"""
开书前设定阶段：当 setting_research.trigger=design_only 时，先由设定研究 Agent 与作者沟通，完善世界模型与各类设定，再进入正篇回合。

交互流程（DESIGN §6.6）：支持 y 设定完成进入正篇 / e 编辑 / s 补充说明 / d 讨论某一方向；选 d 时进入按方向子循环（仅该方向多轮对话→满意后提炼进整体→回到主菜单）；仅作者选择 y（设定完成）时才结束。
"""
import logging
import yaml
from pathlib import Path
from typing import Callable

from src.agents.setting_research import SettingResearchAgent
from src.agents.setting_research.agent import (
    DIRECTION_LABELS,
    discuss_direction,
    discuss_freely,
    extract_direction_yaml,
    extract_discussion_boundaries_by_direction,
    run_discussion_logic_calibration,
    summarize_and_extract_by_directions,
)
from src.config import (
    add_setting_document_to_world_config,
    current_novel_root,
    is_world_config_empty,
    load_special_settings_config,
    load_world_config,
    load_characters_config,
    special_settings_config_dir,
    update_world_brief,
)
from src.author_loop.author_session import AuthorSession
from src.author_harness.author_harness import apply_design_main_menu_ingress
from src.author_loop.classify_intent import classify_intent, looks_like_menu_freeform_design_input
from src.author_harness.prompt_assembler import assemble_retrieval_prompt_block
from src.author_loop.classify_intent import INTENT_DESIGN_COMPLETE, INTENT_FALLBACK
from src.author_loop.context_compression import build_compression_contract
from src.author_loop.retrieve_for_intent import (
    RETRIEVAL_PROFILE_DESIGN_DISCUSSION,
    compress_retrieval_snippets,
    load_compress_settings,
    retrieve_for_intent,
    retrieve_max_total_chars,
)
from src.author_loop.design_session_persistence import (
    add_setting_direction,
    append_summary,
    append_menu_choice,
    append_discussion,
    append_supplement,
    ensure_setting_directions_config,
    load_setting_directions_config,
    save_session,
    load_session_full,
)

logger = logging.getLogger(__name__)


def _design_exit_blocked_by_incomplete_world(menu_key: str, world_config: dict) -> bool:
    """世界名等基础信息未填时，禁止用 y / 其他输入结束设定阶段。"""
    return menu_key in ("y", "other") and is_world_config_empty(world_config)


def _prompt_author_intent_for_setting_research(
    session: AuthorSession,
    *,
    genre: str,
    theme: str,
) -> tuple[str, str]:
    """
    世界名为空时，在首次 agent.run 前向作者收集题材与核心说明，供 LLM 生成**非默认玄幻**的设定初稿。

    返回 (reference 片段, 用于本轮 agent 的 genre 字符串)。
    """
    logger.info("======== 首次设定初稿：请先说明作品方向 ========")
    logger.info(
        "尚未填写世界名称。请说明想写的**类型与核心**（如科幻、都市、言情、悬疑、历史、玄幻等），"
        "系统将据此生成设定研究初稿；避免未说明时模型偏向单一网文套路。"
    )
    idea = session.read_line(
        "请用一两句话描述：① **类型**（必填倾向，可多词）；② **世界或故事核心**（可选）。\n"
        "例：「硬科幻，近未来火星殖民」；「现言，律师与破镜重圆」。若暂时说不清，可直接回车，将按下列题材标签生成**轻量、非修仙默认**的占位体系。\n"
        "> "
    ).strip()
    genre_in = session.read_line(
        "题材关键词（**一两个词**即可，如 科幻 / 都市 / 言情 / 玄幻；回车保留当前「{}」）：".format(
            genre or "架空"
        )
    ).strip()
    new_genre = genre_in or genre or "架空"
    if idea:
        ref = idea
    else:
        ref = (
            "作者暂未逐条说明剧情。题材标签：「{}」。请生成与该标签**一致**的轻度设定骨架；"
            "若无超自然战斗要素，请将 power_system、level_system 命名为该题材贴切概念（如阶层/职级/技术阶段），"
            "禁止默认采用东方修真式境界与灵力设定。".format(new_genre)
        )
    logger.info("已记录设定研究导向：类型=%s，将调用 LLM 生成初稿。", new_genre)
    session.record_round_digest(
        interaction="设定初稿前：作者题材/核心说明",
        system_response="已写入本轮 reference/genre 供 SettingResearchAgent",
        execution=f"genre={new_genre!r}, reference_len={len(ref)}",
        phase="DESIGN_MAIN",
        subphase="setting_intent_bootstrap",
    )
    return ref, new_genre


def _has_existing_setting_output(config_dir: Path) -> bool:
    """检测是否已有设定研究产出文件且含实质内容（非空壳），用于重启时判断是否询问作者再覆盖。"""
    path = special_settings_config_dir(config_dir) / "setting_research_output.yaml"
    if not path.is_file():
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # 除 world_id/version 外有设定方向（如 power_system、level_system）且内容非空即视为已有设定
        skip = {"world_id", "version", "genre", "theme", "reference"}
        for k, v in data.items():
            if k in skip:
                continue
            if isinstance(v, dict) and (v.get("name") or v.get("description") or v.get("levels")):
                return True
            if isinstance(v, (list, str)) and v:
                return True
        return False
    except Exception:
        return False


def _build_cover_brief(
    world_lines: list[str],
    scopes_lines: list[str],
    characters_lines: list[str],
    special_lines: list[str],
) -> str:
    """根据当前审阅摘要拼出封面简介（一两段话），供写入世界配置 brief。"""
    parts: list[str] = []
    # 世界与时代
    for line in (world_lines or []):
        s = line.strip()
        if not s:
            continue
        if "世界:" in s and "时代:" in s:
            # 取「世界: X | 时代: Y」中的 X、Y
            parts.append(s.replace("世界:", "").replace("时代:", "").replace("|", "，").strip())
            break
    # 规则（缩进行）取前 2 条
    rules = [line.strip().replace("规则:", "").strip() for line in (world_lines or []) if "规则:" in line][:2]
    if rules:
        parts.append("；".join(rules) + "。")
    # 范围简述（取范围名或描述首句）
    scope_bits = []
    for line in (scopes_lines or [])[:3]:
        if "范围 [" in line and "]" in line:
            rest = line.split("]", 1)[-1].strip()
            if ":" in rest:
                scope_bits.append(rest.split(":", 1)[0].strip())
            else:
                scope_bits.append(rest[:30])
    if scope_bits:
        parts.append("范围：" + "、".join(scope_bits) + "。")
    # 特殊设定（战力/境界等）取前 2 条简述
    special_bits = []
    for line in (special_lines or [])[:4]:
        s = line.strip()
        if not s or s.startswith("-"):
            continue
        if ":" in s:
            key = s.split(":", 1)[0].strip()
            val = s.split(":", 1)[-1].strip()[:40]
            special_bits.append(f"{key}：{val}")
        else:
            special_bits.append(s[:50])
    if special_bits:
        parts.append("设定：" + "；".join(special_bits[:2]) + "。")
    text = " ".join(parts).replace("  ", " ").strip()
    return text if text else "（暂无简介，保存后将根据设定自动生成）"


# 无独立小说目录时，不会静默进入本模块主循环：run_novel_with_author 先 ensure_current_novel_for_design_phase
#（必要时 prepare_new_novel_if_needed 建初稿），失败则 interactive_resolve_novel_for_design_phase 交互绑定。
# 下列片段用于识别「尚未填写的 YAML 占位」，与 config/example_*.yaml 及 novel_bootstrap._minimal_* 初稿模板对齐；
# 若已有 setting_research_output.reference，审阅区用其替换占位，避免误以为未加载上一轮产出。
_SCOPE_DESC_PLACEHOLDER_MARKERS: tuple[str, ...] = (
    "绑定小说目录后由小说级 config 覆盖",
    "待设定阶段完善",
)
_CHAR_ROLE_PLACEHOLDER_MARKERS: tuple[str, ...] = (
    "绑定小说目录后完善",
    "（待设定）",
)
_CHAR_BG_PLACEHOLDER_MARKERS: tuple[str, ...] = (
    "绑定小说目录后完善",
    "待设定阶段完善",
)


def _field_looks_like_placeholder(text: str, markers: tuple[str, ...]) -> bool:
    t = (text or "").strip()
    return bool(t) and any(m in t for m in markers)


def _ref_preview_note(ref: str, max_chars: int = 100) -> str:
    r = (ref or "").strip()
    if not r:
        return ""
    if len(r) <= max_chars:
        return r
    return r[: max_chars - 1] + "…"


def _scope_desc_is_pending(desc: str) -> bool:
    d = (desc or "").strip()
    return not d or _field_looks_like_placeholder(d, _SCOPE_DESC_PLACEHOLDER_MARKERS)


def _char_role_is_pending(role: str) -> bool:
    r = (role or "").strip()
    return not r or _field_looks_like_placeholder(r, _CHAR_ROLE_PLACEHOLDER_MARKERS)


def _char_bg_is_pending(bg: str) -> bool:
    b = (bg or "").strip()
    return not b or _field_looks_like_placeholder(bg, _CHAR_BG_PLACEHOLDER_MARKERS)


def _has_pending_setting_fields(
    world_config: dict,
    characters_config: dict,
    enabled_scope_ids: list,
    enabled_char_ids: list,
) -> bool:
    """世界名未写、或任一启用范围/角色仍为占位时，要求作者在本轮输入中明确对待填项的处置。"""
    if is_world_config_empty(world_config):
        return True
    for s in world_config.get("scopes") or []:
        if s.get("id") not in enabled_scope_ids:
            continue
        if _scope_desc_is_pending((s.get("description") or "")):
            return True
    for c in characters_config.get("characters") or []:
        if c.get("id") not in enabled_char_ids:
            continue
        if _char_role_is_pending((c.get("role") or "")) or _char_bg_is_pending((c.get("background") or "")):
            return True
    return False


def _author_must_address_pending_line() -> str:
    return (
        "  【须在本轮说明】上文含「【待填写】」处尚未写入正式配置（world.yaml / characters 等）。\n"
        "  请在本轮输入中**至少用一句话**写明：准备如何通过 **c**（讨论归纳）或 **e**（改文件）补全，"
        "或明确「先搁置某项、优先讨论 XX」。**不要**只输入菜单字母而不交代对待填项的处理意向。\n"
    )


def _format_world_summary(world_config: dict, special: dict | None = None) -> list[str]:
    """从 world 配置生成可读摘要行。未写入 world.yaml 的字段标为【待填写】；设定研究仅作「预览」附注（不改变 is_world_config_empty）。"""
    lines = []
    raw_w = world_config.get("world")
    w = raw_w if isinstance(raw_w, dict) else world_config
    if not isinstance(w, dict):
        w = {}
    name_orig = (w.get("name") or "").strip()
    era_orig = (w.get("era") or "").strip()
    sp = special or {}
    ref = ((sp.get("reference") or "") or "").strip()
    name_disp = name_orig if name_orig else "【待填写】"
    era_disp = era_orig if era_orig else "【待填写】"
    has_world_section = isinstance(raw_w, dict)
    if has_world_section or name_orig or era_orig or w.get("rules") or (world_config.get("time") or {}).get("start"):
        lines.append(f"  世界: {name_disp} | 时代: {era_disp}")
        if (not name_orig or not era_orig) and (sp.get("genre") or sp.get("theme") or ref):
            pv = []
            if sp.get("genre"):
                pv.append(f"类型标签「{sp.get('genre')}」")
            if sp.get("theme"):
                pv.append(f"题材「{sp.get('theme')}」")
            if ref:
                pv.append(f"核心说明摘要「{_ref_preview_note(ref, 80)}」")
            lines.append(
                "  （以下为设定研究/初稿**预览**，非 world.yaml 正式值；请 **c** 归纳或 **e** 写入后，上两行「待填写」才会消失）"
            )
            lines.append("  （预览：" + "；".join(pv) + "）")
        rules = w.get("rules") or []
        for r in rules:
            lines.append(f"    规则: {r}")
    time_cfg = world_config.get("time") or {}
    if time_cfg.get("start"):
        lines.append(f"  时间起点: {time_cfg.get('start')}")
    return lines


def _format_scopes_summary(
    world_config: dict,
    enabled_scope_ids: list,
    special: dict | None = None,
) -> list[str]:
    """从 world.scopes 生成范围摘要（仅 enabled）。未写或占位时标【描述待填写】，reference 仅作预览附注。"""
    lines = []
    scopes = world_config.get("scopes") or []
    ref = ((special or {}).get("reference") or "").strip()
    for s in scopes:
        sid = s.get("id")
        if sid not in enabled_scope_ids:
            continue
        desc = (s.get("description") or "").strip()
        if _scope_desc_is_pending(desc):
            line = f"  范围 [{sid}] {s.get('name', sid)}: 【描述待填写】"
            if ref:
                line += f"（设定研究预览，非最终：{_ref_preview_note(ref, 120)}）"
            lines.append(line)
        else:
            lines.append(f"  范围 [{sid}] {s.get('name', sid)}: {desc}")
    return lines


def _format_characters_summary(
    characters_config: dict,
    enabled_char_ids: list,
    special: dict | None = None,
) -> list[str]:
    """从 characters 配置生成角色摘要（仅 enabled）。未写或占位时标【待填写】，reference 仅作预览附注。"""
    lines = []
    chars = characters_config.get("characters") or []
    ref = ((special or {}).get("reference") or "").strip()
    for c in chars:
        cid = c.get("id")
        if cid not in enabled_char_ids:
            continue
        name = c.get("name", cid)
        role = (c.get("role") or "").strip()
        bg = (c.get("background") or "").strip()
        role_part = "身份/职责：【待填写】" if _char_role_is_pending(role) else f"身份/职责：{role}"
        if _char_bg_is_pending(bg):
            bg_part = "背景：【待填写】"
            if ref:
                bg_part += f"（设定研究预览：{_ref_preview_note(ref, 72)}）"
        else:
            bg_part = "背景：" + bg[:120] + ("…" if len(bg) > 120 else "")
        lines.append(f"  角色 [{cid}] {name} | {role_part}；{bg_part}")
    return lines


def _format_special_summary(special: dict | None) -> list[str]:
    """从特殊设定配置生成简短摘要；设定维度不写死，按当前 special 的 key 动态展示。"""
    if not special:
        return ["  （暂无特殊设定文件）"]
    lines = []
    if special.get("genre"):
        lines.append(f"  类型: {special.get('genre')}")
    if special.get("theme"):
        lines.append(f"  题材: {special.get('theme')}")
    base_keys = {"genre", "theme", "world_id", "version", "reference"}
    for key in special:
        if key in base_keys:
            continue
        val = special.get(key)
        if not isinstance(val, dict):
            continue
        label = DIRECTION_LABELS.get(key, key)
        name = val.get("name", "")
        desc = (val.get("description") or "")[:80]
        chapters = val.get("chapters") or []
        if isinstance(chapters, list) and chapters:
            nch = len(chapters)
            bits: list[str] = []
            for c in chapters[:3]:
                if not isinstance(c, dict):
                    continue
                t = (c.get("title") or c.get("name") or "").strip()
                num = c.get("chapter_number", c.get("order", c.get("id", "")))
                if t:
                    bits.append(t)
                elif num != "":
                    bits.append(f"第{num}章")
            ch_hint = f"共{nch}章" + (f"（{', '.join(bits)}…）" if bits else "")
            lines.append(f"  {label}: {name} - {desc} | {ch_hint}")
            continue
        levels = val.get("levels") or []
        level_names = [x.get("name", "") for x in levels[:4] if isinstance(x, dict)]
        if level_names:
            lines.append(f"  {label}: {name} - {desc} ({', '.join(level_names)}{'...' if len(levels) > 4 else ''})")
        else:
            lines.append(f"  {label}: {name} - {desc}")
    return lines if lines else ["  （无其他设定维度）"]


def _direction_snippet(special: dict | None, direction_key: str) -> str:
    """取某一方向的简短摘要，供按方向讨论时作为当前设定上下文。"""
    if not special:
        return "（暂无）"
    d = special.get(direction_key)
    if not d:
        return "（暂无）"
    if isinstance(d, dict):
        name = d.get("name", "")
        desc = (d.get("description") or "")[:200]
        levels = d.get("levels") or []
        return f"名称：{name}\n说明：{desc}\n层级/境界：{levels[:8]}"
    return str(d)[:300]


def _direction_to_md(data: dict) -> str:
    """将某一设定方向 dict 转为 Markdown。"""
    lines = []
    if data.get("name"):
        lines.append(f"# {data['name']}\n")
    if data.get("description"):
        lines.append(f"## 说明\n\n{data['description']}\n")
    levels = data.get("levels") or []
    if levels:
        lines.append("## 层级/境界\n")
        for i, L in enumerate(levels[:30]):
            if isinstance(L, dict):
                lines.append(f"- **{L.get('name', i+1)}**：{L.get('description', '')}")
            else:
                lines.append(f"- {L}")
        if len(levels) > 30:
            lines.append("- ...")
        lines.append("")
    chapters = data.get("chapters") or []
    if isinstance(chapters, list) and chapters:
        lines.append("## 章节要点\n")
        for c in chapters[:200]:
            if isinstance(c, dict):
                num = c.get("chapter_number", c.get("order", c.get("id", "")))
                tit = (c.get("title") or c.get("name") or "").strip()
                summ = (c.get("summary") or c.get("description") or "").strip()
                head = f"第{num}章" if num != "" else "章"
                if tit:
                    head = f"第{num}章 {tit}" if num != "" else tit
                lines.append(f"- **{head}**：{summ}")
            else:
                lines.append(f"- {c}")
        if len(chapters) > 200:
            lines.append("- …")
        lines.append("")
    return "\n".join(lines).strip() or "（暂无内容）"


def _write_special_settings(
    config_dir: Path,
    special: dict,
    project_root: Path | None = None,
    runtime_config: dict | None = None,
    discussion_boundaries: dict[str, str] | None = None,
    allowed_directions: list[str] | None = None,
) -> None:
    """将合并后的特殊设定写回 setting_research_output.yaml；各方向写入 book/setting/<key>.md（仅 allowed_directions 中的方向），可选追加讨论与设定边界。"""
    logger.debug("[设定讨论] _write_special_settings: 开始, allowed_directions=%s, boundaries keys=%s",
                 allowed_directions, list((discussion_boundaries or {}).keys()))
    out_dir = special_settings_config_dir(config_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "setting_research_output.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(special, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    _sync_special_to_book_setting(
        special, project_root, runtime_config,
        discussion_boundaries=discussion_boundaries,
        allowed_directions=allowed_directions,
    )


def _sync_special_to_book_setting(
    special: dict,
    project_root: Path | None,
    runtime_config: dict | None,
    discussion_boundaries: dict[str, str] | None = None,
    allowed_directions: list[str] | None = None,
) -> None:
    """
    将 special 中各设定方向写入 book/setting/<key>.md；可选 discussion_boundaries 为每方向追加「讨论与设定边界」。
    若 allowed_directions 非空，则仅写入该列表中的方向（由 setting_config.yaml 驱动）；为 None 时写入所有方向。
    """
    logger.debug("[设定讨论] _sync_special_to_book_setting: 开始, allowed_directions=%s", allowed_directions)
    if project_root is None or runtime_config is None:
        logger.debug("[设定讨论] _sync_special_to_book_setting: 跳过（无 project_root 或 runtime_config）")
        return
    try:
        from src.runtime.file_sync import get_book_root
        book_root = get_book_root(Path(project_root), runtime_config)
    except Exception:
        pass
    if not book_root:
        book_root = Path(project_root) / "data" / "book"
    logger.debug("[设定讨论] _sync_special_to_book_setting: book_root=%s", book_root)
    base_keys = {"genre", "theme", "world_id", "version", "reference"}
    setting_dir = book_root / "setting"
    setting_dir.mkdir(parents=True, exist_ok=True)
    boundaries = discussion_boundaries or {}
    allowed_set = set(allowed_directions) if allowed_directions is not None else None
    for key, val in special.items():
        if key in base_keys or not isinstance(val, dict):
            continue
        if allowed_set is not None and key not in allowed_set:
            logger.debug("[设定讨论] _sync_special_to_book_setting: 跳过未在配置中的方向 key=%s", key)
            continue
        safe_name = (key or "unknown").replace("/", "_").replace("\\", "_").strip() or "unknown"
        md_path = setting_dir / f"{safe_name}.md"
        logger.debug("[设定讨论] _sync_special_to_book_setting: 写入方向 %s -> %s", key, md_path)
        body = _direction_to_md(val)
        if key in boundaries and (boundaries[key] or "").strip():
            body += "\n\n## 讨论与设定边界\n\n" + (boundaries[key] or "").strip()
        md_path.write_text(body, encoding="utf-8")
        logger.debug("设定方向已写入: %s", md_path)


def _assembled_context_for_discussion(
    author_message: str,
    *,
    session: AuthorSession,
    config_dir: Path,
    runtime_config: dict,
) -> str:
    """R5：自由讨论每轮 classify → retrieve → assemble；结果注入 discuss_freely，并写入 session.extra 便于日志/单测。

    CC-c（D8 §6.1）：超阈且启用时，契约驱动确定性结构保留压缩检索块（来源标签仍由 assembler 保留）。
    """
    _cl = classify_intent(
        author_message,
        session.phase_state,
        session.last_round_digest,
        runtime_config,
        config_dir=config_dir,
    )
    _snippets = retrieve_for_intent(
        _cl.intent_id,
        _cl.retrieval_query or author_message,
        config_dir=config_dir,
        project_root=session.project_root,
        runtime_config=runtime_config,
        internet_search_needed=_cl.internet_search_needed,
        internet_query=_cl.internet_query or None,
        retrieval_profile=RETRIEVAL_PROFILE_DESIGN_DISCUSSION,
    )
    if _cl.intent_id not in (INTENT_DESIGN_COMPLETE, INTENT_FALLBACK):
        contract = build_compression_contract(
            phase="DESIGN_DISCUSSION",
            intent_id=_cl.intent_id,
            user_input=author_message,
            retrieval_query=_cl.retrieval_query or author_message,
            confidence=_cl.confidence,
        )
        _snippets = compress_retrieval_snippets(
            _snippets,
            retrieve_max_total_chars(runtime_config),
            contract=contract,
            settings=load_compress_settings(runtime_config),
        )
    block = assemble_retrieval_prompt_block(_snippets, layout="design_discussion")
    session.extra["intent_retrieval"] = block
    session.extra["intent_retrieval_snippets"] = _snippets
    logger.debug(
        "[设定讨论] _assembled_context_for_discussion: intent=%s retrieval_chars=%s",
        _cl.intent_id,
        len(block),
    )
    return block


def _run_freestyle_discussion(
    config_dir: Path,
    runtime_config: dict,
    theme: str,
    genre: str,
    special: dict,
    initial_message: str,
    session: AuthorSession,
    session_events: list | None = None,
    conversation_resume: list[tuple[str, str]] | None = None,
) -> dict:
    """
    自由讨论子循环：不锁定单一方向，可交叉讨论多维度及其关系；
    作者输入「满意」后由 LLM 提炼并归纳到各方向，写回设定并提示作者。
    conversation_resume：恢复上次未完成讨论时的历史轮次 [(author, agent), ...]，有则不再执行首轮。
    """
    logger.debug("[设定讨论] _run_freestyle_discussion: 进入, initial_message=%r, conversation_resume 轮数=%s",
                 (initial_message or "")[:80], len(conversation_resume) if conversation_resume else 0)
    session.record_round_digest(
        interaction="进入设定自由讨论",
        system_response="多轮对话，满意后归纳到各方向",
        execution="discuss_freely / summarize_and_extract",
        phase="DESIGN_DISCUSSION",
        subphase=None,
    )
    full_special_summary = "\n".join(_format_special_summary(special))
    conversation: list[tuple[str, str]] = list(conversation_resume) if conversation_resume else []
    discussion_text_parts: list[str] = [
        f"作者：{a}\n设定 Agent：{b}" for a, b in conversation
    ]

    # 首轮：仅在没有恢复历史时，用作者刚输入的想法作为第一条
    if initial_message and not conversation_resume:
        logger.debug("[设定讨论] _run_freestyle_discussion: 首轮调用 discuss_freely, initial_message 长度=%s", len(initial_message or ""))
        _ctx0 = _assembled_context_for_discussion(
            initial_message,
            session=session,
            config_dir=config_dir,
            runtime_config=runtime_config,
        )
        reply = discuss_freely(
            author_message=initial_message,
            theme=theme,
            genre=genre,
            full_special_summary=full_special_summary,
            runtime_config=runtime_config,
            conversation_history=conversation,
            assembled_context=_ctx0 or None,
            read_line_fn=session.read_line,
            compressed_retrieval_is_canonical=True,
        )
        conversation.append((initial_message, reply))
        discussion_text_parts.append(f"作者：{initial_message}\n设定 Agent：{reply}")
        logger.info("设定 Agent：%s", reply)
    elif conversation_resume:
        logger.info("已恢复 %d 轮讨论，可继续输入。", len(conversation_resume))

    while True:
        prompt_msg = (
            "\n【设定讨论】请优先谈**可归档的设定与章节大纲**（规则、体系、势力、分章剧情骨架等），"
            "少聊纯文笔或成篇技巧；满意=结束并归纳到各方向 .md，保存=持久化当前对话与设定： "
        )
        user_input = session.read_line(prompt_msg).strip()
        logger.debug("[设定讨论] _run_freestyle_discussion: 用户输入长度=%s, 前50字=%r", len(user_input), (user_input or "")[:50])
        if not user_input:
            continue
        if user_input in ("满意", "可以", "就这样", "ok", "好"):
            logger.debug("[设定讨论] _run_freestyle_discussion: 用户选择「满意」，结束讨论循环")
            break
        if user_input.strip() == "保存" and session_events is not None:
            logger.debug("[设定讨论] _run_freestyle_discussion: 用户选择「保存」，持久化当前对话")
            save_session(
                config_dir,
                theme=theme,
                genre=genre,
                events=session_events,
                state_snapshot={
                    "current_discussion": {
                        "initial_message": initial_message,
                        "rounds": [{"author": a, "agent": b} for a, b in conversation],
                    },
                    "special_summary_lines": _format_special_summary(special),
                },
                project_root=config_dir.parent,
                runtime_config=runtime_config,
            )
            logger.info("已保存当前对话与设定，可继续讨论。")
            continue
        full_special_summary = "\n".join(_format_special_summary(special))
        logger.debug("[设定讨论] _run_freestyle_discussion: 调用 discuss_freely 第 %s 轮", len(conversation) + 1)
        _ctx = _assembled_context_for_discussion(
            user_input,
            session=session,
            config_dir=config_dir,
            runtime_config=runtime_config,
        )
        reply = discuss_freely(
            author_message=user_input,
            theme=theme,
            genre=genre,
            full_special_summary=full_special_summary,
            runtime_config=runtime_config,
            conversation_history=conversation,
            assembled_context=_ctx or None,
            read_line_fn=session.read_line,
            compressed_retrieval_is_canonical=True,
        )
        conversation.append((user_input, reply))
        discussion_text_parts.append(f"作者：{user_input}\n设定 Agent：{reply}")
        logger.info("设定 Agent：%s", reply)

    # 讨论结束：归纳到各方向并写回
    discussion_text = "\n\n".join(discussion_text_parts) or "（无具体讨论，保留当前设定）"
    logger.debug("[设定讨论] _run_freestyle_discussion: 讨论结束, discussion_text 长度=%s, 调用 summarize_and_extract_by_directions", len(discussion_text))
    extracted = summarize_and_extract_by_directions(
        discussion_text=discussion_text,
        theme=theme,
        genre=genre,
        current_special=special,
        runtime_config=runtime_config,
    )
    if extracted:
        logger.debug("[设定讨论] _run_freestyle_discussion: 归纳结果 extracted keys=%s", list(extracted.keys()))
        base_keys = {"genre", "theme", "world_id", "version", "reference"}
        current_direction_keys = [k for k in (special or {}) if k not in base_keys and isinstance((special or {}).get(k), dict)]
        special = {**(special or {}), **extracted}
        direction_keys = [k for k in special if k not in base_keys and isinstance(special.get(k), dict)]
        logger.debug("[设定讨论] _run_freestyle_discussion: current_direction_keys=%s, direction_keys=%s", current_direction_keys, direction_keys)
        # 解析 book 根目录，用于设定方向配置与 .md 落盘
        try:
            from src.runtime.file_sync import get_book_root
            _book_root = get_book_root(Path(config_dir.parent), runtime_config)
        except Exception:
            _book_root = Path(config_dir.parent) / "data" / "book"
        if not _book_root:
            _book_root = Path(config_dir.parent) / "data" / "book"
        # 若尚无设定方向配置，用合并前已有的方向列表引导创建（不包含本次新归纳的方向）
        allowed_directions = load_setting_directions_config(_book_root)
        logger.debug("[设定讨论] _run_freestyle_discussion: 设定方向配置 allowed_directions=%s", allowed_directions)
        if not allowed_directions and current_direction_keys:
            allowed_directions = ensure_setting_directions_config(_book_root, current_direction_keys)
            logger.debug("[设定讨论] _run_freestyle_discussion: 已创建设定方向配置, allowed_directions=%s", allowed_directions)
        # 讨论中涉及但配置中未列出的方向：询问作者是否增加
        for key in extracted:
            if key not in allowed_directions:
                logger.debug("[设定讨论] _run_freestyle_discussion: 新方向「%s」不在配置中，询问作者是否增加", key)
                msg = f"讨论中涉及「{key}」，当前设定配置中未包含该方向，是否增加？(y/n，默认 n): "
                ans = (session.read_line(msg) or "n").strip().lower()
                if ans in ("y", "yes", "是"):
                    add_setting_direction(_book_root, key)
                    add_setting_document_to_world_config(config_dir, key, title=key)
                    allowed_directions = load_setting_directions_config(_book_root)
                    logger.debug("[设定讨论] _run_freestyle_discussion: 已增加方向「%s」, allowed_directions=%s", key, allowed_directions)
        logger.debug("[设定讨论] _run_freestyle_discussion: 调用 extract_discussion_boundaries_by_direction, direction_keys=%s", direction_keys)
        boundaries = extract_discussion_boundaries_by_direction(
            discussion_text, direction_keys, theme, genre, runtime_config
        )
        logger.debug("[设定讨论] _run_freestyle_discussion: 调用 _write_special_settings, allowed_directions=%s", allowed_directions if allowed_directions else None)
        _write_special_settings(
            config_dir, special, config_dir.parent, runtime_config,
            discussion_boundaries=boundaries,
            allowed_directions=allowed_directions if allowed_directions else None,
        )
        direction_names = [DIRECTION_LABELS.get(k, k) for k in extracted.keys()]
        logger.info("已根据讨论提炼并归纳到以下方向：%s", "、".join(direction_names))
        if boundaries:
            logger.info("已按方向写入讨论与设定边界到 book/setting/*.md")
        for line in _format_special_summary(special):
            logger.info(line)
        # 列出本轮更新的设定文件，提醒作者查看；确认没问题后再进行保存与校准
        written_paths: list[str] = [str(special_settings_config_dir(config_dir) / "setting_research_output.yaml")]
        _dirs = allowed_directions if allowed_directions else direction_keys
        for k in _dirs:
            safe = (k or "unknown").replace("/", "_").replace("\\", "_").strip() or "unknown"
            written_paths.append(str(_book_root / "setting" / f"{safe}.md"))
        logger.info("本轮已更新以下设定文件，请查看：")
        for p in written_paths:
            logger.info("  - %s", p)
        while True:
            confirm_msg = (
                "请查看上述设定文件，确认无误后输入 y 继续（将询问是否保存与逻辑校准）： "
            )
            confirm_ans = session.read_line(confirm_msg).strip().lower()
            if confirm_ans in ("y", "yes", "是", "没问题", "确认", "可以", "好"):
                logger.debug("[设定讨论] _run_freestyle_discussion: 作者确认设定文件无误，进入保存与校准")
                break
            logger.info("请查看上述文件后输入 y 确认继续。")
    if session_events is not None:
        logger.debug("[设定讨论] _run_freestyle_discussion: append_discussion, extracted_directions=%s", list(extracted.keys()) if extracted else None)
        append_discussion(
            session_events,
            initial_message=initial_message,
            rounds=conversation,
            extracted_directions=list(extracted.keys()) if extracted else None,
        )

    # 满意后：询问是否保存（保存后可继续讨论）、是否进行本迭代逻辑校准
    logger.debug("[设定讨论] _run_freestyle_discussion: 满意后询问「是否保存」")
    save_prompt = "是否保存？保存后可继续讨论 (y/n，默认 n): "
    save_ans = (session.read_line(save_prompt) or "n").strip().lower()
    logger.debug("[设定讨论] _run_freestyle_discussion: 是否保存 回答=%s", save_ans)
    if save_ans in ("y", "yes", "是") and session_events is not None:
        save_session(
            config_dir,
            theme=theme,
            genre=genre,
            events=session_events,
            state_snapshot={
                "current_discussion": {
                    "initial_message": initial_message,
                    "rounds": [{"author": a, "agent": b} for a, b in conversation],
                },
                "special_summary_lines": _format_special_summary(special),
            },
            project_root=config_dir.parent,
            runtime_config=runtime_config,
        )
        logger.info("已保存，可回到主菜单选 c 继续讨论。")

    logger.debug("[设定讨论] _run_freestyle_discussion: 询问「是否逻辑校准」")
    cal_prompt = "是否进行本迭代讨论的逻辑校准？(y/n，默认 n): "
    cal_ans = (session.read_line(cal_prompt) or "n").strip().lower()
    logger.debug("[设定讨论] _run_freestyle_discussion: 是否逻辑校准 回答=%s", cal_ans)
    if cal_ans in ("y", "yes", "是"):
        special_summary_text = "\n".join(_format_special_summary(special))
        report = run_discussion_logic_calibration(
            discussion_text, special_summary_text, theme, genre, runtime_config
        )
        if report:
            logger.info("【逻辑校准】%s", report)
        else:
            logger.info("逻辑校准未执行或未返回结果（如未配置 LLM）。")

    # 本轮回合结束：将会话归档（显式置 current_discussion 为 None），重启后不再提示「未完成讨论」
    if session_events is not None:
        save_session(
            config_dir,
            theme=theme,
            genre=genre,
            events=session_events,
            state_snapshot={
                "special_summary_lines": _format_special_summary(special),
                "current_discussion": None,  # 明确标记已归档，load 时 _backfill 不再从 events 回填
            },
            project_root=config_dir.parent,
            runtime_config=runtime_config,
        )
        logger.debug("[设定讨论] _run_freestyle_discussion: 已将会话归档（current_discussion=None），重启后不再提示未完成讨论")

    logger.debug("[设定讨论] _run_freestyle_discussion: 返回 special keys=%s", list(special.keys()) if special else [])
    session.record_round_digest(
        interaction="自由讨论子流程结束（满意/归档）",
        system_response="已回到设定主流程可再次审阅",
        execution="归纳写回 setting_research_output 与 book/setting（若 LLM 可用）",
        phase="DESIGN_MAIN",
        subphase=None,
    )
    return special


def run_supplement_setting_during_turn(
    config_dir: Path,
    runtime_config: dict,
    world_config: dict,
    scope_id: str,
    time_str: str,
    place: str,
    turn_summary_snippet: str = "",
    *,
    input_fn: Callable[[str], str] | None = None,
) -> None:
    """
    开篇后确认环节临时补充设定：基于既有设定与当前剧情，仅做补充与完善，不与既有设定冲突。
    提示作者输入补充意向 → 调用 SettingResearchAgent.run_supplement → 写回并同步到 book/setting。
    """
    config_dir = Path(config_dir)
    session = AuthorSession.for_design_phase(
        config_dir=config_dir,
        project_root=config_dir.parent,
        runtime_config=runtime_config,
        input_fn=input_fn,
    )
    theme = (world_config.get("world") or {}).get("name") or "未命名世界"
    inner_world = world_config.get("world") or world_config
    genre = inner_world.get("era") or inner_world.get("genre") or "架空"
    special = load_special_settings_config(config_dir)
    if not special:
        logger.warning("当前无设定文件，无法补充；请先在设定阶段完成设定。")
        return
    context_snippet = f"scope={scope_id}, time={time_str}, place={place}；最近回合摘要：{turn_summary_snippet or '（无）'}"
    prompt_msg = "请输入要补充或完善的设定（需与当前剧情一致、不推翻既有设定）： "
    author_input = session.read_line(prompt_msg).strip()
    if not author_input:
        logger.info("未输入内容，跳过补充。")
        return
    ss_out_dir = special_settings_config_dir(config_dir)
    ss_out_dir.mkdir(parents=True, exist_ok=True)
    agent = SettingResearchAgent(output_dir=ss_out_dir)
    path = agent.run_supplement(
        theme=theme,
        genre=genre,
        current_special=special,
        context_snippet=context_snippet,
        author_input=author_input,
        output_dir=ss_out_dir,
        runtime_config=runtime_config,
    )
    if path is None:
        logger.warning("设定补充未完成（无 LLM 或生成失败），设定未变更。")
        return
    special = load_special_settings_config(config_dir)
    if special:
        _sync_special_to_book_setting(special, config_dir.parent, runtime_config)
    logger.info("设定已补充并写回，可继续确认本回合。")
    session.record_round_digest(
        interaction="开篇回合：补充设定（run_supplement）",
        system_response="已合并写回 setting_research_output 并同步 book/setting",
        execution=f"输出文件 {path}",
        phase="MAIN_WRITING",
        subphase=None,
    )


def run_design_phase(
    config_dir: Path,
    runtime_config: dict,
    world_config: dict,
    characters_config: dict,
    *,
    input_fn: Callable[[str], str] | None = None,
) -> bool:
    """
    开书前设定阶段：运行设定研究 Agent，展示世界模型与设定，与作者交互完善。
    当前：y 确认进入正篇 / e 编辑设定文件 / s 补充说明并重新生成；选 y 即结束。
    目标（DESIGN §6.6）：支持按方向讨论（每次答复仅针对该方向）→ 作者满意后提炼进整体 → 再问修改/继续讨论/设定完成，仅作者明确「设定完成」时才结束。
    返回 True 表示用户曾选择过「e」编辑设定，调用方应重新加载配置并重建编排器后再进入回合。
    """
    config_dir = Path(config_dir)
    session = AuthorSession.for_design_phase(
        config_dir=config_dir,
        project_root=config_dir.parent,
        runtime_config=runtime_config,
        input_fn=input_fn,
    )
    enabled_char = list(runtime_config.get("agents", {}).get("characters", {}).get("enabled_ids", []))
    enabled_scope = list(runtime_config.get("agents", {}).get("scopes", {}).get("enabled_ids", []))

    theme = (world_config.get("world") or {}).get("name") or "未命名世界"
    inner_world = world_config.get("world") or world_config
    genre = inner_world.get("era") or inner_world.get("genre") or "架空"
    reference: str | None = None
    config_was_edited = False

    logger.debug("[设定讨论] run_design_phase: 开始, config_dir=%s", config_dir)
    ss_out_dir = special_settings_config_dir(config_dir)
    ss_out_dir.mkdir(parents=True, exist_ok=True)
    agent = SettingResearchAgent(output_dir=ss_out_dir)
    loaded = load_session_full(config_dir, config_dir.parent, runtime_config)
    logger.debug("[设定讨论] run_design_phase: load_session_full 结果=%s", "有加载" if loaded else "无")
    if loaded:
        logger.debug("[设定讨论] run_design_phase: events 条数=%s, state_snapshot keys=%s",
                     len(loaded.get("events") or []), list((loaded.get("state_snapshot") or {}).keys()))
    session_events: list = (loaded["events"] if loaded else []) or []
    resumed_state: dict = (loaded.get("state_snapshot") or {}) if loaded else {}
    is_first_after_resume = bool(session_events)
    logger.debug("[设定讨论] run_design_phase: session_events 条数=%s, is_first_after_resume=%s", len(session_events), is_first_after_resume)

    # 从讨论子流程（满意→归纳→保存/校准）返回时跳过下一次 agent.run()，避免覆盖刚写回的 setting_research_output.yaml
    skip_next_agent_run = False
    # 主菜单因「基础世界未填」拒绝结束设定阶段时，下一轮不再重复 agent.run（避免无意义覆盖/重复调用 LLM）
    skip_agent_after_menu_block = False
    first_iteration = True  # 用于重启时检测「已有设定/会话」并询问是否保留，避免危险覆盖

    while True:
        # 运行设定研究 Agent（产出/更新 setting_research_output.yaml）；刚从讨论返回时跳过，保留归纳结果
        if skip_next_agent_run:
            logger.debug("[设定讨论] run_design_phase: 主循环 跳过 agent.run()（刚从讨论返回，保留归纳后的设定）")
            skip_next_agent_run = False
        elif skip_agent_after_menu_block:
            logger.debug("[设定讨论] run_design_phase: 跳过 agent.run()（上次主菜单因基础设定未完成被拒）")
            skip_agent_after_menu_block = False
        else:
            # 重启后若检测到已有设定或会话，先询问作者再决定是否覆盖（危险操作需确认）
            run_agent_this_turn = True
            if first_iteration:
                has_existing = bool(loaded) or _has_existing_setting_output(config_dir)
                if has_existing:
                    logger.info("检测到已有设定或会话。重新生成将覆盖现有设定（危险操作）。")
                    confirm = session.read_line(
                        "是否保留现有设定？(y=保留并继续, n=重新生成并覆盖, 默认 y): ",
                    ).lower().strip() or "y"
                    if confirm == "y":
                        run_agent_this_turn = False
                        logger.debug("[设定讨论] run_design_phase: 作者选择保留现有设定，跳过 agent.run()")
                    else:
                        logger.info("作者确认重新生成，将覆盖现有设定。")
            if run_agent_this_turn:
                if is_world_config_empty(world_config) and not session.extra.get(
                    "_author_setting_intent_collected"
                ):
                    ref_add, genre = _prompt_author_intent_for_setting_research(
                        session, genre=genre, theme=theme
                    )
                    session.extra["_author_setting_intent_collected"] = True
                    reference = ref_add if not reference else f"{reference}\n{ref_add}"
                logger.debug("[设定讨论] run_design_phase: 主循环 开始 agent.run()")
                try:
                    agent.run(
                        theme=theme,
                        genre=genre,
                        reference=reference,
                        output_dir=ss_out_dir,
                        runtime_config=runtime_config,
                    )
                except Exception as e:
                    logger.warning("设定研究 Agent 运行失败: %s", e)
        first_iteration = False
        special = load_special_settings_config(config_dir)
        logger.debug("[设定讨论] run_design_phase: 已加载 special keys=%s", list(special.keys()) if special else [])
        if special:
            _sync_special_to_book_setting(special, config_dir.parent, runtime_config)

        # 将 data/book/setting 下已有设定方向回填到世界配置 setting_documents（若尚未登记）
        try:
            from src.runtime.file_sync import get_book_root
            _br = get_book_root(Path(config_dir.parent), runtime_config)
        except Exception:
            _br = Path(config_dir.parent) / "data" / "book"
        if _br:
            dirs = load_setting_directions_config(_br)
            existing_keys = {d.get("key") for d in (world_config.get("setting_documents") or []) if isinstance(d, dict) and d.get("key")}
            for k in dirs:
                if k and k not in existing_keys:
                    add_setting_document_to_world_config(config_dir, k, title=k)
                    existing_keys.add(k)
            # 重新加载世界配置以便后续展示含最新 setting_documents
            world_config = load_world_config(config_dir)

        # 展示世界模型与设定，并记入会话（恢复会话时首轮不重复 append_summary）
        logger.debug("[设定讨论] run_design_phase: 展示世界模型与设定, is_first_after_resume=%s", is_first_after_resume)
        world_lines = _format_world_summary(world_config, special)
        scopes_lines = _format_scopes_summary(world_config, enabled_scope, special)
        characters_lines = _format_characters_summary(characters_config, enabled_char, special)
        special_lines = _format_special_summary(special)
        if not is_first_after_resume:
            append_summary(session_events, world_lines, scopes_lines, characters_lines, special_lines)
        else:
            is_first_after_resume = False

        if is_world_config_empty(world_config):
            logger.info(
                "（世界名称等仍在 world.yaml 中为空：可继续用下方主菜单 **c** 多轮讨论/归纳，或 **e** 编辑配置文件补全世界名与时代。）"
            )
        logger.info("======== 设定阶段：世界模型与设定审阅 ========")
        for line in world_lines:
            logger.info(line)
        logger.info("  --- 范围 ---")
        for line in scopes_lines:
            logger.info(line)
        logger.info("  --- 角色 ---")
        for line in characters_lines:
            logger.info(line)
        logger.info("  --- 特殊设定（战力/境界等，来自设定研究或示例） ---")
        for line in special_lines:
            logger.info(line)
        logger.info("==============================================")

        has_resumed_discussion = bool(resumed_state.get("current_discussion"))
        world_incomplete = is_world_config_empty(world_config)
        pending_fields = _has_pending_setting_fields(
            world_config, characters_config, enabled_scope, enabled_char
        )
        pending_note = _author_must_address_pending_line() if pending_fields else ""
        if pending_fields:
            logger.info(
                "【须在本轮说明】仍存在「待填写」项，请在输入中用一句话说明如何补全或优先讨论何项（见下方菜单提示）。"
            )
        force_discuss_line = (
            "\n  【基础设定未完成：世界名等仍为空，须先 **c** 讨论归纳或 **e** 编辑 world.yaml，**不可直接 y** 结束本阶段】\n"
            if world_incomplete
            else ""
        )
        default_menu = "c" if world_incomplete else "y"
        prompt_msg = (
            "\n请审阅以上世界模型与设定。\n"
            + pending_note
            + "  y 设定完成，进入正篇\n"
            "  e 编辑设定文件后继续\n"
            "  c 输入想法（可一句补充重新生成整体设定，或说出想讨论/新增的设定，进入多轮对话，满意后归纳）\n"
            + ("  【检测到未完成讨论，选 c 可继续上次对话】\n" if has_resumed_discussion else "")
            + "  p 保存进度（持久化当前设定与全部对话，便于后续增量续写）\n"
            + force_discuss_line
            + f"请选择 (y/e/c/p，默认 {default_menu}): "
        )
        ans = session.read_line(prompt_msg).lower().strip() or default_menu
        _ingress = apply_design_main_menu_ingress(
            ans,
            session=session,
            config_dir=config_dir,
            runtime_config=runtime_config,
        )
        menu_key = _ingress.menu_key
        _cl = _ingress.classification
        logger.debug(
            "[设定讨论] run_design_phase: 主菜单 raw=%s intent=%s menu_key=%s retrieval_chars=%s",
            ans,
            _cl.intent_id,
            menu_key,
            len(_ingress.retrieval_block),
        )
        append_menu_choice(session_events, ans)

        if _design_exit_blocked_by_incomplete_world(menu_key, world_config):
            logger.info(
                "【尚未完成基础设定】世界名称等仍为空，不能结束设定阶段。"
                "请先选 **c** 进行设定交流（多轮讨论至「满意」后归纳），或选 **e** 编辑小说目录下 config/world.yaml 补全世界名与时代。"
            )
            session.record_round_digest(
                interaction=f"主菜单: 尝试结束设定({menu_key!s}, 输入={ans!r})，因基础世界未填被拦截",
                system_response="须先 c 或 e",
                execution="continue；跳过下一轮 agent.run",
                phase="DESIGN_MAIN",
            )
            skip_agent_after_menu_block = True
            continue

        if menu_key == "y":
            logger.debug("[设定讨论] run_design_phase: 用户选择 y，设定完成进入正篇")
            logger.info("设定阶段结束，进入正篇。")
            session.record_round_digest(
                interaction="主菜单: y（设定完成，进入正篇）",
                system_response="结束 run_design_phase",
                execution="返回调用方，进入书名确认或正篇回合",
                phase="DESIGN_MAIN",
            )
            return config_was_edited
        if menu_key == "e":
            logger.debug("[设定讨论] run_design_phase: 用户选择 e，编辑设定文件")
            config_was_edited = True
            _sr_hint = special_settings_config_dir(config_dir) / "setting_research_output.yaml"
            if current_novel_root(config_dir):
                logger.info(
                    "请编辑小说目录下 config/ 中的 world.yaml、characters.yaml、"
                    "setting_research_output.yaml（当前路径：%s），或全局 config/ 下的 example_special_settings.yaml，保存后回到此处。",
                    _sr_hint,
                )
            else:
                logger.info(
                    "请编辑 config/ 下的 example_world.yaml、example_characters.yaml、"
                    "example_special_settings.yaml 或 setting_research_output.yaml，保存后回到此处。"
                )
            session.read_line("编辑完成后按回车继续。")
            world_config = load_world_config(config_dir)
            characters_config = load_characters_config(config_dir)
            reference = None
            special = load_special_settings_config(config_dir) or {}
            session.record_round_digest(
                interaction="主菜单: e（编辑设定相关 YAML 后继续）",
                system_response="已提示路径并等待回车",
                execution="重新加载 world / characters / special",
                phase="DESIGN_MAIN",
            )
            continue
        if menu_key == "p":
            logger.debug("[设定讨论] run_design_phase: 用户选择 p，保存进度")
            snapshot = {
                "world_summary": world_lines,
                "scopes_summary": scopes_lines,
                "characters_summary": characters_lines,
                "special_summary": special_lines,
                "special_keys": list(special.keys()) if special else [],
            }
            # 若最近一条是讨论，一并写入 current_discussion，便于下次启动时识别「继续上次对话」
            if session_events:
                last_ev = session_events[-1]
                if last_ev.get("type") == "discussion":
                    snapshot["current_discussion"] = {
                        "initial_message": last_ev.get("initial_message", ""),
                        "rounds": last_ev.get("rounds", []),
                    }
            save_session(
                config_dir,
                theme=theme,
                genre=genre,
                events=session_events,
                state_snapshot=snapshot,
                project_root=config_dir.parent,
                runtime_config=runtime_config,
            )
            # 将当前设定摘要写入世界配置的封面简介（brief），随 p 保存动态更新
            cover_brief = _build_cover_brief(world_lines, scopes_lines, characters_lines, special_lines)
            update_world_brief(config_dir, cover_brief)
            session.record_round_digest(
                interaction="主菜单: p（保存进度）",
                system_response="已持久化 design_session 与封面 brief",
                execution="save_session + update_world_brief",
                phase="DESIGN_MAIN",
            )
            continue
        if menu_key == "c":
            logger.debug("[设定讨论] run_design_phase: 用户选择 c，进入讨论或继续上次")
            current_discussion = resumed_state.pop("current_discussion", None) if resumed_state else None
            logger.debug("[设定讨论] run_design_phase: current_discussion=%s", "有" if current_discussion else "无")
            if current_discussion:
                initial_message = current_discussion.get("initial_message", "")
                rounds_raw = current_discussion.get("rounds") or []
                conversation_resume = [
                    (r.get("author", ""), r.get("agent", "")) for r in rounds_raw
                    if isinstance(r, dict)
                ]
                reference = initial_message
                logger.info("继续上次讨论（共 %d 轮），可直接输入看法或「满意」结束。", len(conversation_resume))
                special = load_special_settings_config(config_dir) or {}
                logger.debug("[设定讨论] run_design_phase: 进入 _run_freestyle_discussion（继续上次）, 恢复轮数=%s", len(conversation_resume))
                special = _run_freestyle_discussion(
                    config_dir, runtime_config, theme, genre, special or {},
                    initial_message, session,
                    session_events=session_events,
                    conversation_resume=conversation_resume,
                )
                skip_next_agent_run = True  # 保留归纳后的 setting_research_output.yaml，下次循环不覆盖
                continue
            logger.debug("[设定讨论] run_design_phase: 首次讨论，等待用户输入想法")
            idea_prompt = (
                "请输入您的想法或补充（一句补充将用于重新生成整体设定；或直接说出想讨论/新增的设定内容，将进入多轮对话，满意后归纳到各方向）： "
            )
            if looks_like_menu_freeform_design_input(ans):
                author_thought = (ans or "").strip()
                logger.info("主菜单已输入设定描述，直接进入讨论（等价于选 c）。")
            else:
                author_thought = session.read_line(idea_prompt).strip()
            if not author_thought:
                logger.info("未输入内容，请重试。")
                continue
            reference = author_thought
            append_supplement(session_events, author_thought)
            discuss_prompt = "是否进入多轮讨论继续细化？（y/回车=是，n=否；选否将仅把当前输入作为补充，下一轮审阅时重新生成整体）： "
            want_discuss = session.read_line(discuss_prompt).lower().strip() != "n"
            logger.debug("[设定讨论] run_design_phase: 是否进入多轮讨论=%s", want_discuss)
            if want_discuss:
                # 进入讨论前先根据输入更新整体设定，再自由讨论
                logger.debug("[设定讨论] run_design_phase: 进入讨论前 agent.run(reference=...), 再 _run_freestyle_discussion")
                try:
                    agent.run(
                        theme=theme,
                        genre=genre,
                        reference=reference,
                        output_dir=ss_out_dir,
                        runtime_config=runtime_config,
                    )
                except Exception as e:
                    logger.warning("设定研究 Agent 运行失败: %s", e)
                special = load_special_settings_config(config_dir) or {}
                special = _run_freestyle_discussion(
                    config_dir, runtime_config, theme, genre, special or {}, author_thought, session,
                    session_events=session_events,
                )
                skip_next_agent_run = True  # 保留归纳后的 setting_research_output.yaml，下次循环不覆盖
            # 若未进入讨论，仅更新 reference，下一轮循环会 agent.run(reference=reference) 并展示
            continue
        # 其他输入视为确认
        logger.info("设定阶段结束，进入正篇。")
        session.record_round_digest(
            interaction=f"主菜单: 其他输入（{ans!r}，intent={_cl.intent_id}）视为确认进入正篇",
            system_response="非 y/e/c/p 的默认分支",
            execution="run_design_phase 返回",
            phase="DESIGN_MAIN",
        )
        return config_was_edited
