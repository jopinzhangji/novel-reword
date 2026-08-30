"""
记忆与事件检索：从 Storage 读取角色私有记忆与范围事件，格式化为可注入 LLM prompt 的文本。
与 TECH_IMPLEMENTATION §7（键结构）、§10（记忆与事件检索）一致。
"""
from typing import Any


def retrieve_character_memory(
    storage: Any,
    character_id: str,
    events_limit: int = 10,
    relations_limit: int = 20,
    include_profile: bool = True,
    include_layers: bool = False,
) -> str:
    """
    检索某角色的私有记忆（profile、relations、events），拼接为一段文本，供角色 Agent 生成时注入 prompt。
    storage 需实现 get_profile、get_relations、get_events（如 MemoryStorage）。
    include_layers=True 时追加 L2 解释（[解释（L2）]）与 L3 短期策略（[短期计划（L3）]）——§4 记忆分层检索；storage 需实现 get_interpretations/get_active_strategies。
    """
    parts = []
    if include_profile:
        profile = storage.get_profile(character_id)
        if profile:
            parts.append("[人物设定] " + _format_dict(profile))
    relations = storage.get_relations(character_id)
    if relations:
        take = relations[-relations_limit:] if relations_limit else relations
        parts.append("[关系] " + " | ".join(_format_relation(e) for e in take))
    events = storage.get_events(character_id, limit=events_limit)
    if events:
        parts.append("[事件提炼] " + " | ".join(_format_event(e) for e in events))
    if include_layers:
        layers_parts = []
        if hasattr(storage, "get_interpretations"):
            interp = storage.get_interpretations(character_id)
            if interp:
                layers_parts.append("[解释（L2）] " + " | ".join(_format_event(e) for e in interp))
        if hasattr(storage, "get_active_strategies"):
            strat = storage.get_active_strategies(character_id)
            if strat:
                layers_parts.append("[短期计划（L3）] " + " | ".join(_format_event(e) for e in strat))
        parts.extend(layers_parts)
    if not parts:
        return ""
    return "\n".join(parts)


def _format_dict(d: dict) -> str:
    return " ".join(f"{k}={v}" for k, v in d.items() if v)


def _format_relation(e: dict) -> str:
    if isinstance(e, dict):
        target = e.get("target_id") or e.get("target", "")
        rel_type = e.get("type") or e.get("relation", "")
        return f"{target}:{rel_type}" if target or rel_type else str(e)
    return str(e)


def _format_event(e: dict) -> str:
    if isinstance(e, dict) and e.get("summary"):
        return e["summary"]
    return str(e)


def format_scope_events_snippet(storage: Any, scope_id: str, k: int = 10) -> str:
    """
    从 Storage 取指定范围最近 k 条事件，格式化为一段摘要文本（与 build_turn_context_from_storage 中逻辑一致）。
    供 ScopeAgent 或编排器组装 shared_story_snippet 时复用。正文仅存于事件中，需完整正文时用 get_turn_body_from_storage。
    """
    events = storage.get_recent_events(scope_id, k=k)
    if not events:
        return ""
    parts = []
    for e in events:
        if isinstance(e, dict) and ("summary" in e or "text" in e):
            parts.append(e.get("summary") or e.get("text") or str(e))
        else:
            parts.append(str(e))
    return " | ".join(parts) if parts else ""


def get_turn_body_from_storage(
    storage: Any,
    scope_id: str,
    index_from_end: int = 0,
) -> str:
    """
    从记忆（storage）中取指定范围某回合的正文，保证与持久化一致、单一数据源。
    index_from_end=0 表示最近一条，1 表示倒数第二条。
    """
    events = storage.get_recent_events(scope_id, k=index_from_end + 1)
    if not events or len(events) <= index_from_end:
        return ""
    e = events[-(1 + index_from_end)]
    if isinstance(e, dict) and e.get("body"):
        return (e["body"] or "").strip()
    return ""


def format_secondary_characters_snippet(
    storage: Any,
    scope_id: str | None = None,
    limit: int = 30,
) -> str:
    """
    从 Storage 取次要角色列表，格式化为可注入 prompt 的文本，供 ScopeAgent/CharacterAgent 查阅。
    配置中仅关键角色；小说中其余角色可动态加入此列表（如写戏时生成「村长」「猎户老陈」等）。
    storage 需实现 get_secondary_characters(scope_id, limit)。
    """
    if not hasattr(storage, "get_secondary_characters"):
        return ""
    entries = storage.get_secondary_characters(scope_id=scope_id, limit=limit)
    if not entries:
        return "（暂无其他角色记录；可自由生成本场景/世界中的配角并写入次要角色列表供后续查阅）"
    parts = []
    for e in entries:
        name = e.get("name") or e.get("id") or "未命名"
        brief = e.get("brief") or e.get("description") or ""
        parts.append(f"{name}：{brief}" if brief else name)
    return "本场景/世界中已出现的其他角色（供参考）：" + "；".join(parts)
