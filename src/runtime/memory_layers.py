"""
三层记忆（§4）确定性分类与条目构造（阶段 2 写入校验前置；无 LLM）。

定义：
- L1 事实层：不可篡改（发生了什么）。
- L2 解释层：可随认知更新（我如何理解/立场）。
- L3 策略层：可过期（我下一步打算/计划）。
用关键词启发式把角色本回合言行有条理地归入 L2/L3（L1 为默认事实卡，已在 apply_memory_write 落库）。
"""
from __future__ import annotations

from typing import Any

# L3 命中即策略/计划；需要解释层与事实层的词分开判。
_L3_KEYWORDS = (
    "计划", "打算", "准备", "下一步", "决意", "部署", "安排", "暂定",
    "先…再", "提防", "预备", "将要去", "正欲", "盘算",
)
_L2_KEYWORDS = (
    "觉得", "认为", "怀疑", "判断", "理解", "明白", "意识到", "警惕",
    "信任", "敌意", "好感", "猜想", "回味", "认定", "预感", "不悦",
)

# G1 屏外线记忆类型（与 layer 正交；outline-and-beats §2.2 平行主线）：
THREAD_OFF_SCREEN = "off_screen"        # 未入场时的屏外独立活动
THREAD_PARALLEL = "parallel_thread"     # 同世界观下另一条并列主线（可导出番外）


def classify_memory_layer(summary: str) -> str:
    """
    返回 "L1"/"L2"/"L3"：命中 L3 计划词 → L3；命中 L2 解释/立场词 → L2；否则 → L1。
    """
    text = (summary or "").strip()
    if not text:
        return "L1"
    for kw in _L3_KEYWORDS:
        if kw in text:
            return "L3"
    for kw in _L2_KEYWORDS:
        if kw in text:
            return "L2"
    return "L1"


def interpretation_subject(summary: str, max_len: int = 12) -> str:
    """取 L2 条目 upsert 键：去常见第一人称/判断前缀，截短主体；空给 "general"。"""
    text = (summary or "").strip()
    for pref in ("我觉得", "我认为", "我意识到", "我判断", "我方", "在下觉得"):
        if text.startswith(pref):
            text = text[len(pref):]
            break
    text = text.strip(" ，。；：,.:-")
    if not text or text in ("我", "俺", "本座"):
        return "general"
    return text[:max_len]


def strategy_expires_turn(turn_index: int, ttl: int = 5) -> int:
    """L3 策略过期回合 = 当前回合 + ttl。"""
    return int(turn_index or 0) + max(1, int(ttl))


def build_layer_entry(
    summary: str,
    layer: str,
    *,
    scope_id: str = "",
    turn_index: int | None = None,
    time: str = "",
    place: str = "",
    ttl: int = 5,
    thread: str = "",
) -> dict[str, Any]:
    """构造 L2/L3 记忆条目（带 §4.2 统一标签）。L2→subject；L3→plan+expires_turn。
    `thread`（G1）为去 `off_screen`/`parallel_thread`，非空时写入条目，标识屏外/并列主线记忆。"""
    summary = (summary or "").strip()
    base: dict[str, Any] = {
        "layer": layer,
        "scope_id": scope_id,
        "turn_index": turn_index,
        "time": time,
        "place": place,
        "impact_level": "med",
    }
    if thread:
        base["thread"] = thread
    if layer == "L2":
        base["subject"] = interpretation_subject(summary)
        base["statement"] = (summary or "")[:200]
    elif layer == "L3":
        base["plan"] = (summary or "")[:200]
        base["expires_turn"] = strategy_expires_turn(turn_index if turn_index is not None else 0, ttl)
    return base