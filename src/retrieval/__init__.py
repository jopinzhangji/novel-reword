# 记忆与事件检索：从 Storage 按角色/范围取最近记忆与事件，格式化为可注入 prompt 的文本。
# 与 TECH_IMPLEMENTATION §7、§10 一致；供 Agent 接 LLM 时组装上下文。
from .memory import (
    retrieve_character_memory,
    format_scope_events_snippet,
    format_secondary_characters_snippet,
)
from .relationship import (
    get_relation,
    get_neighbors,
    get_relation_change_log,
    format_relation_snippet,
)
from .info_view import (
    event_visible_to_character,
    build_character_event_view,
    format_unknown_hint,
)

__all__ = [
    "retrieve_character_memory",
    "format_scope_events_snippet",
    "format_secondary_characters_snippet",
    "get_relation",
    "get_neighbors",
    "get_relation_change_log",
    "format_relation_snippet",
    "event_visible_to_character",
    "build_character_event_view",
    "format_unknown_hint",
]
