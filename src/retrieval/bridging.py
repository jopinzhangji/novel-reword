"""
G1 屏外线 / 并列主线桥接摘要（SDD D10，phase G1b）。

桥接 = 当主书下一场景依赖某**非在场**角色屏外结果时，向正文生成注入的一段短摘要。
来源为该角色屏外记忆（off_screen / parallel_thread 条目），按预算字符截断；**不**灌副线全文。
默认关闭（`parallel_threads.enabled=false`）；开启后由 `bridge_ids` 明示需要桥接的角色。
"""
from __future__ import annotations

from typing import Any

from src.runtime.memory_layers import THREAD_OFF_SCREEN

DEFAULT_BRIDGE_BUDGET_CHARS = 400
DEFAULT_BRIDGE_ENTRY_LIMIT = 3


def format_bridging_snippet(
    entries: list[dict[str, Any]],
    name: str = "",
    budget_chars: int = DEFAULT_BRIDGE_BUDGET_CHARS,
) -> str:
    """
    把某角色最近屏外线条目格式化为 prompt 桥接块 `【桥接摘要（<name> 屏外结果）】`。
    截断到 budget_chars（预留精简）；空条目不返回（不改变无桥接场景行为）。
    """
    summaries = [str(e.get("summary") or e.get("plan") or "").strip() for e in entries]
    summaries = [s for s in summaries if s]
    if not summaries:
        return ""
    label = f"【桥接摘要（{name} 屏外结果）】" if name else "【桥接摘要（屏外结果）】"
    body = label + "\n" + "\n".join("- " + s for s in summaries)
    if budget_chars and len(body) > budget_chars:
        body = body[: max(0, budget_chars)] + "…"
    return body


def build_bridging_snippet_from_storage(
    storage: Any,
    present_character_ids: list[str] | tuple[str, ...],
    parallel_threads_cfg: dict[str, Any] | None = None,
    characters_config: dict[str, Any] | None = None,
    *,
    budget_chars: int = DEFAULT_BRIDGE_BUDGET_CHARS,
) -> str:
    """
    从 Storage 屏外记忆组装桥接摘要。默认关闭（enabled=false 或未给 bridge_ids → 空串）。
    - `bridge_ids`：主书需要其屏外结果的非在场角色（明示，避免自动灌全员）。
    - 已在场的角色**跳过**（其屏外结果不用于本场景，符合 §5.3 主书仍主角轴）。
    - 无 storage 取屏外能力或无可桥接条目时返回空串。
    """
    cfg = parallel_threads_cfg or {}
    if not bool(cfg.get("enabled", False)):
        return ""
    bridge_ids = [str(x) for x in (cfg.get("bridge_ids") or []) if x]
    if not bridge_ids:
        return ""
    config = (characters_config or {}).get("characters") or []
    name_of = {str(c.get("id")): (c.get("name") or str(c.get("id"))) for c in config}
    present = {str(x) for x in present_character_ids if x}
    if not hasattr(storage, "get_recent_off_screen"):
        return ""
    limit = int(cfg.get("bridge_entry_limit", DEFAULT_BRIDGE_ENTRY_LIMIT))
    blocks: list[str] = []
    for cid in bridge_ids:
        if cid in present:
            continue
        entries = storage.get_recent_off_screen(cid, thread=THREAD_OFF_SCREEN, limit=limit)
        snippet = format_bridging_snippet(entries, name=name_of.get(cid, cid), budget_chars=budget_chars)
        if snippet:
            blocks.append(snippet)
    return "\n\n".join(blocks)