"""
Storage 抽象（内存版）：角色记忆库（profile/relations/events/emotions）、范围事件簿与状态。
键结构符合 TECH_IMPLEMENTATION §7；每个 Agent 独立记忆库、分开存储。
"""
from pathlib import Path
from typing import Any


class MemoryStorage:
    """内存版 Storage：按 character_id、scope_id 分键，供编排器与各 Agent 读写。"""

    def __init__(self) -> None:
        self._profile: dict[str, dict] = {}
        self._relations: dict[str, list] = {}
        self._char_events: dict[str, list] = {}
        self._emotions: dict[str, list] = {}
        self._scope_events: dict[str, list] = {}
        self._scope_state: dict[str, dict] = {}
        # 次要角色列表：小说中非配置关键角色，由剧情动态产生，供 Agent 查阅（name, brief, scope_id 等）
        self._secondary_characters: list[dict] = []
        # 三层记忆（§4）：L2 解释（可更新）、L3 策略（可过期）。L1 事实存 _char_events。
        self._char_interpretations: dict[str, list] = {}
        self._char_strategies: dict[str, list] = {}

    # --- 角色：profile ---
    def get_profile(self, character_id: str) -> dict:
        return self._profile.get(character_id, {}).copy()

    def update_profile(self, character_id: str, delta: dict) -> None:
        self._profile.setdefault(character_id, {})
        self._profile[character_id].update(delta)

    # --- 角色：relations ---
    def get_relations(self, character_id: str) -> list:
        return list(self._relations.get(character_id, []))

    def append_relation(self, character_id: str, entry: dict) -> None:
        self._relations.setdefault(character_id, []).append(entry)

    # --- 角色：events（事件提炼）---
    def get_events(self, character_id: str, limit: int = 50) -> list:
        return list(self._char_events.get(character_id, [])[-limit:])

    def append_event_refinement(self, character_id: str, entry: dict) -> None:
        self._char_events.setdefault(character_id, []).append(entry)

    # --- 角色：emotions ---
    def get_emotions(self, character_id: str, target_id: str | None = None) -> list:
        raw = self._emotions.get(character_id, [])
        if target_id is None:
            return list(raw)
        return [e for e in raw if e.get("target_id") == target_id]

    def append_emotion(self, character_id: str, entry: dict) -> None:
        self._emotions.setdefault(character_id, []).append(entry)

    # --- 三层记忆：L2 解释（可更新） / L3 策略（可过期）——§4 记忆分层 ---
    def upsert_interpretation(self, character_id: str, entry: dict) -> dict:
        """
        L2 解释层：按 subject 若已存在则**原地替换**（解释可随认知更新），否则追加。
        返回入库的 entry。subject 为 upsert 键，缺省给 "general"。
        """
        entry = dict(entry)
        entries = self._char_interpretations.setdefault(character_id, [])
        subject = str(entry.get("subject") or "general")
        for i in range(len(entries) - 1, -1, -1):
            if str(entries[i].get("subject") or "general") == subject:
                entries[i] = entry  # 覆盖原解释（L2 可更新，不叠加历史）
                return entry
        entries.append(entry)
        return entry

    def get_interpretations(self, character_id: str, limit: int = 8) -> list:
        return list(self._char_interpretations.get(character_id, [])[-limit:]) if limit else list(
            self._char_interpretations.get(character_id, [])
        )

    def append_strategy(self, character_id: str, entry: dict) -> dict:
        """L3 策略层：追加一条短期计划/下一步动作。entry 一般带 expires_turn（过期回合）。"""
        entry = dict(entry)
        self._char_strategies.setdefault(character_id, []).append(entry)
        return entry

    def get_active_strategies(self, character_id: str, current_turn: int | None = None, limit: int = 8) -> list:
        """L3 策略层：可过期——current_turn 给出时过滤已过期（expires_turn<=current_turn）条目；未给或过期逻辑缺省则全返。"""
        raw = self._char_strategies.get(character_id, [])
        if current_turn is not None:
            raw = [e for e in raw if str(e.get("expires_turn") or "").isdigit() is False
                   or not (isinstance(e.get("expires_turn"), int) and e["expires_turn"] <= current_turn)]
        # 只保留未过期（或未设置过期）的
        active = []
        for e in raw:
            et = e.get("expires_turn")
            if current_turn is not None and isinstance(et, int) and et <= current_turn:
                continue
            active.append(e)
        return list(active[-limit:]) if limit else active

    # --- 范围：events ---
    def append_events(self, scope_id: str, events: list[dict]) -> None:
        self._scope_events.setdefault(scope_id, []).extend(events)

    def set_scope_events(self, scope_id: str, events: list[dict]) -> None:
        """用给定事件列表覆盖该范围的事件（如从磁盘加载后写入），保证正文等仅从本存储读取，持久化一致。"""
        self._scope_events[scope_id] = list(events)

    def get_recent_events(self, scope_id: str, k: int = 50) -> list:
        return list(self._scope_events.get(scope_id, [])[-k:])

    def get_event_count(self, scope_id: str) -> int:
        """该范围事件总数（用作回合号/过期基准）。"""
        return len(self._scope_events.get(scope_id, []))

    # --- 范围：state ---
    def get_state(self, scope_id: str) -> dict:
        return self._scope_state.get(scope_id, {}).copy()

    def set_state(self, scope_id: str, state: dict) -> None:
        self._scope_state[scope_id] = dict(state)

    # --- 次要角色列表（非配置关键角色，可自由生成与查阅）---
    def get_secondary_characters(
        self,
        scope_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        获取已记录的次要角色列表，供 Agent 查阅。
        entry 建议含 name, brief（一句话描述）, scope_id（可选）等。
        scope_id 非空时仅返回与该范围相关的记录（entry 的 scope_id 匹配或为空）。
        """
        raw = list(self._secondary_characters)
        if scope_id:
            raw = [e for e in raw if e.get("scope_id") in (None, "", scope_id)]
        return raw[-limit:] if limit else raw

    def append_secondary_character(self, entry: dict) -> None:
        """
        追加一条次要角色记录。建议至少含 name, brief；可选 scope_id, turn_id 等。
        同一 name 可多次追加（如信息更新），由调用方或后续去重策略决定。
        """
        self._secondary_characters.append(dict(entry))
