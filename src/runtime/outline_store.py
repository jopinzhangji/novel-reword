"""
全书大纲与进度：落盘于 <data_root>/book/outline/outline.yaml 与 progress.yaml。

data_root 与 file_sync、relationship_graph 同源：runtime.storage.data_root。
一般为当前小说目录 data/novels/<slug>/，outline 与 content/events/relationships 等同在一棵目录树下，
与「按书名隔离」一致。

无文件时本模块返回 None（主流程不强制要求大纲文件）。
见 docs/design/outline-and-beats.md。
"""
from __future__ import annotations

import datetime as _dt
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def outline_yaml_path(data_root: Path) -> Path:
    return Path(data_root) / "book" / "outline" / "outline.yaml"


def progress_yaml_path(data_root: Path) -> Path:
    return Path(data_root) / "book" / "outline" / "progress.yaml"


def _read_yaml(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("读取 YAML 失败 %s: %s", path, e)
        return None
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        logger.warning("大纲文件根类型应为 mapping: %s", path)
        return None
    return raw


def validate_outline(outline: dict[str, Any]) -> list[str]:
    """
    轻量校验，仅收集提示性警告，不阻止加载。
    """
    warnings: list[str] = []
    ver = outline.get("version")
    if ver is not None and not isinstance(ver, int):
        warnings.append("version 建议为整数")
    if "chapters" in outline and outline["chapters"] is not None:
        if not isinstance(outline["chapters"], list):
            warnings.append("chapters 应为列表")
        else:
            for i, ch in enumerate(outline["chapters"]):
                if not isinstance(ch, dict):
                    warnings.append(f"chapters[{i}] 应为 mapping")
                    continue
                if not ch.get("id"):
                    warnings.append(f"chapters[{i}] 缺少 id")
                beats = ch.get("beats")
                if beats is not None and not isinstance(beats, list):
                    warnings.append(f"chapters[{i}].beats 应为列表")
    if "volumes" in outline and outline["volumes"] is not None:
        if not isinstance(outline["volumes"], list):
            warnings.append("volumes 应为列表")
        else:
            for i, vol in enumerate(outline["volumes"]):
                if not isinstance(vol, dict):
                    warnings.append(f"volumes[{i}] 应为 mapping")
                    continue
                chs = vol.get("chapters")
                if chs is not None and not isinstance(chs, list):
                    warnings.append(f"volumes[{i}].chapters 应为列表")
    if not outline.get("chapters") and not outline.get("volumes"):
        warnings.append("未定义 chapters 或 volumes（空大纲亦可）")
    return warnings


def validate_progress(progress: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    ver = progress.get("version")
    if ver is not None and not isinstance(ver, int):
        warnings.append("progress.version 建议为整数")
    if "chapter_id" not in progress and "beat_id" not in progress:
        warnings.append("progress 建议包含 chapter_id / beat_id 之一以便定位")
    tib = progress.get("turns_in_beat")
    if tib is not None:
        try:
            int(tib)
        except (TypeError, ValueError):
            warnings.append("turns_in_beat 建议为整数")
    return warnings


@dataclass
class OutlineSnapshot:
    """内存中的大纲 + 可选进度，供日志与后续注入 prompt。"""

    outline: dict[str, Any]
    progress: dict[str, Any] | None
    outline_path: Path
    progress_path: Path
    warnings: list[str] = field(default_factory=list)

    def log_line(self) -> str:
        """单行摘要，供启动或回合日志。"""
        parts = [f"大纲文件: {self.outline_path.name}"]
        ch_n = len(self._flat_chapters())
        if ch_n:
            parts.append(f"{ch_n} 章")
        if self.progress:
            cid = self.progress.get("chapter_id") or "?"
            bid = self.progress.get("beat_id") or "?"
            tib = self.progress.get("turns_in_beat", 0)
            parts.append(f"进度 chapter={cid} beat={bid} 本节拍回合≈{tib}")
        else:
            parts.append("无 progress.yaml")
        if self.warnings:
            parts.append(f"校验提示 {len(self.warnings)} 条")
        return "；".join(parts)

    def _flat_chapters(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        root = self.outline.get("chapters") or []
        if isinstance(root, list):
            for c in root:
                if isinstance(c, dict):
                    out.append(c)
        for vol in self.outline.get("volumes") or []:
            if not isinstance(vol, dict):
                continue
            for c in vol.get("chapters") or []:
                if isinstance(c, dict):
                    out.append(c)
        return out


def load_outline_snapshot(data_root: Path | None) -> OutlineSnapshot | None:
    """
    若存在 outline.yaml 则加载；progress 可选。
    data_root 为空或 outline 不存在时返回 None。
    """
    if not data_root:
        return None
    root = Path(data_root)
    op = outline_yaml_path(root)
    raw = _read_yaml(op)
    if raw is None:
        return None
    warnings = validate_outline(raw)
    pp = progress_yaml_path(root)
    prog = _read_yaml(pp)
    if prog is not None:
        warnings.extend(validate_progress(prog))
    return OutlineSnapshot(
        outline=raw,
        progress=prog,
        outline_path=op,
        progress_path=pp,
        warnings=warnings,
    )


@dataclass
class BeatContext:
    """当前章 + 节拍，供注入写作前分析与正文 prompt（大纲 MVP-1）。"""

    chapter_id: str
    chapter_title: str
    dramatic_question: str
    beat_id: str
    beat_intent: str
    suggested_scope_id: str | None
    tags: list[str]
    turns_in_beat: int
    soft_max_turns: int
    next_beat_hint: str
    missing_ref: str = ""  # Opt-7：progress 引用到不存在的章/拍时置 "chapter"/"beat"；无缺失为 ""


def outline_injection_options(runtime_config: dict[str, Any]) -> dict[str, Any]:
    """是否注入大纲块、单节拍软上限回合数（仅文案提示）。"""
    inner = runtime_config.get("runtime") or runtime_config
    ol = inner.get("outline") or {}
    enabled = ol.get("enabled", True)
    if enabled is False:
        en = False
    else:
        en = True
    soft = ol.get("soft_max_turns_per_beat", 3)
    try:
        soft_i = int(soft)
    except (TypeError, ValueError):
        soft_i = 3
    return {"enabled": bool(en), "soft_max_turns": max(1, soft_i)}


def resolve_current_beat(
    snapshot: OutlineSnapshot,
    *,
    soft_max_turns: int = 3,
) -> BeatContext | None:
    """
    根据 progress 定位当前节拍；缺 progress 或 beat 时回退到第一章首个 planned/active 节拍。
    """
    chapters = snapshot._flat_chapters()
    if not chapters:
        return None
    prog = snapshot.progress or {}
    cid_req = prog.get("chapter_id")
    bid_req = prog.get("beat_id")
    try:
        turns_in_beat = int(prog.get("turns_in_beat", 0) or 0)
    except (TypeError, ValueError):
        turns_in_beat = 0

    chapter: dict[str, Any] | None = None
    missing_ref: str = ""  # Opt-7：progress 引用到不存在的章/拍时置位，调用方 WARN
    if cid_req:
        for ch in chapters:
            if isinstance(ch, dict) and ch.get("id") == cid_req:
                chapter = ch
                break
    if chapter is None:
        if cid_req:
            missing_ref = "chapter"  # 请求的 chapter_id 未命中 → 显式记载缺失
        chapter = chapters[0] if isinstance(chapters[0], dict) else None
    if not chapter:
        return None

    beats_raw = chapter.get("beats") or []
    beats: list[dict[str, Any]] = [b for b in beats_raw if isinstance(b, dict)]
    if not beats:
        return None

    beat: dict[str, Any] | None = None
    beat_idx = -1
    if bid_req:
        for i, b in enumerate(beats):
            if b.get("id") == bid_req:
                beat = b
                beat_idx = i
                break
        if beat is None and not missing_ref:
            missing_ref = "beat"  # 请求的 beat_id 未命中 → 显式记载缺失
    if beat is None:
        for i, b in enumerate(beats):
            st = str(b.get("status") or "planned").lower()
            if st in ("planned", "active"):
                beat = b
                beat_idx = i
                break
    if beat is None:
        beat = beats[0]
        beat_idx = 0

    ch_id = str(chapter.get("id") or "")
    ch_title = str(chapter.get("title") or ch_id or "（章）")
    dq = str(chapter.get("dramatic_question") or "").strip()
    b_id = str(beat.get("id") or "")
    intent = str(beat.get("intent") or "").strip() or "（未写节拍意图）"
    sugg = beat.get("suggested_scope_id")
    sugg_s = str(sugg).strip() if sugg else None
    tags_raw = beat.get("tags") or []
    tags: list[str] = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []

    next_hint = ""
    if beat_idx >= 0 and beat_idx + 1 < len(beats):
        nb = beats[beat_idx + 1]
        ni = str(nb.get("intent") or "").strip()
        if ni:
            next_hint = f"下一节拍（勿在本回合写尽）：{ni}"
    elif beat_idx >= 0:
        next_hint = "本章后续无更多节拍条目；勿提前写下一章核心转折除非分析中说明原因。"

    return BeatContext(
        chapter_id=ch_id,
        chapter_title=ch_title,
        dramatic_question=dq,
        beat_id=b_id,
        beat_intent=intent,
        suggested_scope_id=sugg_s,
        tags=tags,
        turns_in_beat=turns_in_beat,
        soft_max_turns=soft_max_turns,
        next_beat_hint=next_hint,
        missing_ref=missing_ref,
    )


def format_outline_snippet_for_prompt(
    beat: BeatContext | None,
    *,
    protagonist_id: str | None,
    protagonist_display_name: str | None,
) -> str:
    """拼【全书大纲·当前节拍】块；beat 为 None 时返回空串。"""
    if beat is None:
        return ""
    sm = beat.soft_max_turns
    lines = [
        "【全书大纲·当前节拍】（须与下面「本段目标」一致或可解释偏离；勿用本段写尽下一节拍）",
        f"- 章：{beat.chapter_title}（id={beat.chapter_id}）",
    ]
    if beat.dramatic_question:
        lines.append(f"- 本章戏剧问题：{beat.dramatic_question}")
    lines.append(f"- 当前节拍 id：{beat.beat_id}")
    lines.append(f"- 本节拍意图：{beat.beat_intent}")
    if beat.suggested_scope_id:
        lines.append(f"- 建议范围 scope_id：{beat.suggested_scope_id}")
    if beat.tags:
        lines.append(f"- 标签：{', '.join(beat.tags)}")
    lines.append(
        f"- 本节拍已推进约 {beat.turns_in_beat} 回合；建议单节拍通常少于 {sm} 回合（软提示，非硬性截断）。"
    )
    if beat.next_beat_hint:
        lines.append(f"- {beat.next_beat_hint}")
    if protagonist_id or protagonist_display_name:
        who = protagonist_display_name or protagonist_id
        lines.append(
            f"- 叙事主轴：以主角「{who}」（id={protagonist_id or who}）为镜头锚点；"
            "非主角仅在场或必要时简短带过。"
        )
    return "\n".join(lines)


def resolve_outline_context(
    runtime_config: dict[str, Any],
    outline_snapshot: OutlineSnapshot | None,
    characters_config: dict[str, Any] | None = None,
    *,
    protagonist_id: str | None = None,
    protagonist_display_name: str | None = None,
) -> tuple[str, BeatContext | None]:
    """
    **单次解析**（Opt 3/4）：合并 runtime.outline 开关、resolve_current_beat、主角解析，
    一次得到注入 prompt 的整段文本与 BeatContext，供 prompt 注入 + 日志 + 写回复用。
    protagonist_id/display 可由调用方传入（避免重复解析主角）；缺省时内部 resolve。
    关闭或快照为空时返回 ("", None)。
    """
    opts = outline_injection_options(runtime_config)
    if not opts["enabled"] or outline_snapshot is None:
        return ("", None)
    beat = resolve_current_beat(
        outline_snapshot,
        soft_max_turns=int(opts["soft_max_turns"]),
    )
    if protagonist_id is None or protagonist_display_name is None:
        from src.runtime.protagonist import resolve_protagonist_id

        pid, pname = resolve_protagonist_id(runtime_config, characters_config)
        protagonist_id = protagonist_id if protagonist_id is not None else pid
        protagonist_display_name = protagonist_display_name if protagonist_display_name is not None else pname
    snippet = format_outline_snippet_for_prompt(
        beat,
        protagonist_id=protagonist_id,
        protagonist_display_name=protagonist_display_name,
    )
    return (snippet, beat)


def build_outline_prompt_snippet(
    runtime_config: dict[str, Any],
    outline_snapshot: OutlineSnapshot | None,
    characters_config: dict[str, Any] | None = None,
) -> str:
    """
    兼容入口：委托 resolve_outline_context 取 snippet（保留原签名，外部调用不变）。
    """
    snippet, _ = resolve_outline_context(runtime_config, outline_snapshot, characters_config)
    return snippet


# --- MVP-1b：从设定「章节大纲」单向生成首版 outline.yaml（见 docs/planning/outline-mvp-plan.md §2、§4.5）---

SETTING_CHAPTER_OUTLINE_KEY = "章节大纲"


def extract_chapter_outline_from_setting(special: dict[str, Any]) -> dict[str, Any] | None:
    """返回设定 YAML 中「章节大纲」块；若无 chapters 列表或为空则 None。"""
    raw = special.get(SETTING_CHAPTER_OUTLINE_KEY)
    if not isinstance(raw, dict):
        return None
    chs = raw.get("chapters")
    if not isinstance(chs, list) or len(chs) == 0:
        return None
    return raw


def outline_dict_from_setting_chapter_outline(block: dict[str, Any]) -> dict[str, Any]:
    """
    将 ``章节大纲`` 下的 ``chapters[]``（``chapter_number`` / ``title`` / ``summary`` 等）
    映射为 ``outline.yaml`` 根结构：每章一条 **单节拍占位**，``intent = summary``。
    """
    chapters_out: list[dict[str, Any]] = []
    chapters_in = block.get("chapters") or []
    if not isinstance(chapters_in, list):
        chapters_in = []
    for i, row in enumerate(chapters_in):
        if not isinstance(row, dict):
            continue
        num = row.get("chapter_number")
        try:
            n = int(num) if num is not None else i + 1
        except (TypeError, ValueError):
            n = i + 1
        ch_id = str(row.get("id") or "").strip() or f"ch{n:02d}"
        title = str(row.get("title") or f"第{n}章").strip() or f"第{n}章"
        summary = str(row.get("summary") or row.get("intent") or "").strip() or "（本节拍功能未写）"
        dq = str(row.get("dramatic_question") or "").strip()
        bid = str(row.get("beat_id") or "").strip() or f"{ch_id}_b1"
        beat: dict[str, Any] = {
            "id": bid,
            "intent": summary,
            "status": "planned",
        }
        ss = row.get("suggested_scope_id")
        if ss:
            beat["suggested_scope_id"] = str(ss).strip()
        tags_raw = row.get("tags")
        if isinstance(tags_raw, list) and tags_raw:
            beat["tags"] = [str(t) for t in tags_raw]
        chapters_out.append(
            {
                "id": ch_id,
                "title": title,
                "dramatic_question": dq,
                "beats": [beat],
            }
        )
    return {"version": 1, "chapters": chapters_out}


def materialize_outline_from_setting_research(
    data_root: Path,
    setting_research: dict[str, Any],
    *,
    overwrite: bool = False,
    write_initial_progress: bool = True,
) -> tuple[bool, str]:
    """
    若设定中含非空「章节大纲」且目标位置尚无 ``outline.yaml`` 或 ``overwrite=True``，
    则写入 ``book/outline/outline.yaml``；可选写入首章首节拍的 ``progress.yaml``。
    """
    block = extract_chapter_outline_from_setting(setting_research)
    if block is None:
        return (False, "设定中无可用章节大纲（章节大纲.chapters 为空或未定义）")
    outline_body = outline_dict_from_setting_chapter_outline(block)
    if not outline_body.get("chapters"):
        return (False, "章节大纲映射后为空（无有效章条目）")
    root = Path(data_root)
    op = outline_yaml_path(root)
    if op.is_file() and not overwrite:
        return (False, f"已存在 {op}，未覆盖（overwrite=False）")
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(
        yaml.dump(outline_body, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    msg = f"已写入 {op}"
    if write_initial_progress:
        ch0 = outline_body["chapters"][0]
        cid = str(ch0.get("id") or "")
        beats0 = ch0.get("beats") or []
        bid = ""
        if beats0 and isinstance(beats0[0], dict):
            bid = str(beats0[0].get("id") or "")
        if cid and bid:
            if overwrite or not progress_yaml_path(root).is_file():
                prog = {"version": 1, "chapter_id": cid, "beat_id": bid, "turns_in_beat": 0}
                pp = save_progress(root, prog)
                msg += f"；已写入 {pp}"
    return (True, msg)


# --- MVP-2：progress.yaml 写回 + 节拍推进（见 docs/planning/outline-mvp-plan.md §5）---
# updated_at 时间戳仅由 I/O 层 save_progress 填充；纯计算函数（bump/advance）不带时间，保持确定性易测。


def normalize_progress(progress: dict[str, Any]) -> dict[str, Any]:
    """补默认键：version 缺省 1；返回新 dict，不做原地改动。"""
    out = dict(progress or {})
    if not out.get("version"):
        out["version"] = 1
    return out


def bump_turns_in_beat(progress: dict[str, Any]) -> dict[str, Any]:
    """安全默认：返回 turns_in_beat+1 的新 progress，其余键保留。每确认写回一个有效回合调用。"""
    out = normalize_progress(progress)
    try:
        tib = int(out.get("turns_in_beat", 0) or 0)
    except (TypeError, ValueError):
        tib = 0
    out["turns_in_beat"] = tib + 1
    return out


def advance_to_next_beat(
    snapshot: OutlineSnapshot,
    progress: dict[str, Any],
) -> dict[str, Any] | None:
    """
    作者显式推进：同章下一拍 → 下一章首拍（planned/active，缺省首拍）→ 到末章末拍返 None（不越界）。
    返回新 progress（turns_in_beat 重置 0）；无下一拍返回 None。
    """
    chapters = snapshot._flat_chapters()
    if not chapters:
        return None
    beat = resolve_current_beat(snapshot)
    if beat is None:
        return None

    cur_cid = beat.chapter_id
    cur_bid = beat.beat_id
    # 当前章在扁平列表中的索引
    cur_ch_idx = -1
    for i, ch in enumerate(chapters):
        if isinstance(ch, dict) and ch.get("id") == cur_cid:
            cur_ch_idx = i
            break
    if cur_ch_idx < 0:
        return None

    cur_ch = chapters[cur_ch_idx]
    beats = [b for b in (cur_ch.get("beats") or []) if isinstance(b, dict)]
    # 同章内下一拍
    for i, b in enumerate(beats):
        if b.get("id") == cur_bid and i + 1 < len(beats):
            nxt = beats[i + 1]
            return {
                "version": 1,
                "chapter_id": cur_cid,
                "beat_id": str(nxt.get("id") or ""),
                "turns_in_beat": 0,
            }
    # 无同章下一拍 → 下一章首拍
    for ch in chapters[cur_ch_idx + 1:]:
        for b in (ch.get("beats") or []):
            if isinstance(b, dict):
                return {
                    "version": 1,
                    "chapter_id": str(ch.get("id") or ""),
                    "beat_id": str(b.get("id") or ""),
                    "turns_in_beat": 0,
                }
    return None


def save_progress(data_root: Path, progress: dict[str, Any]) -> Path:
    """写 progress.yaml：补 updated_at（UTC ISO）并落盘。统一写点，未来加锁有收敛面。"""
    root = Path(data_root)
    pp = progress_yaml_path(root)
    pp.parent.mkdir(parents=True, exist_ok=True)
    body = normalize_progress(progress)
    body["updated_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    pp.write_text(
        yaml.dump(body, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    logger.info("[大纲] 已写回进度: %s", pp)
    return pp
