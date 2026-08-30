"""
信息视野 / 感知不对称（设计文档 §4.6；阶段 1a）。

关键角色不再看到全量 scope 事件流，只看到其"亲身经历/知情"的事件；未知部分只计数、不泄内容，
从而产生差异化解读。这是"关键角色独立演进"的机制本体。
可见性判定：`present_characters` 含该角色，或 `visibility == "public"`。
"""
from __future__ import annotations

from typing import Any, Iterable


def event_visible_to_character(entry: dict[str, Any], character_id: str) -> bool:
    """
    该事件是否对 character_id 可见。
    - 事件显式声明 `visibility=="public"`：对任何角色可见；
    - 事件带 `present_characters`（本回合在场角色）：仅在场角色可见；
    - 事件两者皆无（旧数据/未打标签）：默认可见（兼容，不做剧透收缩）。
    """
    entry = entry or {}
    if entry.get("visibility") == "public":
        return True
    present = entry.get("present_characters") or []
    if present:
        return character_id in {str(c) for c in present}
    return True


def count_events(storage: Any, scope_id: str | None, events_limit: int = 0) -> int:
    """统计某 scope 事件总数；scope 缺省时遍历所有已知 scope。"""
    if scope_id is not None:
        return len(storage.get_recent_events(scope_id, k=events_limit) if events_limit else storage.get_recent_events(scope_id))
    total = 0
    cursor = getattr(storage, "_scope_events", None)
    for sid in cursor or {}:
        total += len(storage.get_recent_events(sid))
    return total


def iter_events_by_scope(storage: Any, scope_id: str | None) -> Iterable[tuple[str, list[dict[str, Any]]]]:
    """按 scope 产出 (scope_id, events) 迭代对。scope 缺省时遍历所有已有 scope。"""
    if scope_id is not None:
        yield scope_id, storage.get_recent_events(scope_id)
        return
    cursor = getattr(storage, "_scope_events", {})
    for sid in dict(cursor or {}):
        yield sid, storage.get_recent_events(sid)


def _event_text(entry: dict[str, Any]) -> str:
    return (entry.get("summary") or entry.get("text") or str(entry)).strip()


def build_character_event_view(
    storage: Any,
    character_id: str,
    scope_id: str | None = None,
    events_limit: int = 5,
) -> str:
    """
    生成该角色"你的信息视野"文本：只含其可见事件，格式化为最近 N 件亲身经历/知情的事实；
    对不可见事件只计数（不泄内容）。无可见事件时给占位。
    """
    known: list[str] = []
    unknown_count = 0
    for sid, events in iter_events_by_scope(storage, scope_id):
        window = events[-events_limit:] if events_limit else events
        for entry in window:
            if event_visible_to_character(entry, character_id):
                text = _event_text(entry)
                prefix = f"[{sid}]" if text else ""
                known.append((prefix + " " + text).strip() if prefix else text)
            else:
                unknown_count += 1
    if not known:
        return "（你对最近一段剧情没有亲身经历或知情记录；你不在场发生的部分，你并不知道其细节。）"
    lines = ["你亲身经历/知情的最近事件：", *[f"- {t}" for t in known]]
    if unknown_count:
        lines.append(f"（另有 {unknown_count} 起你未亲身参与的事件不在你的信息视野内。）")
    return "\n".join(lines)


def format_unknown_hint(character_id: str, scope_id: str | None, known_count: int, unknown_count: int) -> str:
    """未知剧情占位文案，供 prompt 在无视图/部分视图时提示角色不虚构。"""
    parts = []
    if unknown_count:
        parts.append(f"你未亲身参与的 {unknown_count} 起事件，你并不知情其细节。")
    if not known_count:
        parts.append("你当前对这段剧情没有直接经历；若有猜测请显式标注为推测。")
    return " ".join(parts) if parts else ""