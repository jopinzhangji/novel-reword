"""
run_novel_with_author 集成测试：配置 + 开局场景 + 作者在环一回合（作者全同意）→ 事件簿与角色记忆有写入。
与 NEXT_ITERATION 第 8 项「配套测试」一致，覆盖作者在环主流程。
"""
import pytest
from src.config import load_all_config, get_initial_scene, PROJECT_ROOT
from src.orchestrator import Orchestrator
from src.author_loop import review_turn_result, review_memory_plan


def _config_available():
    try:
        load_all_config(PROJECT_ROOT / "config")
        return True
    except FileNotFoundError:
        return False


class TestRunNovelWithAuthorFlow:
    """作者在环主流程：从配置读场景、一回合审阅全同意、写回事件与记忆。"""

    def test_one_turn_author_approves_all_writes_events_and_memory(self):
        if not _config_available():
            pytest.skip("config 目录或示例配置不存在")
        orch = Orchestrator.from_config(PROJECT_ROOT / "config")
        scene = get_initial_scene(orch.runtime_config, orch.world_config)
        scope_id = scene["scope_id"]
        time_str = scene["time"]
        place = scene["place"]
        runtime = orch.runtime_config
        enabled_char = list(runtime.get("agents", {}).get("characters", {}).get("enabled_ids", []))
        present = [c for c in enabled_char if c in orch.character_agents]

        result = orch.run_one_turn(
            scope_id=scope_id,
            time=time_str,
            place=place,
            present_character_ids=present,
            last_turn_summary="",
            auto_write=False,
        )
        approved, result_phase1 = review_turn_result(result, scope_id, time_str, place, input_fn=lambda _: "y")
        assert approved and result_phase1 is not None
        orch.apply_event_and_state_write(result_phase1, scope_id, time_str, place)
        confirmed, result_phase2 = review_memory_plan(result_phase1, scope_id, time_str, place, input_fn=lambda _: "y")
        assert confirmed and result_phase2 is not None
        orch.apply_memory_write(result_phase2, scope_id, time_str, place)

        events = orch.storage.get_recent_events(scope_id, k=5)
        assert len(events) >= 1
        assert "summary" in events[0]
        for cid in present:
            char_events = orch.storage.get_events(cid, limit=5)
            assert len(char_events) >= 1
            assert any("summary" in e or "scope_id" in e for e in char_events)

    def test_entry_script_exits_cleanly_on_stdin_eof(self, tmp_path):
        """stdin 关闭（EOF）时入口脚本应优雅退出：不打印 Traceback，且以非零码结束（交互未完成）。"""
        import subprocess
        import sys

        proc = subprocess.run(
            [sys.executable, "run_novel_with_author.py"],
            cwd=PROJECT_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            env={**__import__("os").environ, "MIN_AUTOBOOK_LOG_DIR": str(tmp_path / "logs")},
        )
        combined = proc.stdout + proc.stderr
        assert "Traceback" not in combined
        assert "交互已中断" in combined
        assert proc.returncode != 0
