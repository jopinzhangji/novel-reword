"""
分类后按需检索（docs/design/author-interaction.md §9、§13 M4）。

最小实现：「设定相关」「保存进度」与 **R7c** 正篇审阅 **`review_revise`**（须传 ``storage`` + ``scope_id``）；
其余 intent 返回空列表。
片段总长度受 max_total_chars 约束，便于单测与后续注入 Handler。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

import re

from src.author_harness.retrieval_registry import (
    DESIGN_MAIN_SETTING_TOOLS,
    INTENT_RETRIEVAL_TOOL_CHAINS,
    MAIN_WRITING_REVIEW_TOOLS,
)
from src.author_loop.classify_intent import (
    INTENT_DESIGN_COMPLETE,
    INTENT_EDIT_SETTING_FILES,
    INTENT_FALLBACK,
    INTENT_INPUT_IDEA_DISCUSS,
    INTENT_REVIEW_REVISE,
    INTENT_SAVE_PROGRESS,
)
from src.agents.setting_research.agent import DIRECTION_LABELS
from src.author_loop.context_compression import reduce_snippet_structure_preserved
from src.config import current_novel_root, load_world_config
from src.runtime.file_sync import get_book_root
from src.author_harness.internet_search import fetch_internet_snippet_playwright, load_internet_search_settings

logger = logging.getLogger(__name__)

# 设定自由讨论：与 Harness「整段 YAML」相对，改用结构化提要 + 归档 .md 行级压缩（不省略数据源）
RETRIEVAL_PROFILE_DEFAULT = "default"
RETRIEVAL_PROFILE_DESIGN_DISCUSSION = "design_discussion"

# 压缩模式下至多汇入的归档 .md 数（避免单次 prompt 线性膨胀；其余仍在磁盘可查）
_COMPACT_BOOK_SETTING_MD_MAX_FILES = 12

_PLACEHOLDER_MD_BULLET = re.compile(r"^[-*]\s+\*\*[^*]+\*\*\s*[：:]\s*$")


@dataclass(frozen=True)
class RetrievalSnippet:
    """单条检索结果（来源标签 + 文本）。"""

    source: str
    text: str
    truncated: bool = False


def _author_interaction_cfg(runtime_config: dict) -> dict[str, Any]:
    rt = runtime_config.get("runtime") if isinstance(runtime_config.get("runtime"), dict) else {}
    if not isinstance(rt, dict):
        rt = {}
    ar = rt.get("author_interaction")
    return ar if isinstance(ar, dict) else {}


def retrieve_max_total_chars(runtime_config: dict, default: int = 2800) -> int:
    cfg = _author_interaction_cfg(runtime_config)
    raw = cfg.get("retrieve_max_total_chars")
    if isinstance(raw, int) and raw > 200:
        return min(raw, 20000)
    return default


def _normalize_query_tokens(q: str) -> list[str]:
    """拆出用于相关性打分的 token；过短拉丁字符丢弃，避免菜单键 `c` 误命中。"""
    q = (q or "").strip()
    if not q:
        return []
    raw = [p for p in re.split(r"\s+", q) if p]
    low = q.lower()
    if low not in raw and len(q) >= 2:
        raw.append(q)
    out: list[str] = []
    for t in raw:
        if len(t) >= 2 or any(ord(c) > 127 for c in t):
            out.append(t)
    seen: set[str] = set()
    deduped: list[str] = []
    for t in out:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            deduped.append(t)
    return deduped


def _score_text_for_query(text: str, tokens: list[str]) -> int:
    if not text or not tokens:
        return 0
    tlow = text.lower()
    return sum(len(tok) for tok in tokens if tok.lower() in tlow)


def _budgets_weighted(cap: int, weights: list[int]) -> list[int]:
    """按权重分配 cap（整数、非负、之和为 cap）。"""
    if cap <= 0:
        return [0] * len(weights)
    w = [max(1, x) for x in weights]
    tw = sum(w)
    raw = [int(cap * wi / tw) for wi in w]
    rem = cap - sum(raw)
    i = 0
    while rem > 0 and raw:
        raw[i % len(raw)] += 1
        rem -= 1
        i += 1
    return raw


def _truncate(s: str, max_chars: int) -> tuple[str, bool]:
    s = (s or "").strip()
    if len(s) <= max_chars:
        return s, False
    return s[: max_chars - 1] + "…", True


def _setting_research_yaml_path(config_dir: Path) -> Path | None:
    novel_root = current_novel_root(config_dir)
    if novel_root:
        p = novel_root / "config" / "setting_research_output.yaml"
        if p.is_file():
            return p
    return None


def _snippet_world(config_dir: Path, budget: int) -> RetrievalSnippet | None:
    try:
        wc = load_world_config(config_dir)
    except Exception as e:
        logger.debug("retrieve_for_intent: load_world_config failed: %s", e)
        return None
    w = wc.get("world") if isinstance(wc.get("world"), dict) else {}
    name = (w.get("name") or "").strip()
    era = (w.get("era") or "").strip()
    brief = ""
    if isinstance(wc.get("brief"), str):
        brief = wc["brief"].strip()
    lines = []
    if name:
        lines.append(f"世界名: {name}")
    if era:
        lines.append(f"时代: {era}")
    if brief:
        lines.append(f"封面/简介 brief: {brief}")
    text = "\n".join(lines) if lines else "（世界配置暂无摘要）"
    t, trunc = _truncate(text, budget)
    return RetrievalSnippet(source="world.yaml", text=t, truncated=trunc)


def _format_setting_research_dict_digest(data: dict) -> str:
    """
    将 setting_research_output 结构压成短文本（对齐 design_phase._format_special_summary 信息密度，避免整文件 YAML）。
    """
    if not isinstance(data, dict):
        return "（无效的设定结构）"
    lines: list[str] = []
    if data.get("genre"):
        lines.append(f"类型: {data.get('genre')}")
    if data.get("theme"):
        lines.append(f"题材: {data.get('theme')}")
    if data.get("world_id"):
        lines.append(f"world_id: {data.get('world_id')}")
    ref = ((data.get("reference") or "")).strip()
    if ref:
        clip = ref if len(ref) <= 260 else ref[:259] + "…"
        lines.append(f"作者参照/草稿摘录: {clip}")
    base_keys = {"genre", "theme", "world_id", "version", "reference"}
    for key in data:
        if key in base_keys:
            continue
        val = data.get(key)
        if not isinstance(val, dict):
            continue
        label = DIRECTION_LABELS.get(key, key)
        name = val.get("name", "")
        desc = ((val.get("description") or ""))[:100]
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
            lines.append(f"{label}: {name} - {desc} | {ch_hint}")
            continue
        levels = val.get("levels") or []
        level_names = [str(x.get("name", "")) for x in levels[:6] if isinstance(x, dict) and x.get("name")]
        if level_names:
            suf = "…" if len(levels) > 6 else ""
            lines.append(f"{label}: {name} - {desc} | 层级: {', '.join(level_names)}{suf}")
        else:
            lines.append(f"{label}: {name} - {desc}")
    return "\n".join(lines) if lines else "（无可展开的设定条目）"


def _snippet_setting_research_digest(config_dir: Path, budget: int) -> RetrievalSnippet | None:
    """
    Setting YAML 的结构化提要（与同目录 ``setting_research_output`` 语义对齐 design_phase._format_special_summary）。
    用于设定讨论：**不整块注入 YAML**，以降低与归档稿重复；非删源，仅存盘内容的压缩视图。
    """
    path = _setting_research_yaml_path(config_dir)
    if not path:
        return RetrievalSnippet(
            source="setting_research_output.yaml",
            text="（未找到小说目录下 setting_research_output.yaml）",
            truncated=False,
        )
    try:
        raw_text = path.read_text(encoding="utf-8")
    except Exception as e:
        return RetrievalSnippet(source="setting_research_output.yaml", text=f"（读取失败: {e}）", truncated=False)
    try:
        data = yaml.safe_load(raw_text) or {}
    except Exception:
        t, trunc = _truncate(raw_text, min(budget, 900))
        return RetrievalSnippet(
            source=f"setting_research_output.yaml:{path.name}#原文片段",
            text="（YAML 解析失败，附原文前缀）\n" + t,
            truncated=trunc,
        )
    if not isinstance(data, dict):
        t, trunc = _truncate(raw_text, min(budget, 900))
        return RetrievalSnippet(
            source=f"setting_research_output.yaml:{path.name}#原文片段",
            text=t,
            truncated=trunc,
        )
    body = _format_setting_research_dict_digest(data)
    t, trunc = _truncate(body, budget)
    return RetrievalSnippet(source=f"setting_research_output.yaml:{path.name}#摘要", text=t, truncated=trunc)


def _compact_book_setting_markdown(raw: str) -> str:
    """
    压缩 book/setting 下归档 Markdown：保留标题行与实质列表行，弱化空壳「- **名**：」占位（与正文策划里「设定概要截取」同源思路）。
    """
    out_lines: list[str] = []
    for line in raw.splitlines():
        t = line.strip()
        if not t:
            continue
        if t in ("---", "***"):
            continue
        if _PLACEHOLDER_MD_BULLET.match(t):
            continue
        out_lines.append(line.rstrip())
    return "\n".join(out_lines).strip()


def _snippet_setting_research_file(config_dir: Path, budget: int) -> RetrievalSnippet | None:
    path = _setting_research_yaml_path(config_dir)
    if not path:
        return RetrievalSnippet(
            source="setting_research_output.yaml",
            text="（未找到小说目录下 setting_research_output.yaml）",
            truncated=False,
        )
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        return RetrievalSnippet(source="setting_research_output.yaml", text=f"（读取失败: {e}）", truncated=False)
    t, trunc = _truncate(raw, budget)
    return RetrievalSnippet(source=f"setting_research_output.yaml:{path.name}", text=t, truncated=trunc)


def _snippet_book_setting_md(
    project_root: Path,
    runtime_config: dict,
    budget: int,
    *,
    compact: bool = False,
) -> RetrievalSnippet | None:
    book_root = get_book_root(project_root, runtime_config)
    if not book_root:
        return None
    setting_dir = book_root / "setting"
    if not setting_dir.is_dir():
        return None
    md_all = sorted(p for p in setting_dir.glob("*.md") if p.is_file())
    if not md_all:
        return None
    omitted = 0
    if compact:
        md_use = md_all[:_COMPACT_BOOK_SETTING_MD_MAX_FILES]
        omitted = len(md_all) - len(md_use)
        per_floor = 120
    else:
        md_use = md_all[:3]
        per_floor = 400
    parts: list[str] = []
    per = max(per_floor, budget // max(1, len(md_use)))
    for p in md_use:
        try:
            body = p.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if compact:
            body = _compact_book_setting_markdown(body)
        chunk, trunc = _truncate(body, per)
        tag = "--- {name} ---{ellipsis}\n{body}".format(
            name=p.name,
            ellipsis=" …截断" if trunc else "",
            body=chunk,
        )
        parts.append(tag)
    if not parts:
        return None
    text = "\n\n".join(parts)
    if compact and omitted > 0:
        text += f"\n\n（另有 {omitted} 篇 book/setting 归档未写入本摘录，请以磁盘为准。）"
    t, trunc = _truncate(text, budget)
    label = "book/setting/*.md#压缩摘要" if compact else "book/setting/*.md"
    return RetrievalSnippet(source=label, text=t, truncated=trunc)


def _snippet_author_interaction_state_file(config_dir: Path, budget: int) -> RetrievalSnippet | None:
    from src.author_loop.author_interaction_state import author_interaction_state_path

    path = author_interaction_state_path(config_dir)
    if not path.is_file():
        return RetrievalSnippet(
            source="author_interaction_state.yaml",
            text="（尚无 author_interaction_state.yaml）",
            truncated=False,
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        return RetrievalSnippet(source="author_interaction_state.yaml", text=f"（解析失败: {e}）", truncated=False)
    digest = raw.get("last_round_digest") if isinstance(raw, dict) else None
    if not isinstance(digest, dict):
        digest = {}
    lines = [
        f"interaction: {digest.get('interaction', '')}",
        f"system_response: {digest.get('system_response', '')}",
        f"execution: {digest.get('execution', '')}",
    ]
    oi = digest.get("open_issues")
    if isinstance(oi, list) and oi:
        lines.append("open_issues: " + "; ".join(str(x) for x in oi[:8]))
    text = "\n".join(lines)
    t, trunc = _truncate(text, budget)
    return RetrievalSnippet(source="author_interaction_state.yaml#last_round_digest", text=t, truncated=trunc)


def _snippet_scope_recent_events(
    storage: Any,
    scope_id: str,
    budget: int,
    *,
    k: int = 8,
) -> RetrievalSnippet | None:
    """最近范围事件摘要（与正文数据源一致的事件簿）；无事件时仍返回占位说明。"""
    from src.retrieval.memory import format_scope_events_snippet

    text = format_scope_events_snippet(storage, scope_id, k=k)
    if not (text or "").strip():
        return RetrievalSnippet(
            source=f"scope_events:{scope_id}",
            text="（暂无范围事件摘要；storage 无记录或尚未写回事件簿）",
            truncated=False,
        )
    t, trunc = _truncate(text, budget)
    return RetrievalSnippet(source=f"scope_events:{scope_id}", text=t, truncated=trunc)


def _snippet_design_session_meta(config_dir: Path, budget: int) -> RetrievalSnippet | None:
    path = Path(config_dir) / "design_session.yaml"
    if not path.is_file():
        return RetrievalSnippet(source="design_session.yaml", text="（尚无 design_session.yaml）", truncated=False)
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        return RetrievalSnippet(source="design_session.yaml", text=f"（读取失败: {e}）", truncated=False)
    t, trunc = _truncate(raw, budget)
    return RetrievalSnippet(source="design_session.yaml", text=t, truncated=trunc)


def retrieve_for_intent(
    intent_id: str,
    retrieval_query: str,
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
    max_total_chars: int | None = None,
    storage: Any | None = None,
    scope_id: str | None = None,
    internet_search_needed: bool = False,
    internet_query: str | None = None,
    retrieval_profile: str = RETRIEVAL_PROFILE_DEFAULT,
) -> list[RetrievalSnippet]:
    """
    按 intent 从磁盘与配置组装短片段。M4 仅实现两类：

    - ``input_idea_discuss`` / ``edit_setting_files``：世界摘要、setting_research_output、book/setting 下若干 .md 尾部
    - ``save_progress``：上一轮 digest（author_interaction_state）、design_session 元数据

    其它 intent（含 ``design_complete``、``intent_fallback``）返回空列表。

    **R4**：``retrieval_query`` 参与设定类意图的预算分配（先默认预算采样、再按命中加权重建）；
    ``save_progress`` 与 ``review_revise`` 两路同理。

    **R7c**：``intent_id=review_revise`` 时须提供 ``storage`` 与 ``scope_id`` 以拉取最近事件摘要；
    缺省时仅返回 ``author_interaction_state`` digest。意图→工具链见 ``author_harness.retrieval_registry``。

    **按需联网（I5）**：当 ``runtime.author_harness.internet_search.require_classifier_signal`` 为默认 true 时，
    须 ``internet_search_needed=True``（通常来自 ``classify_intent``）才会发起 Bing 抓取；
    ``internet_query`` 非空时优先作为搜索词句，否则沿用 ``retrieval_query``。

    ``retrieval_profile``：``design_discussion`` 用于「设定自由讨论」—— **YAML 结构化提要**
    （与同目录磁盘 YAML 语义等价、非整块照搬）叠加 **归档 .md 行级压缩**；
    ``book/setting`` 可多文件汇入（单轮上限十二篇）；默认 ``profile`` 仍为主菜单 Harness 的整段 YAML + 至多三篇归档。
    """
    cap = max_total_chars if max_total_chars is not None else retrieve_max_total_chars(runtime_config)
    cap = max(400, min(cap, 20000))
    tokens = _normalize_query_tokens(retrieval_query)

    if intent_id in (INTENT_INPUT_IDEA_DISCUSS, INTENT_EDIT_SETTING_FILES):
        tool_chain = INTENT_RETRIEVAL_TOOL_CHAINS[intent_id]
        if tool_chain != DESIGN_MAIN_SETTING_TOOLS:
            raise NotImplementedError(
                "retrieve_for_intent: intent %r has tool chain %r; R4 仅实现 DESIGN_MAIN_SETTING_TOOLS"
                % (intent_id, tool_chain)
            )
        inet_settings = load_internet_search_settings(runtime_config)
        iq_eff = (
            ((internet_query or "").strip())
            if internet_query is not None
            else ""
        ) or (
            retrieval_query.strip()
            if retrieval_query else ""
        )
        inet_tokens = _normalize_query_tokens(iq_eff)

        classifier_ok = internet_search_needed or not inet_settings.require_classifier_signal

        use_internet = (
            inet_settings.enabled
            and inet_settings.provider in ("playwright", "browser", "bing", "ddg")
            and classifier_ok
            and len(inet_tokens) >= inet_settings.min_query_tokens
        )
        net_budget = 0
        if use_internet:
            net_budget = min(
                inet_settings.max_chars,
                max(300, cap // 5),
                cap // 2,
            )
        local_cap = cap - net_budget

        if retrieval_profile == RETRIEVAL_PROFILE_DESIGN_DISCUSSION:
            # 提要占比较少，多分预算给归档 .md（经行级压缩后仍保留多文件要点）
            b1 = max(260, local_cap // 6)
            b2 = max(400, local_cap // 4)
            b3 = local_cap - b1 - b2
            sw = _snippet_world(config_dir, b1)
            sr = _snippet_setting_research_digest(config_dir, b2)
            bk = _snippet_book_setting_md(
                project_root, runtime_config, b3, compact=True
            )
        else:
            b1 = local_cap // 4
            b2 = local_cap // 2
            b3 = local_cap // 6
            sw = _snippet_world(config_dir, b1)
            sr = _snippet_setting_research_file(config_dir, b2)
            bk = _snippet_book_setting_md(
                project_root, runtime_config, b3, compact=False
            )
        out = [x for x in (sw, sr, bk) if x]
        if tokens:
            sc0 = _score_text_for_query(sw.text, tokens) if sw else 0
            sc1 = _score_text_for_query(sr.text, tokens) if sr else 0
            sc2 = _score_text_for_query(bk.text, tokens) if bk else 0
            total_sc = sc0 + sc1 + sc2
            if total_sc > 0:
                if bk is None:
                    nb = _budgets_weighted(local_cap, [sc0 + 1, sc1 + 1])
                    sw = _snippet_world(config_dir, nb[0])
                    if retrieval_profile == RETRIEVAL_PROFILE_DESIGN_DISCUSSION:
                        sr = _snippet_setting_research_digest(config_dir, nb[1])
                    else:
                        sr = _snippet_setting_research_file(config_dir, nb[1])
                    out = [x for x in (sw, sr) if x]
                else:
                    nb = _budgets_weighted(local_cap, [sc0 + 1, sc1 + 1, sc2 + 1])
                    sw = _snippet_world(config_dir, nb[0])
                    if retrieval_profile == RETRIEVAL_PROFILE_DESIGN_DISCUSSION:
                        sr = _snippet_setting_research_digest(config_dir, nb[1])
                        bk = _snippet_book_setting_md(
                            project_root, runtime_config, nb[2], compact=True
                        )
                    else:
                        sr = _snippet_setting_research_file(config_dir, nb[1])
                        bk = _snippet_book_setting_md(
                            project_root, runtime_config, nb[2], compact=False
                        )
                    out = [x for x in (sw, sr, bk) if x]
                logger.debug(
                    "retrieve_for_intent: retrieval_query tokens=%s scores=(%s,%s,%s) budgets=%s",
                    tokens,
                    sc0,
                    sc1,
                    sc2,
                    nb,
                )
        if use_internet and net_budget > 0:
            inet = fetch_internet_snippet_playwright(
                iq_eff,
                budget=net_budget,
                settings=inet_settings,
            )
            if inet:
                inet_snip = RetrievalSnippet(
                    source=inet.source,
                    text=inet.text,
                    truncated=inet.truncated,
                )
                out = [*out, inet_snip]
                logger.info(
                    "retrieve_for_intent: internet_playwright chars=%d source=%s",
                    len(inet_snip.text),
                    inet_snip.source,
                )
        return _enforce_total_budget(out, cap)

    if intent_id == INTENT_SAVE_PROGRESS:
        b1 = cap // 2
        b2 = cap - b1
        s1 = _snippet_author_interaction_state_file(config_dir, b1)
        s2 = _snippet_design_session_meta(config_dir, b2)
        out = [x for x in (s1, s2) if x]
        if tokens and len(out) == 2:
            sc0 = _score_text_for_query(s1.text, tokens)
            sc1 = _score_text_for_query(s2.text, tokens)
            if sc0 + sc1 > 0:
                nb = _budgets_weighted(cap, [sc0 + 1, sc1 + 1])
                s1 = _snippet_author_interaction_state_file(config_dir, nb[0])
                s2 = _snippet_design_session_meta(config_dir, nb[1])
                out = [x for x in (s1, s2) if x]
                logger.debug(
                    "retrieve_for_intent: save_progress query tokens=%s scores=(%s,%s) budgets=%s",
                    tokens,
                    sc0,
                    sc1,
                    nb,
                )
        return _enforce_total_budget(out, cap)

    if intent_id == INTENT_REVIEW_REVISE:
        tool_chain = INTENT_RETRIEVAL_TOOL_CHAINS[intent_id]
        if tool_chain != MAIN_WRITING_REVIEW_TOOLS:
            raise NotImplementedError(
                "retrieve_for_intent: review_revise expects MAIN_WRITING_REVIEW_TOOLS, got %r" % (tool_chain,)
            )
        if storage is not None and scope_id:
            b1 = cap // 2
            b2 = cap - b1
            se = _snippet_scope_recent_events(storage, scope_id, b1)
            ai = _snippet_author_interaction_state_file(config_dir, b2)
            out = [x for x in (se, ai) if x]
            if tokens and len(out) == 2:
                sc0 = _score_text_for_query(se.text, tokens)
                sc1 = _score_text_for_query(ai.text, tokens)
                if sc0 + sc1 > 0:
                    nb = _budgets_weighted(cap, [sc0 + 1, sc1 + 1])
                    se = _snippet_scope_recent_events(storage, scope_id, nb[0])
                    ai = _snippet_author_interaction_state_file(config_dir, nb[1])
                    out = [x for x in (se, ai) if x]
                    logger.debug(
                        "retrieve_for_intent: review_revise query tokens=%s scores=(%s,%s) budgets=%s",
                        tokens,
                        sc0,
                        sc1,
                        nb,
                    )
            return _enforce_total_budget(out, cap)
        ai = _snippet_author_interaction_state_file(config_dir, cap)
        return _enforce_total_budget([x for x in (ai,) if x], cap)

    if intent_id in (INTENT_DESIGN_COMPLETE, INTENT_FALLBACK):
        return []

    return []


def _enforce_total_budget(snippets: list[RetrievalSnippet], cap: int) -> list[RetrievalSnippet]:
    total = sum(len(s.text) for s in snippets)
    if total <= cap:
        return snippets
    # 按比例缩减每条
    ratio = cap / max(1, total)
    out: list[RetrievalSnippet] = []
    for s in snippets:
        n = max(80, int(len(s.text) * ratio))
        t, trunc = _truncate(s.text, n)
        out.append(RetrievalSnippet(source=s.source, text=t, truncated=trunc or s.truncated))
    return out


# --- CC-c：契约驱动确定性结构保留压缩（SDD D8 §6.1；纯确定性、无 LLM） ---
_DEFAULT_COMPRESS = {"enabled": False, "threshold_ratio": 0.75, "target_ratio": 0.5}
_FLOOR_PER_SNIPPET = 32  # 每块保留锚点下限，保证「非单段结论」的最小结构


def load_compress_settings(runtime_config: dict) -> dict[str, Any]:
    """读 `runtime.author_interaction.context_compress`；缺省默认关（用户可调）。"""
    cfg = _author_interaction_cfg(runtime_config)
    cc = cfg.get("context_compress")
    cc = cc if isinstance(cc, dict) else {}
    value = dict(_DEFAULT_COMPRESS)
    for k, d in (("enabled", False), ("threshold_ratio", 0.75), ("target_ratio", 0.5)):
        raw = cc.get(k, d)
        if k == "enabled":
            value[k] = bool(raw)
        elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
            value[k] = max(0.0, min(1.0, float(raw)))
    return value


def compress_retrieval_snippets(
    snippets: list[RetrievalSnippet],
    cap: int,
    *,
    contract: Any,
    settings: dict[str, Any] | None = None,
) -> list[RetrievalSnippet]:
    """CC-c 门限触发压缩：契约驱动逐块结构保留削减至 target_ratio×cap（滞回）。

    - 未启用 / 超阈 未达 threshold_ratio×cap → **原样返回**（无阈行为不变，default 不破）。
    - 超阈启用 → 每块 `reduce_snippet_structure_preserved` 缩到份额（下限保锚点），来源标签
      由 assembler 保留 → 输出仍分块/分节、带【来源】，绝不含糊单段结论。
    - 返回后由调用方 `_enforce_total_budget`（硬保险）兜底。
    """
    settings = settings or load_compress_settings({})
    if not settings.get("enabled") or cap <= 0:
        return snippets
    total = sum(len(s.text) for s in snippets)
    threshold = int(settings.get("threshold_ratio", 0.75) * cap)
    if total <= cap or total < threshold:  # 未超阈：保持原样
        return snippets
    target = max(1, int(settings.get("target_ratio", 0.5) * cap))
    # 契约参与：若契约要求 keep 的结构层占主导，削减更保守（此处按份额等比，契约 ID 留日志可观测）
    out: list[RetrievalSnippet] = []
    n = len(snippets)
    # 每块保底份额（保证「非单段结论」最小结构），且 Σfloor ≤ target；余量按文本占比分。
    per_floor = _FLOOR_PER_SNIPPET if n == 0 else min(_FLOOR_PER_SNIPPET, max(1, target // n))
    pool = max(0, target - per_floor * n)
    weights = [max(1e-9, len(s.text)) for s in snippets]
    wsum = sum(weights)
    for s, w in zip(snippets, weights):
        share = per_floor + (int(pool * w / wsum) if n else 0) if n else 0
        new_text = reduce_snippet_structure_preserved(s.text, max(1, share))
        out.append(RetrievalSnippet(source=s.source, text=new_text, truncated=True))
    logger.info(
        "compress_retrieval_snippets: is_compressed chars=%d->%d cap=%d target=%d contract_proto=%s",
        total, sum(len(x.text) for x in out), cap, target,
        getattr(contract, "prototype_id", "") or "",
    )
    return out


def format_snippets_for_prompt(snippets: list[RetrievalSnippet]) -> str:
    """拼成一段可注入提示词的短上下文（带来源标题）。"""
    if not snippets:
        return ""
    blocks = []
    for s in snippets:
        blocks.append(f"【{s.source}】\n{s.text}")
    return "\n\n".join(blocks)


def _discussion_snippet_sort_key(sn: RetrievalSnippet) -> tuple[int, str]:
    """设定讨论归档：世界 → YAML 提要 → 本地 md → 外网摘录（外链放末便于对标流行写法）。"""
    src_l = (sn.source or "").lower()
    src = sn.source or ""
    if any(x in src_l for x in ("internet", "playwright", "bing", "ddg")):
        return (3, src)
    if "world" in src_l:
        return (0, src)
    if "#摘要" in src or ("setting_research" in src_l and "摘要" in src):
        return (1, src)
    if "book" in src_l or "#压缩摘要" in src:
        return (2, src)
    return (2, src)


def _discussion_section_title(sn: RetrievalSnippet) -> str:
    """人读层级编号，与实际 source 技术指标并列便于对照。"""
    src_l = (sn.source or "").lower()
    src = sn.source or ""
    if any(x in src_l for x in ("internet", "playwright", "bing", "ddg")):
        return "④ 外网检索摘要（可选对照流行写法）"
    if "world" in src_l:
        return "① 世界配置摘要"
    if "#摘要" in src or ("setting_research" in src_l and "摘要" in src):
        return "② 结构化设定提要（与 setting_research YAML 语义对齐·已压缩）"
    if "book" in src_l or "setting" in src_l:
        return "③ book/setting 归档稿摘录（Markdown 已行级压缩）"
    return "摘录"


def format_snippets_design_discussion(snippets: list[RetrievalSnippet]) -> str:
    """
    设定**自由讨论**专用排版：分层标题 + 固定阅读顺序，与 ``discuss_freely`` 的「归档摘录」块衔接。
    """
    if not snippets:
        return ""
    ordered = sorted(snippets, key=_discussion_snippet_sort_key)
    lines = [
        "「归档摘录」——请按自上而下的序号分层阅读（与磁盘一致；下层可提供更细的原文要点）。",
        "————————————————————————",
    ]
    for sn in ordered:
        title = _discussion_section_title(sn)
        lines.append(f"【{title}】  技术指标：{sn.source}")
        lines.append(sn.text.strip())
        lines.append("")
    return "\n".join(lines).rstrip()
