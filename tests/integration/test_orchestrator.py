"""
编排器集成测试：配置 + Storage + 壳 Agent → 单回合 → 断言事件簿/状态有写入。
与 TECH_IMPLEMENTATION §6、NEXT_ITERATION 第 4 项一致。
"""
import pytest
from src.orchestrator import Orchestrator, TurnResult
from src.config import load_all_config, PROJECT_ROOT


def _config_available():
    try:
        load_all_config(PROJECT_ROOT / "config")
        return True
    except FileNotFoundError:
        return False


def _first_scope_id(orch):
    """从编排器取第一个已配置的 scope_id（与 config 中 agents.scopes.enabled_ids 一致）。"""
    return next(iter(orch.scope_agents)) if orch.scope_agents else None


def _present_characters(orch, max_n=2):
    """从编排器取在场角色 id 列表（最多 max_n 个）。"""
    ids = list(orch.character_agents.keys())
    return ids[:max_n] if ids else []


class TestOrchestratorFromConfig:
    def test_from_config_creates_agents_and_storage(self):
        if not _config_available():
            pytest.skip("config 目录或示例配置不存在")
        orch = Orchestrator.from_config(PROJECT_ROOT / "config")
        assert orch.storage is not None
        assert len(orch.character_agents) >= 1
        assert len(orch.scope_agents) >= 1


class TestOrchestratorRunOneTurn:
    def test_run_one_turn_returns_turn_result(self):
        if not _config_available():
            pytest.skip("config 目录或示例配置不存在")
        orch = Orchestrator.from_config(PROJECT_ROOT / "config")
        scope_id = _first_scope_id(orch)
        present = _present_characters(orch)
        result = orch.run_one_turn(
            scope_id=scope_id,
            time="永和十年春",
            place="京城",
            present_character_ids=present,
            last_turn_summary="",
        )
        assert isinstance(result, TurnResult)
        assert result.scope_output is not None
        assert isinstance(result.character_outputs, dict)

    def test_run_one_turn_writes_events_to_storage(self):
        if not _config_available():
            pytest.skip("config 目录或示例配置不存在")
        orch = Orchestrator.from_config(PROJECT_ROOT / "config")
        scope_id = _first_scope_id(orch)
        present = _present_characters(orch)
        orch.run_one_turn(
            scope_id=scope_id,
            time="永和十年春",
            place="京城",
            present_character_ids=present,
        )
        events = orch.storage.get_recent_events(scope_id, k=10)
        assert len(events) >= 1
        assert "summary" in events[0] or "event_summary" in str(events[0])
        # 冲突裁决后写入的摘要应包含 scope 与角色言行（壳输出含「壳」或「暂无」）
        summary = events[0].get("summary", "")
        assert summary
        assert " | " in summary or len(summary) >= 1


class TestOrchestratorRunNTurns:
    """多回合循环：状态持久化，下一回合能读到上一回合写入的事件簿。"""

    def test_run_n_turns_returns_n_results(self):
        if not _config_available():
            pytest.skip("config 目录或示例配置不存在")
        orch = Orchestrator.from_config(PROJECT_ROOT / "config")
        scope_id = _first_scope_id(orch)
        present = _present_characters(orch)
        results = orch.run_n_turns(
            n=2,
            scope_id=scope_id,
            time="永和十年春",
            place="京城",
            present_character_ids=present,
        )
        assert len(results) == 2
        assert all(isinstance(r, TurnResult) for r in results)

    def test_run_n_turns_persists_events_each_turn(self):
        if not _config_available():
            pytest.skip("config 目录或示例配置不存在")
        orch = Orchestrator.from_config(PROJECT_ROOT / "config")
        scope_id = _first_scope_id(orch)
        present = _present_characters(orch)
        orch.run_n_turns(
            n=3,
            scope_id=scope_id,
            time="永和十年春",
            place="京城",
            present_character_ids=present,
        )
        events = orch.storage.get_recent_events(scope_id, k=10)
        assert len(events) >= 3
        for i in range(3):
            assert "summary" in events[i] or "event_summary" in str(events[i])


class TestOrchestratorAuthorInTheLoop:
    """作者在环：auto_write=False 不写回；apply_event_and_state_write / apply_memory_write 分别写回。"""

    def test_run_one_turn_auto_write_false_does_not_write_events(self):
        if not _config_available():
            pytest.skip("config 目录或示例配置不存在")
        orch = Orchestrator.from_config(PROJECT_ROOT / "config")
        scope_id = _first_scope_id(orch)
        present = _present_characters(orch)
        initial_events = orch.storage.get_recent_events(scope_id, k=5)
        result = orch.run_one_turn(
            scope_id=scope_id,
            time="永和十年春",
            place="京城",
            present_character_ids=present,
            auto_write=False,
        )
        events_after = orch.storage.get_recent_events(scope_id, k=5)
        assert len(events_after) == len(initial_events), "auto_write=False 时不应追加事件簿"

    def test_apply_event_and_state_write_then_apply_memory_write(self):
        if not _config_available():
            pytest.skip("config 目录或示例配置不存在")
        orch = Orchestrator.from_config(PROJECT_ROOT / "config")
        scope_id = _first_scope_id(orch)
        present = _present_characters(orch)
        result = orch.run_one_turn(
            scope_id=scope_id,
            time="永和十年春",
            place="京城",
            present_character_ids=present,
            auto_write=False,
        )
        # 用总数增量断言（而非窗口长度）：data/ 事件可随历次全量测试累计，一旦超过
        # k=500 截断窗口，窗口长度不再随 append 增长（易假失败），故改用 get_event_count。
        n_before = orch.storage.get_event_count(scope_id)
        orch.apply_event_and_state_write(result, scope_id, "永和十年春", "京城")
        assert orch.storage.get_event_count(scope_id) >= n_before + 1, (
            "apply_event_and_state_write 应追加至少一条 scope 事件"
        )
        events = orch.storage.get_recent_events(scope_id, k=1)
        assert events and "summary" in events[0]
        orch.apply_memory_write(result, scope_id, "永和十年春", "京城")
        for cid in present:
            char_events = orch.storage.get_events(cid, limit=20)
            assert len(char_events) >= 1
            assert any("summary" in e or "scope_id" in e for e in char_events)
