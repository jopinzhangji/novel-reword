"""
角色 Agent：输入 TurnContext，输出 CharacterTurnOutput（内心独白、言行）。
支持接 LLM（拼 prompt、检索记忆、解析）；无 LLM 或调用失败时回退壳输出。与 TECH_IMPLEMENTATION §3.2、第 13 项一致。
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.context import TurnContext


@dataclass
class CharacterTurnOutput:
    """角色单回合输出：内心独白、言行文本，可选 metadata。与 TECH §3.2 一致。
    reaction 为 U-6 回合内二次反应（先发批之后对在场他人公开言行的定向回应），随合并并入 dialogue_action/inner_monologue。"""
    inner_monologue: str = ""
    dialogue_action: str = ""
    metadata: dict[str, Any] | None = None
    reaction: str = ""


def _get_character_profile(characters_config: dict | None, character_id: str) -> dict:
    """从 characters_config 取指定角色的设定，用于拼 prompt。"""
    if not characters_config:
        return {}
    for c in characters_config.get("characters") or []:
        if c.get("id") == character_id:
            return dict(c)
    return {}


def _build_character_prompt(
    character_id: str,
    profile: dict,
    memory_snippet: str,
    ctx: TurnContext,
    info_view: str | None = None,
    growth_snippet: str | None = None,
) -> str:
    """拼角色回合 prompt：身份、记忆、场景。info_view 为该角色自身信息视野（§4.6），growth_snippet 为本角色成长状态（§2，阶段 1b/2 落盘）。"""
    name = profile.get("name") or character_id
    role = profile.get("role") or "角色"
    background = (profile.get("background") or "").strip()
    traits = profile.get("traits") or []
    goals = profile.get("goals") or {}
    short_goal = goals.get("short") if isinstance(goals, dict) else ""

    lines = [
        f"你是{name}，{role}。",
        f"背景：{background}" if background else "",
        f"性格/特点：{', '.join(traits)}" if traits else "",
        f"当前目标：{short_goal}" if short_goal else "",
        (growth_snippet or ""),
        "",
        "【你的记忆】",
        memory_snippet if memory_snippet else "（暂无记忆）",
        "",
        "【当前场景】",
        f"范围：{ctx.scope_id}，时间：{ctx.time}，地点：{ctx.place}。",
        ((f"【你的信息视野】\n{info_view}") if info_view else f"最近剧情：{ctx.shared_story_snippet or '（无）'}"),
        (ctx.secondary_characters_snippet or ""),
        "",
        "【写作前分析】落笔前请先完成：① 场景分析（当前场景、氛围、自己所在位置）；② 相关角色分析（本段中与自己有交集的角色及其状态）；③ 受害者/冲突方分析（若本段涉及冲突，谁受影响、自己处于何种立场）；④ 相关其他人员与生物（在场或即将出现的配角、生物）；⑤ 本段目标分析（自己在本段想达成的意图或反应）；⑥ 结合前文提要与设定，把握基调与风格；⑦ 分场景/分镜构思（本段自己的动作、对话、反应如何分步呈现）。",
        "",
        "【叙事节奏】剧情如画卷缓缓打开，本回合宜克制、具体：内心独白可写一瞬的感受或观察，言行可写一句短对话、一个细微动作或反应，不必在本回合达成重大行动或冲突。",
        "",
        "上述成长状态与目标会影响你的言行与内心——但角色不应主动张口念出自己成长状态的名目，而是在分析、判断、选择时自然地体现这些状态。请你在此基础上按以下两行格式输出：",
        "内心独白：...",
        "言行：...",
    ]
    return "\n".join(l for l in lines if l is not None)


def _parse_character_llm_response(raw: str) -> tuple[str, str]:
    """从 LLM 回复中解析内心独白与言行。要求含「内心独白：」「言行：」。"""
    inner = ""
    dialogue = ""
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("内心独白："):
            inner = line[len("内心独白：") :].strip()
        elif line.startswith("言行："):
            dialogue = line[len("言行：") :].strip()
    if not inner and not dialogue:
        inner = raw.strip()[:200] if raw else "（壳）暂无内心独白"
        dialogue = "（壳）暂无言行"
    return inner or "（壳）暂无内心独白", dialogue or "（壳）暂无言行"


class CharacterAgent:
    """
    角色 Agent：绑定 character_id；若注入 storage、runtime_config、characters_config 则 turn() 中调 LLM，否则壳输出。
    """

    def __init__(
        self,
        character_id: str,
        *,
        storage: Any = None,
        runtime_config: dict | None = None,
        characters_config: dict | None = None,
        data_root: Path | None = None,
    ) -> None:
        self.character_id = character_id
        self._storage = storage
        self._runtime_config = runtime_config or {}
        self._characters_config = characters_config or {}
        self._data_root = data_root

    def turn(self, ctx: TurnContext) -> CharacterTurnOutput:
        """单回合：有 LLM 时拼 prompt、检索记忆、调用 LLM 并解析；否则返回壳输出。"""
        metadata = {"character_id": self.character_id, "scope_id": ctx.scope_id}

        try:
            from src.llm import get_llm_provider
            provider = get_llm_provider(self._runtime_config)
            if provider.__class__.__name__ == "DummyLLM":
                return CharacterTurnOutput(
                    inner_monologue="（壳）暂无内心独白",
                    dialogue_action="（壳）暂无言行",
                    metadata=metadata,
                )
            memory_snippet = ""
            if self._storage:
                from src.retrieval import retrieve_character_memory
                include_layers = bool(
                    (self._runtime_config.get("agents") or {}).get("characters", {}).get("memory_layers", False)
                )
                memory_snippet = retrieve_character_memory(
                    self._storage, self.character_id, include_layers=include_layers
                )
            # 信息视野（§4.6）：有 storage 时用该角色自身可见事件视图，替代全量 scope 摘要，防上帝视角。
            info_view: str | None = None
            if self._storage:
                from src.retrieval import build_character_event_view
                info_view = build_character_event_view(self._storage, self.character_id, scope_id=ctx.scope_id)
            growth_snippet: str | None = None
            if self._data_root:
                from src.runtime.character_growth import load_growth_state, format_growth_snippet
                state = load_growth_state(self.character_id, self._data_root)
                growth_snippet = format_growth_snippet(state)
                if not growth_snippet:
                    growth_snippet = None
            if self._data_root:
                from src.runtime.relationship_graph import load_graph, relationship_graph_yaml_path
                from src.retrieval.relationship import format_relation_snippet

                gpath = relationship_graph_yaml_path(Path(self._data_root))
                if gpath.is_file():
                    graph = load_graph(gpath)
                    rel_snippet = format_relation_snippet(graph, self.character_id, limit=8)
                    if rel_snippet:
                        label = "【关系图谱（持久化快照，截至上一回合）】"
                        memory_snippet = f"{memory_snippet}\n\n{label}\n{rel_snippet}" if memory_snippet else f"{label}\n{rel_snippet}"
            profile = _get_character_profile(self._characters_config, self.character_id)
            prompt = _build_character_prompt(
                self.character_id, profile, memory_snippet, ctx,
                info_view=info_view, growth_snippet=growth_snippet,
            )
            raw = provider.generate(prompt)
            inner, dialogue = _parse_character_llm_response(raw)
            return CharacterTurnOutput(
                inner_monologue=inner,
                dialogue_action=dialogue,
                metadata=metadata,
            )
        except Exception:
            return CharacterTurnOutput(
                inner_monologue="（壳）暂无内心独白",
                dialogue_action="（壳）暂无言行",
                metadata=metadata,
            )

    def react_to_peers(self, ctx: TurnContext, peers_snippet: str) -> CharacterTurnOutput:
        """
        U-6 回合内二次反应：本回合先发批之后，对**在场其他角色**的公开言行（peers_snippet）做一段简短定向回应。
        peers_snippet 只含他人 dialogue_action（在场可闻的公开言行），不注入他人 inner_monologue——不泄私有内心，与 §4.6 一致。
        DummyLLM / 异常 → 返回空 reaction（不产生二次批）。
        """
        metadata = {"character_id": self.character_id, "scope_id": ctx.scope_id, "phase": "react"}
        try:
            from src.llm import get_llm_provider
            provider = get_llm_provider(self._runtime_config)
            if provider.__class__.__name__ == "DummyLLM":
                return CharacterTurnOutput(metadata=metadata)
            profile = _get_character_profile(self._characters_config, self.character_id)
            name = profile.get("name") or self.character_id
            prompt_lines = [
                f"你是{name}（{self.character_id}）。",
                "本回合你已先行说过话；现在你又听到在场其他角色的公开言行：",
                (peers_snippet or "（其他人尚未言语）"),
                "",
                "请据此，对其中与你相关的一人，给出一段简短、具体、贴合自己性格与处境的回应（一句内心感受或一句对话/动作，不必长篇）。",
                "只输出以下两行：",
                "内心独白：...",
                "言行：...",
            ]
            raw = provider.generate("\n".join(prompt_lines))
            inner, dialogue = _parse_character_llm_response(raw)
            reaction = "、".join(x for x in [inner, dialogue] if x and not x.startswith("（壳）"))
            return CharacterTurnOutput(
                inner_monologue=inner,
                dialogue_action=dialogue,
                metadata=metadata,
                reaction=reaction or "",
            )
        except Exception:
            return CharacterTurnOutput(metadata=metadata)
