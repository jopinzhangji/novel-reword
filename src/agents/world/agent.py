"""
范围 Agent：输入 TurnContext（含 scope_id），输出 ScopeTurnOutput（约束、事件摘要）。
支持接 LLM（拼 prompt、检索事件、解析）；无 LLM 或调用失败时回退壳输出。与 TECH_IMPLEMENTATION §3.2、第 13 项一致。
"""
from dataclasses import dataclass
from typing import Any

from src.context import TurnContext


@dataclass
class ScopeTurnOutput:
    """范围单回合输出：约束列表、本回合正文（或事件摘要），可选 state_delta。与 TECH §3.2 一致。"""
    constraints: list[str]
    event_summary: str  # 本回合正文（多行叙述）或事件摘要，下游作 scope 段使用
    state_delta: dict[str, Any] | None = None


def _get_scope_info(world_config: dict | None, scope_id: str) -> dict:
    """从 world_config 取指定范围的设定，用于拼 prompt。"""
    if not world_config:
        return {}
    for s in world_config.get("scopes") or []:
        if s.get("id") == scope_id:
            return dict(s)
    return {}


def _build_scope_prompt(
    scope_id: str,
    scope_info: dict,
    events_snippet: str,
    ctx: TurnContext,
    main_characters_snippet: str = "",
) -> str:
    """拼范围回合 prompt：场景、主角/主要角色、最近事件、次要角色。"""
    name = scope_info.get("name") or scope_id
    desc = (scope_info.get("description") or "").strip()
    lines = [
        f"你是范围「{name}」（{scope_id}）的叙事者。",
        f"场景：{ctx.place}，时间：{ctx.time}。",
        f"场景说明：{desc}" if desc else "",
    ]
    if main_characters_snippet:
        lines.extend(["", main_characters_snippet])
    if ctx.present_growth_snippet:
        lines.extend(["", ctx.present_growth_snippet])
    lines.extend([
        "",
        "【最近事件】",
        events_snippet if events_snippet else "（暂无）",
        f"最近剧情：{ctx.shared_story_snippet or '（无）'}",
        (ctx.secondary_characters_snippet or ""),
        "",
        "【写作前分析】落笔前请先完成以下分析（可简要列出或心中推演）：① 场景分析（时间、地点、环境、氛围）；② 相关角色分析（本段涉及的主要角色及其状态）；③ 受害者/冲突方分析（若有冲突或危机，谁受影响、施动方）；④ 相关其他人员与生物（在场或相关的配角、生物、势力）；⑤ 本段目标分析（本段要推进的情节目标或情绪目标）；⑥ 结合前文提要与设定，确定基调与风格（如紧张/舒缓、写实/写意等）；⑦ 分场景构思（本段内若有多个小场景，各自写什么）。",
        "",
        "【叙事节奏】开篇宜如画卷徐徐展开，不要推进过快。本回合只推进一小步：可写氛围、环境细节、人物的一个反应或一个微小变化，避免一次性爆发重大冲突或塞入过多情节。",
        "",
        "请在上述分析基础上，最后按以下格式输出：",
        "约束：...（一行或列表，本段叙事约束）",
        "本回合正文：...（本回合的场景/事件叙述正文，一段成文，可多行，建议控制篇幅）",
    ])
    return "\n".join(l for l in lines if l is not None)


def _parse_scope_llm_response(raw: str) -> tuple[list[str], str]:
    """从 LLM 回复中解析约束列表与本回合正文（存于 event_summary 字段）。"""
    constraints: list[str] = []
    event_summary = ""
    in_constraints = False
    in_body = False
    body_lines: list[str] = []
    for line in raw.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("约束："):
            in_constraints = True
            in_body = False
            if body_lines:
                event_summary = "\n".join(body_lines).strip()
                body_lines = []
            rest = line_stripped[3:].strip()
            if rest:
                constraints = [c.strip() for c in rest.replace("、", " ").split() if c.strip()]
        elif "本回合正文" in line_stripped or line_stripped.startswith("本回合事件摘要："):
            in_constraints = False
            in_body = True
            sep = "：" if "：" in line_stripped else ":"
            rest = (line_stripped.split(sep, 1)[-1] if sep in line_stripped else line_stripped).strip()
            body_lines = [rest] if rest else []
        elif in_body and line_stripped:
            body_lines.append(line_stripped)
        elif in_constraints and line_stripped:
            constraints.append(line_stripped)
        elif not in_body and event_summary and line_stripped:
            event_summary += " " + line_stripped
    if body_lines:
        event_summary = "\n".join(body_lines).strip()
    if not constraints:
        constraints = ["（壳）无额外约束"]
    if not event_summary:
        event_summary = raw.strip()[:500] if raw else "（壳）本回合无正文"
    return constraints, event_summary


class ScopeAgent:
    """
    范围 Agent：绑定 scope_id；若注入 storage、runtime_config、world_config 则 turn() 中调 LLM，否则壳输出。
    """

    def __init__(
        self,
        scope_id: str,
        *,
        storage: Any = None,
        runtime_config: dict | None = None,
        world_config: dict | None = None,
        characters_config: dict | None = None,
    ) -> None:
        self.scope_id = scope_id
        self._storage = storage
        self._runtime_config = runtime_config or {}
        self._world_config = world_config or {}
        self._characters_config = characters_config

    def turn(self, ctx: TurnContext) -> ScopeTurnOutput:
        """单回合：有 LLM 时拼 prompt、检索事件、调用 LLM 并解析；否则返回壳输出。"""
        try:
            from src.llm import get_llm_provider
            provider = get_llm_provider(self._runtime_config)
            if provider.__class__.__name__ == "DummyLLM":
                return ScopeTurnOutput(
                    constraints=["（壳）无额外约束"],
                    event_summary="（壳）本回合无事件摘要",
                    state_delta=None,
                )
            events_snippet = ""
            if self._storage:
                from src.retrieval import format_scope_events_snippet
                events_snippet = format_scope_events_snippet(self._storage, self.scope_id, k=10)
            scope_info = _get_scope_info(self._world_config, self.scope_id)
            main_characters_snippet = ""
            if self._characters_config:
                from src.runtime.protagonist import format_main_characters_snippet
                main_characters_snippet = format_main_characters_snippet(
                    self._runtime_config, self._characters_config
                )
            prompt = _build_scope_prompt(
                self.scope_id, scope_info, events_snippet, ctx,
                main_characters_snippet=main_characters_snippet,
            )
            raw = provider.generate(prompt)
            constraints, event_summary = _parse_scope_llm_response(raw)
            return ScopeTurnOutput(
                constraints=constraints,
                event_summary=event_summary,
                state_delta=None,
            )
        except Exception:
            return ScopeTurnOutput(
                constraints=["（壳）无额外约束"],
                event_summary="（壳）本回合无事件摘要",
                state_delta=None,
            )
