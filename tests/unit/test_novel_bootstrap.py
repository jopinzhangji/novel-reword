from pathlib import Path

import yaml

from src.author_loop.novel_bootstrap import prepare_new_novel_if_needed


class _DummyLog:
    def info(self, *args, **kwargs):
        return None


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def test_prepare_new_novel_creates_minimal_files_and_force_design(tmp_path: Path):
    project_root = tmp_path
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(
        config_dir / "novel_writing.yaml",
        {"turn_based": True},
    )
    runtime = {
        "agents": {
            "characters": {"enabled_ids": ["张凡", "李墨"]},
            "scopes": {"enabled_ids": ["怪物来袭"]},
        },
        "runtime": {"storage": {"data_root": str(project_root / "data")}},
    }

    touched = prepare_new_novel_if_needed(
        config_dir=config_dir,
        project_root=project_root,
        runtime_config=runtime,
        log=_DummyLog(),
    )
    assert touched is True
    assert not (config_dir / "example_world.yaml").is_file()
    assert not (config_dir / "example_characters.yaml").is_file()
    drafts = list((project_root / "data" / "novels").glob("draft-*"))
    assert len(drafts) == 1
    meta = yaml.safe_load((drafts[0] / "meta.yaml").read_text(encoding="utf-8")) or {}
    assert meta.get("status") == "draft"
    assert (config_dir / "current_novel.yaml").is_file()

    nw = yaml.safe_load((config_dir / "novel_writing.yaml").read_text(encoding="utf-8")) or {}
    assert nw.get("setting_research", {}).get("enabled") is True
    assert nw.get("setting_research", {}).get("trigger") == "design_only"


def test_prepare_new_novel_ignores_obsolete_global_setting_yaml(tmp_path: Path):
    """未绑定小说时，全局 config/setting_research_output.yaml 不再视为已有设定，仍走新小说引导。"""
    project_root = tmp_path
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(config_dir / "novel_writing.yaml", {"turn_based": True})
    _write_yaml(config_dir / "setting_research_output.yaml", {"power_system": {"name": "修行"}})
    runtime = {
        "agents": {"characters": {"enabled_ids": ["a"]}, "scopes": {"enabled_ids": ["s"]}},
        "runtime": {"storage": {"data_root": str(project_root / "data")}},
    }
    touched = prepare_new_novel_if_needed(
        config_dir=config_dir,
        project_root=project_root,
        runtime_config=runtime,
        log=_DummyLog(),
    )
    assert touched is True


def test_prepare_new_novel_skip_when_has_setting_in_novel_config(tmp_path: Path):
    """已绑定 current_novel 时，以小说目录 config/setting_research_output.yaml 判定已有设定。"""
    project_root = tmp_path
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    novel_root = project_root / "data" / "novels" / "book-a"
    (novel_root / "config").mkdir(parents=True)
    _write_yaml(
        novel_root / "config" / "setting_research_output.yaml",
        {"power_system": {"name": "修行"}},
    )
    _write_yaml(
        config_dir / "current_novel.yaml",
        {"slug": "book-a", "root": str(novel_root)},
    )
    runtime = {"agents": {"characters": {"enabled_ids": ["a"]}, "scopes": {"enabled_ids": ["s"]}}}
    touched = prepare_new_novel_if_needed(
        config_dir=config_dir,
        project_root=project_root,
        runtime_config=runtime,
        log=_DummyLog(),
    )
    assert touched is False

