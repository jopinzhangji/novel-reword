"""
DevAgent 配置契约测试：运行时配置中 dev_agent 段的结构与合法值。
dev_agent 位于 system_config.yaml，经 load_runtime_config 合并（可选 example_runtime 或内置默认）。
"""
import pytest
from pathlib import Path

from src.config import load_runtime_config


def _load_merged_runtime(project_root):
    config_dir = project_root / "config"
    if not config_dir.is_dir():
        pytest.skip("config directory not found")
    return load_runtime_config(config_dir)


class TestDevAgentConfigSection:
    """dev_agent 配置段必须存在且包含必填字段。"""

    def test_dev_agent_section_exists(self, project_root):
        data = _load_merged_runtime(project_root)
        assert "dev_agent" in data, "runtime config must have dev_agent section"

    def test_dev_agent_enabled_is_bool(self, project_root):
        data = _load_merged_runtime(project_root)
        dev = data.get("dev_agent", {})
        assert "enabled" in dev, "dev_agent.enabled required"
        assert isinstance(dev["enabled"], bool), "dev_agent.enabled must be bool"

    def test_dev_agent_trigger_allowed_values(self, project_root):
        data = _load_merged_runtime(project_root)
        dev = data.get("dev_agent", {})
        assert "trigger" in dev, "dev_agent.trigger required"
        assert dev["trigger"] in ("continuous", "on_demand", "off"), (
            "dev_agent.trigger must be one of: continuous, on_demand, off"
        )

    def test_dev_agent_test_command_non_empty(self, project_root):
        data = _load_merged_runtime(project_root)
        dev = data.get("dev_agent", {})
        assert "test_command" in dev, "dev_agent.test_command required"
        assert isinstance(dev["test_command"], str), "dev_agent.test_command must be string"
        assert dev["test_command"].strip(), "dev_agent.test_command must be non-empty"

    def test_dev_agent_scope_optional_list(self, project_root):
        data = _load_merged_runtime(project_root)
        dev = data.get("dev_agent", {})
        if "scope" in dev:
            assert isinstance(dev["scope"], list), "dev_agent.scope must be list if present"
