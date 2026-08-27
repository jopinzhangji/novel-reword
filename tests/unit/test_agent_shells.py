"""
单 Agent 壳测试：CharacterAgent、ScopeAgent 输入 TurnContext，输出结构符合 TECH §3.2。
含第 13 项：mock LLM 时 turn() 接 LLM 并解析。
"""
import pytest
from unittest.mock import patch, Mock

from src.context import build_turn_context
from src.agents.character import CharacterAgent, CharacterTurnOutput
from src.agents.world import ScopeAgent, ScopeTurnOutput


def _minimal_ctx():
    return build_turn_context(
        scope_id="capital",
        time="永和十年春",
        place="京城",
        present_character_ids=["a", "b"],
    )


class TestCharacterAgentShell:
    def test_turn_returns_CharacterTurnOutput(self):
        agent = CharacterAgent(character_id="a")
        ctx = _minimal_ctx()
        out = agent.turn(ctx)
        assert isinstance(out, CharacterTurnOutput)
        assert hasattr(out, "inner_monologue")
        assert hasattr(out, "dialogue_action")
        assert hasattr(out, "metadata")
        assert isinstance(out.inner_monologue, str)
        assert isinstance(out.dialogue_action, str)
        assert out.metadata is not None
        assert out.metadata.get("character_id") == "a"
        assert out.metadata.get("scope_id") == "capital"

    def test_turn_output_content_shell(self):
        agent = CharacterAgent(character_id="b")
        out = agent.turn(_minimal_ctx())
        assert "壳" in out.inner_monologue or len(out.inner_monologue) >= 0
        assert "壳" in out.dialogue_action or len(out.dialogue_action) >= 0


class TestScopeAgentShell:
    def test_turn_returns_ScopeTurnOutput(self):
        agent = ScopeAgent(scope_id="capital")
        ctx = _minimal_ctx()
        out = agent.turn(ctx)
        assert isinstance(out, ScopeTurnOutput)
        assert hasattr(out, "constraints")
        assert hasattr(out, "event_summary")
        assert hasattr(out, "state_delta")
        assert isinstance(out.constraints, list)
        assert all(isinstance(c, str) for c in out.constraints)
        assert isinstance(out.event_summary, str)
        assert out.state_delta is None or isinstance(out.state_delta, dict)

    def test_turn_output_content_shell(self):
        agent = ScopeAgent(scope_id="jianghu")
        out = agent.turn(_minimal_ctx())
        assert len(out.constraints) >= 1
        assert "壳" in out.event_summary or len(out.event_summary) >= 0


class TestCharacterAgentWithMockLLM:
    """第 13 项：mock get_llm_provider 时 CharacterAgent.turn 调用 LLM 并解析。"""

    def test_turn_parses_llm_response(self):
        mock_llm = Mock()
        mock_llm.generate.return_value = "内心独白：我有点紧张。\n言行：对众人拱手道：诸位稍安勿躁。"
        mock_llm.__class__.__name__ = "MockLLM"
        with patch("src.llm.get_llm_provider", return_value=mock_llm):
            agent = CharacterAgent(
                "a",
                storage=None,
                runtime_config={"framework": {"llm": "tongyi"}},
                characters_config={"characters": [{"id": "a", "name": "测试", "role": "主角"}]},
            )
            ctx = _minimal_ctx()
            out = agent.turn(ctx)
        assert "紧张" in out.inner_monologue
        assert "拱手" in out.dialogue_action or "稍安" in out.dialogue_action
        mock_llm.generate.assert_called_once()

    def test_turn_includes_relationship_graph_when_data_root(self, tmp_path):
        from pathlib import Path
        from src.runtime.relationship_graph import save_graph, relationship_graph_yaml_path

        dr = Path(tmp_path) / "novel"
        gpath = relationship_graph_yaml_path(dr)
        gpath.parent.mkdir(parents=True, exist_ok=True)
        save_graph(
            gpath,
            {
                "version": 1,
                "nodes": [{"id": "a", "name": "甲"}, {"id": "b", "name": "乙"}],
                "edges": [
                    {
                        "source_id": "a",
                        "target_id": "b",
                        "type": "ally",
                        "status": "active",
                        "evidence_events": ["capital.turn_0001"],
                        "change_log": [],
                    }
                ],
            },
        )
        mock_llm = Mock()
        mock_llm.generate.return_value = "内心独白：graph_ok。\n言行：Hi。"
        mock_llm.__class__.__name__ = "MockLLM"
        with patch("src.llm.get_llm_provider", return_value=mock_llm):
            agent = CharacterAgent(
                "a",
                storage=None,
                runtime_config={"framework": {"llm": "tongyi"}},
                characters_config={"characters": [{"id": "a", "name": "甲", "role": "主角"}]},
                data_root=dr,
            )
            out = agent.turn(_minimal_ctx())
        assert "graph_ok" in out.inner_monologue
        prompt = mock_llm.generate.call_args[0][0]
        assert "关系图谱" in prompt
        assert "ally" in prompt


class TestScopeAgentWithMockLLM:
    """第 13 项：mock get_llm_provider 时 ScopeAgent.turn 调用 LLM 并解析。"""

    def test_turn_parses_llm_response(self):
        mock_llm = Mock()
        mock_llm.generate.return_value = "约束：不得动武\n本回合事件摘要：众人齐聚京城，商议要事。"
        mock_llm.__class__.__name__ = "MockLLM"
        with patch("src.llm.get_llm_provider", return_value=mock_llm):
            agent = ScopeAgent(
                "capital",
                storage=None,
                runtime_config={"framework": {"llm": "tongyi"}},
                world_config={"scopes": [{"id": "capital", "name": "京城"}]},
            )
            ctx = _minimal_ctx()
            out = agent.turn(ctx)
        assert any("不得动武" in c or "动武" in c for c in out.constraints)
        assert "京城" in out.event_summary or "商议" in out.event_summary
        mock_llm.generate.assert_called_once()
