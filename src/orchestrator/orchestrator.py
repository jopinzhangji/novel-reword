"""
编排器：加载配置、创建 Agent、单回合流程（下发 Context → 并行调用 → 收集 → 写回事件簿/状态）。
写回拆为「事件簿/状态」与「记忆」两段，中间留作者确认点；本实现先写事件簿/状态，记忆写回由调用方或后续作者确认后执行。
若 runtime.storage.data_root 已配置，则双写到该目录（content/turns、memory/），见 docs/design/memory-storage-and-retrieval.md。
与 TECH_IMPLEMENTATION §6 一致。
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import load_all_config

logger = logging.getLogger(__name__)
from src.context import build_turn_context_from_storage, TurnContext
from src.agents.character import CharacterAgent, CharacterTurnOutput
from src.agents.world import ScopeAgent, ScopeTurnOutput
from src.runtime.storage import MemoryStorage
from src.runtime import file_sync
from src.runtime.relationship_graph import sync_relationship_graph_after_scope_turn


@dataclass
class TurnResult:
    """单回合结果：Scope 输出、各角色输出，供作者审阅或写回记忆。可选 body_narrative 为本回合小说正文（≤2000 字），有则写回时优先使用。"""
    scope_output: ScopeTurnOutput
    character_outputs: dict[str, CharacterTurnOutput] = field(default_factory=dict)
    body_narrative: str | None = None  # 基于写作前分析生成的本回合正文，作者同意分析后生成


def resolve_turn_conflict(
    scope_output: ScopeTurnOutput,
    character_outputs: dict[str, CharacterTurnOutput],
) -> str:
    """
    冲突裁决（简单规则）：将 Scope 事件摘要与各角色言行合并为一条本回合事件摘要。
    规则：scope.event_summary 在前，再按 character_id 字典序追加各角色 dialogue_action，用 " | " 连接。
    与 TECH_IMPLEMENTATION「收集 TurnOutputs → 冲突裁决」一致。
    """
    parts = [scope_output.event_summary.strip() or "（无）"]
    for cid in sorted(character_outputs.keys()):
        action = (character_outputs[cid].dialogue_action or "").strip()
        if action:
            parts.append(action)
    return " | ".join(parts)


class Orchestrator:
    """
    编排器：持有配置、Storage、CharacterAgents、ScopeAgents；驱动单回合（构建 Context、并行调用、写回事件簿/状态）。
    """

    def __init__(
        self,
        storage: MemoryStorage,
        character_agents: dict[str, CharacterAgent],
        scope_agents: dict[str, ScopeAgent],
        world_config: dict,
        runtime_config: dict,
        characters_config: dict,
        data_root: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.storage = storage
        self.character_agents = character_agents
        self.scope_agents = scope_agents
        self.world_config = world_config
        self.runtime_config = runtime_config
        self.characters_config = characters_config
        self._data_root = data_root
        self._project_root = project_root or Path(".")

    @classmethod
    def from_config(cls, config_dir: Path | None = None) -> "Orchestrator":
        """从配置目录加载全量配置，创建 Storage 与 Agent；若配置了 data_root 则从磁盘加载范围事件（含正文）作为记忆唯一来源，并在此后写回时同步到磁盘。"""
        logger.debug("[启动] Orchestrator.from_config: 开始, config_dir=%s", config_dir)
        all_cfg = load_all_config(config_dir)
        runtime = all_cfg["runtime"]
        world = all_cfg["world"]
        characters = all_cfg["characters"]
        enabled_char = list(runtime.get("agents", {}).get("characters", {}).get("enabled_ids", []))
        enabled_scope = list(runtime.get("agents", {}).get("scopes", {}).get("enabled_ids", []))
        logger.debug("[启动] Orchestrator.from_config: enabled_char=%s, enabled_scope=%s", enabled_char, enabled_scope)
        storage = MemoryStorage()
        project_root = config_dir.resolve().parent if config_dir else Path(".")
        data_root = file_sync.get_data_root(project_root, runtime) if config_dir else None
        if data_root and enabled_scope:
            for sid in enabled_scope:
                loaded = file_sync.load_scope_events_from_disk(data_root, sid)
                if loaded:
                    storage.set_scope_events(sid, loaded)
                    logger.debug("[启动] 从磁盘加载 scope=%s 事件 %s 条（正文仅存此处，展示从记忆取）", sid, len(loaded))
        character_agents = {
            cid: CharacterAgent(
                cid,
                storage=storage,
                runtime_config=runtime,
                characters_config=characters,
                data_root=data_root,
            )
            for cid in enabled_char
        }
        scope_agents = {
            sid: ScopeAgent(
                sid,
                storage=storage,
                runtime_config=runtime,
                world_config=world,
            )
            for sid in enabled_scope
        }
        logger.debug("[启动] Orchestrator.from_config: 已创建 CharacterAgent %s 个, ScopeAgent %s 个",
                     len(character_agents), len(scope_agents))
        return cls(
            storage=storage,
            character_agents=character_agents,
            scope_agents=scope_agents,
            world_config=world,
            runtime_config=runtime,
            characters_config=characters,
            data_root=data_root,
            project_root=project_root,
        )

    def run_one_turn(
        self,
        scope_id: str,
        time: str,
        place: str,
        present_character_ids: list[str],
        last_turn_summary: str = "",
        recent_events_k: int = 5,
        auto_write: bool = True,
    ) -> TurnResult:
        """
        单回合：构建 TurnContext → 并行调用当前 ScopeAgent + 在场 CharacterAgent → 可选写回事件簿/状态 → 返回结果。
        auto_write=True（默认）：写回事件簿与范围状态，不写角色记忆（记忆留作者确认后由 apply_memory_write 执行）。
        auto_write=False：不写任何存储，仅返回 TurnResult，供作者在环审阅后调用 apply_event_and_state_write / apply_memory_write。
        """
        ctx = build_turn_context_from_storage(
            scope_id=scope_id,
            time=time,
            place=place,
            present_character_ids=present_character_ids,
            storage=self.storage,
            world_config=self.world_config,
            last_turn_summary=last_turn_summary,
            recent_events_k=recent_events_k,
        )
        scope_agent = self.scope_agents.get(scope_id)
        if not scope_agent:
            raise ValueError(f"scope_id 未启用或不存在: {scope_id}")

        # 并行：ScopeAgent.turn(ctx) + 各在场 CharacterAgent.turn(ctx)
        character_outputs: dict[str, CharacterTurnOutput] = {}
        scope_output: ScopeTurnOutput
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {}
            futures["__scope__"] = executor.submit(scope_agent.turn, ctx)
            for cid in present_character_ids:
                agent = self.character_agents.get(cid)
                if agent:
                    futures[cid] = executor.submit(agent.turn, ctx)
            for key, fut in futures.items():
                out = fut.result()
                if key == "__scope__":
                    scope_output = out
                else:
                    character_outputs[key] = out

        result = TurnResult(scope_output=scope_output, character_outputs=character_outputs)
        if auto_write:
            self.apply_event_and_state_write(result, scope_id, time, place)
        return result

    def apply_event_and_state_write(
        self,
        result: TurnResult,
        scope_id: str,
        time: str,
        place: str,
    ) -> None:
        """
        作者在环阶段一通过后：将本回合摘要与正文写回 scope 事件簿（记忆唯一来源）；有 data_root 时同步到磁盘，正文仅此一处持久化，展示时从 storage 取，避免多处存储不一致。
        并应用 scope 的 state_delta。
        """
        from src.author_loop.turn_planning import generate_turn_summary_from_body

        body = (result.body_narrative or "").strip()
        if body:
            summary = generate_turn_summary_from_body(body, self.runtime_config)
            event_entry = {
                "summary": summary,
                "body": body,
                "scope_id": scope_id,
                "time": time,
                "place": place,
            }
        else:
            summary = resolve_turn_conflict(result.scope_output, result.character_outputs)
            event_entry = {
                "summary": summary,
                "scope_id": scope_id,
                "time": time,
                "place": place,
            }
        self.storage.append_events(scope_id, [event_entry])
        turn_index: int | None = None
        if self._data_root:
            turn_index = file_sync.next_turn_index(self._data_root)
            state = dict(self.storage.get_state(scope_id))
            if result.scope_output.state_delta:
                state = {**state, **result.scope_output.state_delta}
            file_sync.sync_scope_turn(
                self._data_root,
                scope_id,
                turn_index,
                event_entry,
                state,
            )
        if result.scope_output.state_delta:
            current = self.storage.get_state(scope_id)
            self.storage.set_state(scope_id, {**current, **result.scope_output.state_delta})
        if self._data_root and turn_index is not None:
            present = sorted(result.character_outputs.keys())
            sync_relationship_graph_after_scope_turn(
                self._data_root,
                characters_config=self.characters_config,
                scope_id=scope_id,
                turn_index=turn_index,
                present_character_ids=present,
                event_summary=str(event_entry.get("summary") or ""),
            )

    def apply_memory_write(
        self,
        result: TurnResult,
        scope_id: str,
        time: str,
        place: str,
    ) -> None:
        """
        作者在环阶段二确认后：将本回合各角色输出写回其私有记忆（事件提炼）。
        每个在场角色追加一条 append_event_refinement，内容为 dialogue_action 或 inner_monologue 的摘要。
        """
        for cid, out in result.character_outputs.items():
            summary = (out.dialogue_action or out.inner_monologue or "").strip() or "（本回合无言行摘要）"
            self.storage.append_event_refinement(
                cid,
                {"summary": summary, "scope_id": scope_id, "time": time, "place": place},
            )

    def run_n_turns(
        self,
        n: int,
        scope_id: str,
        time: str,
        place: str,
        present_character_ids: list[str],
        initial_last_turn_summary: str = "",
        recent_events_k: int = 5,
    ) -> list[TurnResult]:
        """
        多回合循环：连续执行 n 次 run_one_turn，同一 Storage 持久化；每回合的 last_turn_summary 取上一回合的 scope_output.event_summary。
        场景参数（scope_id, time, place, present_character_ids）当前固定，后续可改为按规则或作者输入切换。
        返回各回合的 TurnResult 列表。
        """
        results: list[TurnResult] = []
        last_summary = initial_last_turn_summary
        for _ in range(n):
            result = self.run_one_turn(
                scope_id=scope_id,
                time=time,
                place=place,
                present_character_ids=present_character_ids,
                last_turn_summary=last_summary,
                recent_events_k=recent_events_k,
            )
            results.append(result)
            last_summary = result.scope_output.event_summary
        return results
