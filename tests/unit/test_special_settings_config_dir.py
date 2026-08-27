"""特殊设定路径：绑定小说时落在小说 config/ 下。"""
from pathlib import Path

import pytest
import yaml

from src.config import load_special_settings_config, special_settings_config_dir


def test_special_settings_config_dir_raises_when_no_novel(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="尚未创建或选择当前作品"):
        special_settings_config_dir(config_dir)


def test_special_settings_config_dir_novel_when_bound(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    novel_root = tmp_path / "data" / "novels" / "n1"
    (novel_root / "config").mkdir(parents=True)
    (config_dir / "current_novel.yaml").write_text(
        yaml.dump({"root": str(novel_root)}, allow_unicode=True),
        encoding="utf-8",
    )
    assert special_settings_config_dir(config_dir) == novel_root / "config"


def test_load_special_prefers_novel_setting_yaml(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    novel_root = tmp_path / "data" / "novels" / "n2"
    (novel_root / "config").mkdir(parents=True)
    (config_dir / "current_novel.yaml").write_text(
        yaml.dump({"root": str(novel_root)}, allow_unicode=True),
        encoding="utf-8",
    )
    (novel_root / "config" / "setting_research_output.yaml").write_text(
        yaml.dump({"power_system": {"name": "novel"}}, allow_unicode=True),
        encoding="utf-8",
    )
    (config_dir / "setting_research_output.yaml").write_text(
        yaml.dump({"power_system": {"name": "global"}}, allow_unicode=True),
        encoding="utf-8",
    )
    data = load_special_settings_config(config_dir)
    assert data and data.get("power_system", {}).get("name") == "novel"


def test_load_special_falls_back_to_example_when_no_novel(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "example_special_settings.yaml").write_text(
        yaml.dump({"power_system": {"name": "example"}}, allow_unicode=True),
        encoding="utf-8",
    )
    data = load_special_settings_config(config_dir)
    assert data and data.get("power_system", {}).get("name") == "example"
