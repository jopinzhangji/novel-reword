"""
作者自由输入经 LLM 体系化归类后，持久化到 data_root/book/memory/author_classified/<类别>/entries.md；
生成写作前分析时按「索引 → LLM 选类 → 加载对应目录」做渐进式检索，注入 prompt。

默认 5 类；可通过 `runtime.author_classified_memory` 按小说类型扩展或替换（见 `config/novel_writing.yaml`，经合并后位于 `runtime` 下）。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 与 docs/design/memory-storage-and-retrieval.md 的 book 布局一致
AUTHOR_MEMORY_SEG = Path("memory") / "author_classified"

DEFAULT_CATEGORY_DEFS: list[dict[str, str]] = [
    {"id": "setting", "label_zh": "设定", "hint": "世界观、规则、道具等"},
    {"id": "character", "label_zh": "人物", "hint": "人物、关系、出场要求"},
    {"id": "constraints", "label_zh": "约束", "hint": "禁止项、尺度、硬约束"},
    {"id": "narrative", "label_zh": "剧情", "hint": "剧情走向、悬念、节奏"},
    {"id": "meta", "label_zh": "其他", "hint": "无法归类或流程说明"},
]

AUTHOR_CATEGORIES: tuple[str, ...] = tuple(d["id"] for d in DEFAULT_CATEGORY_DEFS)

_CATEGORY_ID_SAFE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

_CATEGORY_ALIASES: dict[str, str] = {
    "设定": "setting",
    "世界观": "setting",
    "人物": "character",
    "角色": "character",
    "约束": "constraints",
    "禁忌": "constraints",
    "剧情": "narrative",
    "叙事": "narrative",
    "其他": "meta",
    "杂项": "meta",
}


@dataclass(frozen=True)
class AuthorClassifiedSpec:
    """当前运行时的作者记忆分类（顺序影响默认检索回退顺序）。"""

    category_ids: tuple[str, ...]
    defs_by_id: dict[str, dict[str, str]]
    fallback_id: str


def sanitize_category_id(raw: str) -> str | None:
    s = (raw or "").strip().lower()
    return s if _CATEGORY_ID_SAFE.match(s) else None


def _inner_runtime(runtime_config: dict) -> dict:
    return runtime_config.get("runtime") or runtime_config


def get_author_classified_spec(runtime_config: dict | None) -> AuthorClassifiedSpec:
    """
    从 runtime 读取 author_classified_memory：
    - include_defaults（默认 true）：先内置 5 类，再追加 categories。
    - include_defaults: false：仅用 categories（须非空），适合完全自定义的小说类型维度。
    - categories: [{ id, label_zh?, hint? }, ...] 或 [ "id_only", ... ]
    - fallback_id：无法识别的 LLM 输出归入此类（须在最终 id 列表中）。
    """
    if not runtime_config:
        return _spec_from_defs(DEFAULT_CATEGORY_DEFS, "meta")

    raw = _inner_runtime(runtime_config).get("author_classified_memory")
    if not isinstance(raw, dict):
        return _spec_from_defs(DEFAULT_CATEGORY_DEFS, "meta")

    include_defaults = raw.get("include_defaults", True)
    if not isinstance(include_defaults, bool):
        include_defaults = bool(include_defaults)

    fallback_raw = sanitize_category_id(str(raw.get("fallback_id") or "meta") or "meta")
    custom = raw.get("categories") or []
    if not isinstance(custom, list):
        custom = []

    defs: dict[str, dict[str, str]] = {}
    ids_order: list[str] = []

    def add_from_def(d: dict[str, Any]) -> None:
        cid = sanitize_category_id(str(d.get("id", "")))
        if not cid:
            logger.warning("忽略非法 author_classified id: %s", d.get("id"))
            return
        if cid in defs:
            return
        label = str(d.get("label_zh") or d.get("label") or cid).strip()
        hint = str(d.get("hint") or "").strip()
        defs[cid] = {"label_zh": label, "hint": hint}
        ids_order.append(cid)

    if include_defaults:
        for d in DEFAULT_CATEGORY_DEFS:
            add_from_def(d)

    for item in custom:
        if isinstance(item, dict):
            add_from_def(item)
        elif isinstance(item, str):
            add_from_def({"id": item, "label_zh": item, "hint": ""})

    if not ids_order:
        logger.warning("author_classified_memory 无有效分类，使用内置默认")
        return _spec_from_defs(DEFAULT_CATEGORY_DEFS, "meta")

    fb = fallback_raw if fallback_raw and fallback_raw in defs else None
    if not fb:
        fb = "meta" if "meta" in defs else ids_order[-1]

    return AuthorClassifiedSpec(
        category_ids=tuple(ids_order),
        defs_by_id={k: dict(v) for k, v in defs.items()},
        fallback_id=fb,
    )


def _spec_from_defs(defs: list[dict[str, str]], fallback_id: str) -> AuthorClassifiedSpec:
    by: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for d in defs:
        cid = d["id"]
        order.append(cid)
        by[cid] = {
            "label_zh": d.get("label_zh", cid),
            "hint": d.get("hint", ""),
        }
    fb = fallback_id if fallback_id in by else order[-1]
    return AuthorClassifiedSpec(
        category_ids=tuple(order),
        defs_by_id=by,
        fallback_id=fb,
    )


def _classify_prompt_line_for_spec(spec: AuthorClassifiedSpec) -> str:
    parts: list[str] = []
    for cid in spec.category_ids:
        d = spec.defs_by_id.get(cid, {})
        label = d.get("label_zh", cid)
        hint = (d.get("hint") or "").strip()
        if hint:
            parts.append(f"{cid}（{label}：{hint}）")
        else:
            parts.append(f"{cid}（{label}）")
    return ", ".join(parts)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_author_memory_root(project_root: Path, runtime_config: dict) -> Path | None:
    """返回 book/memory/author_classified 的父目录（即 book/），便于拼子路径；无 data_root 时返回 None。"""
    try:
        from src.runtime.file_sync import get_book_root
    except ImportError:
        return None
    return get_book_root(Path(project_root), runtime_config)


def author_classified_base(book_root: Path) -> Path:
    return book_root / AUTHOR_MEMORY_SEG


def ensure_author_memory_layout(
    book_root: Path,
    runtime_config: dict | None = None,
) -> Path:
    """创建 memory/author_classified 及当前配置中的各分类目录与 README。"""
    spec = get_author_classified_spec(runtime_config)
    base = author_classified_base(book_root)
    base.mkdir(parents=True, exist_ok=True)
    readme = base / "README.md"
    lines = [
        "# author_classified 作者归类记忆",
        "",
        "分类列表由 `runtime.author_classified_memory` 决定；以下为当前应存在的子目录：",
        "",
    ]
    for cid in spec.category_ids:
        dinfo = spec.defs_by_id.get(cid, {})
        hint = (dinfo.get("hint") or "").strip()
        label = dinfo.get("label_zh", cid)
        lines.append(f"- `{cid}/` {label}" + (f" — {hint}" if hint else ""))
    lines.append("")
    readme.write_text("\n".join(lines), encoding="utf-8")

    for cid in spec.category_ids:
        d = base / cid
        d.mkdir(parents=True, exist_ok=True)
        idx = d / "README.md"
        if idx.is_file():
            continue
        dinfo = spec.defs_by_id.get(cid, {})
        hint = (dinfo.get("hint") or "").strip()
        label = dinfo.get("label_zh", cid)
        body = f"# {cid}\n\n{label}\n\n"
        if hint:
            body += f"{hint}\n\n"
        body += "本目录 `entries.md` 为追加日志。\n"
        idx.write_text(body, encoding="utf-8")
    return base


def _normalize_categories(raw: Any, spec: AuthorClassifiedSpec) -> list[str]:
    allowed = frozenset(spec.category_ids)
    fallback = spec.fallback_id
    out: list[str] = []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return [fallback]
    for x in raw:
        s = str(x).strip().lower()
        if s in allowed:
            out.append(s)
            continue
        s2 = _CATEGORY_ALIASES.get(str(x).strip(), "")
        if s2 and s2 in allowed:
            out.append(s2)
    return list(dict.fromkeys(out)) or [fallback]


def _extract_json_object(s: str) -> dict[str, Any] | None:
    s = (s or "").strip()
    if "```" in s:
        parts = re.split(r"```(?:json)?\s*", s, flags=re.IGNORECASE)
        for p in parts:
            p = p.strip()
            if p.startswith("{"):
                s = p
                break
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def classify_author_input(text: str, runtime_config: dict) -> dict[str, Any]:
    """
    调用 LLM 输出 JSON：categories, one_line, retrieval_query。
    失败或 Dummy 时归入 fallback_id，并仍返回结构化字段。
    """
    spec = get_author_classified_spec(runtime_config)
    fb = spec.fallback_id
    text = (text or "").strip()
    if not text:
        return {"categories": [fb], "one_line": "", "retrieval_query": ""}
    keys_line = _classify_prompt_line_for_spec(spec)
    prompt = (
        "你是写作项目记忆管理员。将下面「作者输入」归类到下列英文目录 key（可多选，至少一个）：\n"
        f"{keys_line}\n\n"
        "仅输出一个 JSON 对象，不要其它文字：\n"
        '{"categories":["setting","constraints"],'
        '"one_line":"一句话中文归纳",'
        '"retrieval_query":"供后续检索的短关键词句"}\n\n'
        f"作者输入：\n{text}"
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return {
                "categories": [fb],
                "one_line": text[:120] + ("…" if len(text) > 120 else ""),
                "retrieval_query": text[:80],
            }
        raw = provider.generate(prompt)
        data = _extract_json_object(raw) or {}
        cats = _normalize_categories(data.get("categories"), spec)
        return {
            "categories": cats,
            "one_line": str(data.get("one_line") or text[:120]).strip(),
            "retrieval_query": str(data.get("retrieval_query") or "").strip() or text[:80],
        }
    except Exception as e:
        logger.warning("classify_author_input LLM 失败，归入 fallback: %s", e)
        return {
            "categories": [fb],
            "one_line": text[:120] + ("…" if len(text) > 120 else ""),
            "retrieval_query": text[:80],
        }


def append_classified_entries(
    book_root: Path,
    scope_id: str,
    author_text: str,
    classified: dict[str, Any],
    runtime_config: dict | None = None,
) -> None:
    """将一条记录追加到各 categories 对应目录的 entries.md。"""
    spec = get_author_classified_spec(runtime_config)
    base = ensure_author_memory_layout(book_root, runtime_config)
    ts = _now_iso()
    one_line = classified.get("one_line") or ""
    rq = classified.get("retrieval_query") or ""
    block = (
        f"\n## {ts} | scope:{scope_id}\n"
        f"- 归纳：{one_line}\n"
        f"- 检索：{rq}\n"
        f"- 原文：\n\n{author_text}\n"
    )
    allowed = frozenset(spec.category_ids)
    fb = spec.fallback_id
    for cat in classified.get("categories") or [fb]:
        if cat not in allowed:
            cat = fb
        path = base / cat / "entries.md"
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        path.write_text(existing + block, encoding="utf-8")


def _tail_entries_file(path: Path, max_chars: int = 600) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    if len(text) <= max_chars:
        return text
    return "…\n" + text[-max_chars:]


def build_category_index_snippet(
    book_root: Path,
    runtime_config: dict | None = None,
    per_cat_chars: int = 220,
) -> str:
    """各分类 entries.md 尾部摘要，供渐进式第一步（选类）。"""
    spec = get_author_classified_spec(runtime_config)
    base = author_classified_base(book_root)
    if not base.is_dir():
        return "（尚无作者归类记忆）"
    parts: list[str] = []
    for cat in spec.category_ids:
        tail = _tail_entries_file(base / cat / "entries.md", max_chars=per_cat_chars)
        if tail:
            parts.append(f"### {cat}\n{tail}")
    return "\n\n".join(parts) if parts else "（各分类暂无条目）"


def select_categories_for_context(
    runtime_config: dict,
    scope_id: str,
    last_turn_summary: str,
    index_snippet: str,
) -> list[str]:
    """
    第二步：由 LLM 根据当前上下文与各类索引，决定加载顺序（ordered_categories）。
    失败时返回配置中的分类顺序（常用作优先级回退）。
    """
    spec = get_author_classified_spec(runtime_config)
    default_order = [c for c in spec.category_ids]

    if (
        not index_snippet.strip()
        or "各分类暂无条目" in index_snippet
        or "尚无作者归类记忆" in index_snippet
    ):
        return []
    keys_allowed = ", ".join(spec.category_ids)
    prompt = (
        "你是记忆检索策略器。下面有「各分类作者记忆」的近期摘要索引，以及当前写作上下文。\n"
        "请决定为「本回合写作前分析」应优先加载哪些分类（按重要顺序，只选有信息价值的）。\n"
        '仅输出 JSON：{"ordered_categories":["constraints","narrative",...],"reason":"一句中文"}\n'
        f"ordered_categories 只能从以下 key 中选（可留空数组）：{keys_allowed}。\n\n"
        f"范围 scope_id：{scope_id}\n"
        f"上一回合摘要：{(last_turn_summary or '（无）')[:800]}\n\n"
        "【分类索引】\n"
        f"{index_snippet[:6000]}"
    )
    allowed = frozenset(spec.category_ids)
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return list(default_order)
        raw = provider.generate(prompt)
        data = _extract_json_object(raw) or {}
        ordered = data.get("ordered_categories") or data.get("categories") or []
        if not isinstance(ordered, list):
            ordered = []
        out: list[str] = []
        for x in ordered:
            s = str(x).strip().lower()
            if s in allowed and s not in out:
                out.append(s)
        return out
    except Exception as e:
        logger.warning("select_categories_for_context 失败，使用默认顺序: %s", e)
        return list(default_order)


def load_author_memory_snippet(
    book_root: Path,
    ordered_categories: list[str],
    allowed_categories: frozenset[str],
    max_per_category: int = 900,
    max_total: int = 2800,
) -> str:
    """按顺序从各分类 entries.md 尾部截取，总长度封顶。"""
    base = author_classified_base(book_root)
    if not base.is_dir() or not ordered_categories:
        return ""
    chunks: list[str] = []
    total = 0
    for cat in ordered_categories:
        if cat not in allowed_categories:
            continue
        path = base / cat / "entries.md"
        piece = _tail_entries_file(path, max_chars=max_per_category)
        if not piece:
            continue
        block = f"【作者记忆/{cat}】\n{piece}"
        if total + len(block) > max_total:
            remain = max_total - total - 20
            if remain > 100:
                block = f"【作者记忆/{cat}】\n{piece[-remain:]}"
            else:
                break
        chunks.append(block)
        total += len(block) + 2
    return "\n\n".join(chunks).strip()


def progressive_author_memory_for_plan(
    project_root: Path,
    runtime_config: dict,
    scope_id: str,
    last_turn_summary: str,
) -> str:
    """
    渐进式：先拼索引 → LLM 选类 → 再加载对应文件尾部。
    无 book_root 或尚无文件时返回空串。
    """
    spec = get_author_classified_spec(runtime_config)
    allowed = frozenset(spec.category_ids)
    br = get_author_memory_root(project_root, runtime_config)
    if not br:
        return ""
    idx = build_category_index_snippet(br, runtime_config)
    if "各分类暂无条目" in idx or "尚无作者归类记忆" in idx:
        return ""
    ordered = select_categories_for_context(runtime_config, scope_id, last_turn_summary, idx)
    if not ordered:
        ordered = list(spec.category_ids)
    return load_author_memory_snippet(br, ordered, allowed_categories=allowed)


def format_recent_turns_for_display(storage: Any, scope_id: str, k: int = 3) -> str:
    """最近 k 条范围事件：摘要 + 正文预览，用于启动时展示。"""
    events = storage.get_recent_events(scope_id, k=max(1, min(k, 20)))
    if not events:
        return ""
    lines: list[str] = [f"## 正文进度（最近 {len(events)} 回合）", ""]
    for i, e in enumerate(events, start=1):
        if not isinstance(e, dict):
            lines.append(f"{i}. {str(e)[:300]}")
            continue
        summ = (e.get("summary") or e.get("text") or "").strip()
        body = (e.get("body") or "").strip()
        lines.append(f"### 回合 {i}")
        lines.append(f"- 摘要：{summ or '（无）'}")
        if body:
            preview = body[:400] + ("…" if len(body) > 400 else "")
            lines.append(f"- 正文预览：{preview}")
        lines.append("")
    return "\n".join(lines).strip()


def format_design_session_resume(
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
) -> str:
    """从 load_session_full 提取可读的「上次设定讨论」摘要。"""
    try:
        from src.author_loop.design_session_persistence import load_session_full
    except ImportError:
        return ""
    full = load_session_full(config_dir, project_root, runtime_config)
    if not full:
        return ""
    state = full.get("state_snapshot") or {}
    events = full.get("events") or []
    lines: list[str] = ["## 设定阶段：上次进展", ""]

    cd = state.get("current_discussion")
    if isinstance(cd, dict) and cd.get("rounds"):
        lines.append("- 进行中的讨论（未归档）：")
        if cd.get("initial_message"):
            lines.append(f"  - 初始想法：{str(cd['initial_message'])[:300]}")
        for r in cd.get("rounds", [])[-3:]:
            if isinstance(r, dict):
                lines.append(f"  - 作者：{str(r.get('author', ''))[:200]}")
                lines.append(f"    Agent：{str(r.get('agent', ''))[:400]}…")
        return "\n".join(lines)

    for ev in reversed(events):
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "discussion":
            lines.append("- 最近一次完整讨论：")
            if ev.get("initial_message"):
                lines.append(f"  - 初始：{str(ev['initial_message'])[:300]}")
            for r in (ev.get("rounds") or [])[-2:]:
                if isinstance(r, dict):
                    lines.append(f"  - 作者：{str(r.get('author', ''))[:200]}")
            return "\n".join(lines)
        if ev.get("type") == "summary":
            w = ev.get("world") or []
            lines.append("- 最近一次设定审阅摘要（世界要点）：")
            for x in w[:8]:
                lines.append(f"  - {x}")
            return "\n".join(lines)

    return "\n".join(lines) if len(lines) > 2 else ""


def print_startup_resume(
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
    storage: Any,
    scope_id: str,
    show_design_hint: bool,
    recent_turns_k: int = 3,
) -> None:
    """启动时打印到 stdout（设定摘要 + 最近回合进展）。"""
    if show_design_hint:
        d = format_design_session_resume(config_dir, project_root, runtime_config)
        if d:
            print("\n" + "=" * 60)
            print(d)
            print("=" * 60 + "\n")
    body_resume = format_recent_turns_for_display(storage, scope_id, k=recent_turns_k)
    if body_resume:
        print("\n" + "=" * 60)
        print(body_resume)
        print("=" * 60 + "\n")
