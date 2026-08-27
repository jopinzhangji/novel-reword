"""
设定研究 Agent 单元测试：SettingResearchAgent.run() 占位产出 YAML；第 14 项 mock LLM 时产出真实结构。
与 TECH_IMPLEMENTATION 第 11 项、第 14 项一致。
"""
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from src.agents.setting_research import SettingResearchAgent
from src.agents.setting_research.agent import discuss_freely


def test_run_writes_yaml_and_returns_path(tmp_path):
    agent = SettingResearchAgent(output_dir=tmp_path)
    path = agent.run(theme="武侠", genre="低武", reference="参照某书")
    assert path == tmp_path / "setting_research_output.yaml"
    assert path.is_file()
    content = path.read_text(encoding="utf-8")
    assert "设定研究 Agent" in content
    assert "武侠" in content
    assert "低武" in content
    assert "power_system" in content
    assert "level_system" in content


def test_run_inline_output_dir(tmp_path):
    agent = SettingResearchAgent()
    path = agent.run(theme="", genre="仙侠", output_dir=tmp_path)
    assert path.is_file()
    assert "仙侠" in path.read_text(encoding="utf-8")


def test_run_requires_output_dir():
    agent = SettingResearchAgent()
    with pytest.raises(ValueError, match="output_dir"):
        agent.run(theme="x", genre="y")


def test_run_with_mock_llm_produces_power_and_level_system(tmp_path):
    """第 14 项：mock get_llm_provider 时 run(runtime_config=...) 产出含 power_system/level_system 的 YAML。"""
    mock_llm = Mock()
    mock_llm.generate.return_value = """
world_id: test_world
version: "0.1"
power_system:
  name: "灵力"
  description: "修真世界灵力修为"
  levels: []
level_system:
  name: "炼气筑基"
  description: "修真境界"
  levels:
    - id: l0
      name: "炼气"
      order: 0
    - id: l1
      name: "筑基"
      order: 1
"""
    with patch("src.llm.get_llm_provider", return_value=mock_llm):
        agent = SettingResearchAgent(output_dir=tmp_path)
        path = agent.run(
            theme="修真",
            genre="末法",
            output_dir=tmp_path,
            runtime_config={"framework": {"llm": "tongyi"}},
        )
    content = path.read_text(encoding="utf-8")
    assert "灵力" in content
    assert "炼气" in content or "筑基" in content
    assert "power_system" in content
    assert "level_system" in content
    mock_llm.generate.assert_called_once()


def test_discuss_freely_exhausts_transport_timeout_returns_placeholder_message():
    httpx = pytest.importorskip("httpx")
    mock_llm = Mock()
    mock_llm.__class__.__name__ = "OpenAICompatStub"
    mock_llm.generate.side_effect = httpx.ReadTimeout("")
    with patch("src.llm.get_llm_provider", return_value=mock_llm):
        out = discuss_freely(
            author_message="作者一句",
            theme="t",
            genre="g",
            full_special_summary="摘要",
            runtime_config={"framework": {"llm": "openai"}},
            read_line_fn=None,
        )
    assert "多次超时" in out
    assert mock_llm.generate.call_count == 4


def test_discuss_freely_includes_assembled_context_in_prompt():
    captured: dict[str, str] = {}

    def grab(prompt: str) -> str:
        captured["prompt"] = prompt
        return "reply"

    mock_llm = Mock()
    mock_llm.__class__.__name__ = "OpenAICompat"
    mock_llm.generate.side_effect = grab
    with patch("src.llm.get_llm_provider", return_value=mock_llm):
        discuss_freely(
            author_message="作者一句",
            theme="t",
            genre="g",
            full_special_summary="摘要",
            runtime_config={"framework": {"llm": "x"}},
            assembled_context="【world.yaml】\nCTX_MARKER_UNIQUE",
        )
    assert "CTX_MARKER_UNIQUE" in captured.get("prompt", "")
    assert "归档摘录" in captured.get("prompt", "")
    assert "回复体例" in captured.get("prompt", "")
    assert "可归档条款" in captured.get("prompt", "")
