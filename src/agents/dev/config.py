"""
DevAgent 配置加载：从合并后的运行时配置中读取 dev_agent 段。
dev_agent 默认在 config/system_config.yaml；与 TECH_IMPLEMENTATION §4.2 一致。
"""
from pathlib import Path

# 项目根：src/agents/dev/config.py -> 上级 x4
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def load_dev_agent_config(config_path: Path | None = None) -> dict:
    """
    加载 dev_agent 配置段。
    config_path 若传入，则取其所在目录为 config 目录并加载合并后的 runtime（system + example_runtime）；
    若未传则使用 PROJECT_ROOT / "config"。
    """
    from src.config import load_runtime_config

    if config_path is None:
        config_dir = PROJECT_ROOT / "config"
    else:
        config_dir = Path(config_path).resolve().parent
    try:
        data = load_runtime_config(config_dir)
    except FileNotFoundError:
        data = {}
    defaults = {
        "enabled": False,
        "trigger": "off",
        "test_command": "",
        "scope": [],
        "search_ideas_enabled": False,  # §3.6 为 true 时 run_once 成功后写 search_ideas 并加入 cursor_tasks
        # 以下可选，用于产出真实条目：setting_research_output_path（已有设定研究 YAML 路径）；或 theme + runtime_config_path 调用设定研究
        # search_ideas_theme / theme, search_ideas_genre / genre, search_ideas_runtime_config_path / runtime_config_path
    }
    return {**defaults, **data.get("dev_agent", {})}
