# 共享上下文：当前场景、已发生事件、时间/地点、在场角色
# TurnContext 为只读，由编排器构建，供 ScopeAgent / CharacterAgent 单回合使用。
# 与 TECH_IMPLEMENTATION §6、§9 一致。

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TurnContext:
    """
    单回合只读上下文：当前范围、时间、地点、在场角色、上一回合摘要等。
    所有本回合被调用的 Agent 收到同一份 TurnContext。
    present_character_ids 为配置中的关键角色；次要角色列表见 secondary_characters_snippet，供 Agent 自由查阅。
    """
    scope_id: str
    time: str
    place: str
    present_character_ids: tuple[str, ...]
    last_turn_summary: str = ""
    shared_story_snippet: str | None = None
    world_constraints: str | None = None
    secondary_characters_snippet: str | None = None
    present_growth_snippet: str = ""

    def __post_init__(self) -> None:
        if not self.scope_id:
            raise ValueError("scope_id 不能为空")
        if not isinstance(self.present_character_ids, (list, tuple)):
            raise ValueError("present_character_ids 必须为 list 或 tuple")


def build_turn_context(
    scope_id: str,
    time: str,
    place: str,
    present_character_ids: list[str] | tuple[str, ...],
    last_turn_summary: str = "",
    shared_story_snippet: str | None = None,
    world_constraints: str | None = None,
    secondary_characters_snippet: str | None = None,
    present_growth_snippet: str = "",
) -> TurnContext:
    """
    从显式参数构建 TurnContext。
    编排器在决定当前场景（scope、时间、地点、在场角色）后调用此函数。
    """
    ids = tuple(present_character_ids) if isinstance(present_character_ids, list) else present_character_ids
    return TurnContext(
        scope_id=scope_id,
        time=time,
        place=place,
        present_character_ids=ids,
        last_turn_summary=last_turn_summary or "",
        shared_story_snippet=shared_story_snippet,
        world_constraints=world_constraints,
        secondary_characters_snippet=secondary_characters_snippet,
        present_growth_snippet=present_growth_snippet,
    )


def build_turn_context_from_storage(
    scope_id: str,
    time: str,
    place: str,
    present_character_ids: list[str] | tuple[str, ...],
    storage: Any,
    world_config: dict | None = None,
    last_turn_summary: str = "",
    recent_events_k: int = 5,
    secondary_characters_limit: int = 30,
    present_growth_snippet: str = "",
) -> TurnContext:
    """
    从 Storage 与可选世界配置组装 TurnContext。
    - 从 storage.get_recent_events(scope_id, k) 取最近事件，格式化为 shared_story_snippet（若为空则用 last_turn_summary 补足）。
    - 从 storage 取次要角色列表，格式化为 secondary_characters_snippet，供 Agent 查阅（配置仅关键角色，其余角色可自由生成并写入该列表）。
    - world_constraints 暂不填充，可由后续 ScopeAgent 预跑或协调者写入。
    """
    snippet = last_turn_summary or ""
    try:
        events = storage.get_recent_events(scope_id, k=recent_events_k)
        if events:
            parts = []
            for e in events[-recent_events_k:]:
                if isinstance(e, dict) and ("summary" in e or "text" in e):
                    parts.append(e.get("summary") or e.get("text") or str(e))
                else:
                    parts.append(str(e))
            if parts:
                joined = " | ".join(parts)
                snippet = (snippet + " | " + joined) if snippet else joined
    except Exception:
        pass
    secondary_snippet = None
    try:
        from src.retrieval import format_secondary_characters_snippet
        secondary_snippet = format_secondary_characters_snippet(
            storage, scope_id=scope_id, limit=secondary_characters_limit
        )
    except Exception:
        pass
    return build_turn_context(
        scope_id=scope_id,
        time=time,
        place=place,
        present_character_ids=present_character_ids,
        last_turn_summary=last_turn_summary,
        shared_story_snippet=snippet or None,
        world_constraints=None,
        secondary_characters_snippet=secondary_snippet,
        present_growth_snippet=present_growth_snippet,
    )
