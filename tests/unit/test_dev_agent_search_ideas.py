"""
DevAgent 搜索与联想扩展点测试：run_search_ideas 占位产出、从设定研究 YAML 产出真实条目、ensure_search_ideas_readme。
与 TECH_IMPLEMENTATION §3.6（2）、NEXT_ITERATION 第 9、15 项一致。
"""
import pytest
import yaml
from pathlib import Path

from src.agents.dev.search_ideas import run_search_ideas, ensure_search_ideas_readme
from src.agents.dev.output_writer import get_output_root


def test_run_search_ideas_from_setting_yaml_produces_real_entries(project_root, tmp_path):
    """配置 setting_research_output_path 指向含 power_system/level_system 的 YAML 时，产出 power_system.md、level_system.md。"""
    fixture_yaml = tmp_path / "setting_research_output.yaml"
    fixture_yaml.write_text(
        yaml.dump({
            "world_id": "test",
            "power_system": {"name": "灵力", "description": "以灵力为根基的战力体系"},
            "level_system": {"name": "筑基境界", "description": "炼气筑基等", "levels": [{"name": "炼气", "order": 0}, {"name": "筑基", "order": 1}]},
        }, allow_unicode=True),
        encoding="utf-8",
    )
    root = get_output_root(project_root)
    ideas_dir = root / "search_ideas"
    ideas_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "search_ideas_enabled": True,
        "setting_research_output_path": str(fixture_yaml),
    }
    entries = run_search_ideas(project_root, config)

    assert len(entries) >= 2
    paths = [e["path"] for e in entries]
    assert any("power_system" in p for p in paths)
    assert any("level_system" in p for p in paths)
    assert (ideas_dir / "power_system.md").is_file()
    assert (ideas_dir / "level_system.md").is_file()
    assert "灵力" in (ideas_dir / "power_system.md").read_text(encoding="utf-8")
    assert "筑基" in (ideas_dir / "level_system.md").read_text(encoding="utf-8")


def test_run_search_ideas_writes_placeholder_and_returns_entries(project_root):
    """run_search_ideas 写入 search_ideas/placeholder.md 并返回至少一条条目。"""
    root = get_output_root(project_root)
    ideas_dir = root / "search_ideas"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    placeholder = ideas_dir / "placeholder.md"
    if placeholder.exists():
        placeholder.unlink()
    entries = run_search_ideas(project_root, {"search_ideas_enabled": True})
    assert isinstance(entries, list)
    assert len(entries) >= 1
    assert "path" in entries[0]
    assert "search_ideas" in entries[0]["path"]
    assert placeholder.is_file()
    content = placeholder.read_text(encoding="utf-8")
    assert "搜索与联想" in content or "占位" in content


def test_ensure_search_ideas_readme_creates_readme(project_root):
    """ensure_search_ideas_readme 在 search_ideas 下创建 README.md（若不存在）。"""
    root = get_output_root(project_root)
    ideas_dir = root / "search_ideas"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    readme = ideas_dir / "README.md"
    if readme.exists():
        readme.unlink()
    ensure_search_ideas_readme(project_root)
    assert readme.is_file()
    assert "search_ideas" in readme.read_text(encoding="utf-8")
