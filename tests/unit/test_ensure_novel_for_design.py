"""ensure_current_novel_for_design_phase：设定阶段前须绑定有效作品目录。"""

from pathlib import Path

import yaml

from src.author_loop.novel_bootstrap import (
    ensure_current_novel_for_design_phase,
    interactive_resolve_novel_for_design_phase,
)


class _Log:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def info(self, *a, **k):
        pass

    def error(self, msg: str, *a, **k):
        self.errors.append(str(msg))


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def test_ensure_creates_provisional_when_only_design_session_no_pointer(tmp_path: Path):
    """仅有 design_session、无 current_novel 时，应用编排器 world/characters 创建初稿。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    _write_yaml(config_dir / "design_session.yaml", {"events": [{"type": "x"}]})
    _write_yaml(
        config_dir / "novel_writing.yaml",
        {"setting_research": {"enabled": True, "trigger": "design_only"}},
    )
    runtime = {
        "agents": {
            "characters": {"enabled_ids": ["p"]},
            "scopes": {"enabled_ids": ["main"]},
        },
        "runtime": {"storage": {"data_root": str(tmp_path / "data")}},
    }
    world = {"world": {"name": "W"}, "time": {"start": ""}, "scopes": []}
    chars = {"characters": [{"id": "p", "name": "P"}]}
    log = _Log()
    ok = ensure_current_novel_for_design_phase(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config=runtime,
        log=log,
        world_config=world,
        characters_config=chars,
    )
    assert ok is True
    assert (config_dir / "current_novel.yaml").is_file()
    data = yaml.safe_load((config_dir / "current_novel.yaml").read_text(encoding="utf-8")) or {}
    root = Path((data.get("root") or "").strip())
    assert root.is_dir()
    assert (root / "config" / "world.yaml").is_file()


def test_ensure_ok_when_root_already_valid(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    novel_root = tmp_path / "data" / "novels" / "n1"
    (novel_root / "config").mkdir(parents=True)
    _write_yaml(config_dir / "current_novel.yaml", {"slug": "n1", "root": str(novel_root)})
    runtime = {"agents": {"characters": {"enabled_ids": []}, "scopes": {"enabled_ids": []}}}
    ok = ensure_current_novel_for_design_phase(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config=runtime,
        log=_Log(),
        world_config={},
        characters_config={"characters": []},
    )
    assert ok is True


def test_ensure_false_when_body_events_without_valid_novel(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    data_root = tmp_path / "data"
    events = data_root / "book" / "events" / "main" / "events"
    events.mkdir(parents=True)
    (events / "turn_001.md").write_text("x", encoding="utf-8")
    runtime = {
        "agents": {"characters": {"enabled_ids": []}, "scopes": {"enabled_ids": []}},
        "runtime": {"storage": {"data_root": str(data_root)}},
    }
    log = _Log()
    ok = ensure_current_novel_for_design_phase(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config=runtime,
        log=log,
        world_config={},
        characters_config={"characters": []},
    )
    assert ok is False
    assert any("正文事件" in m for m in log.errors)


def test_interactive_resolve_option1_creates_provisional_when_body_events(tmp_path: Path):
    """有正文无指针时，交互选 1 可新建初稿并绑定。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    data_root = tmp_path / "data"
    events = data_root / "book" / "events" / "main" / "events"
    events.mkdir(parents=True)
    (events / "turn_001.md").write_text("x", encoding="utf-8")
    runtime = {
        "agents": {
            "characters": {"enabled_ids": ["p"]},
            "scopes": {"enabled_ids": ["main"]},
        },
        "runtime": {"storage": {"data_root": str(data_root)}},
    }
    world = {"world": {"name": "W"}, "time": {"start": ""}, "scopes": []}
    chars = {"characters": [{"id": "p", "name": "P"}]}
    inputs = iter(["1"])
    ok = interactive_resolve_novel_for_design_phase(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config=runtime,
        world_config=world,
        characters_config=chars,
        log=_Log(),
        input_fn=lambda _: next(inputs),
    )
    assert ok is True
    assert (config_dir / "current_novel.yaml").is_file()


def test_interactive_resolve_option2_binds_existing_root(tmp_path: Path):
    inputs = iter(["2", str(tmp_path / "novel_x")])
    novel_root = tmp_path / "novel_x"
    (novel_root / "config").mkdir(parents=True)
    _write_yaml(
        novel_root / "meta.yaml",
        {"slug": "novel_x", "title": "测试书", "status": "draft"},
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    runtime = {
        "agents": {"characters": {"enabled_ids": []}, "scopes": {"enabled_ids": []}},
        "runtime": {"storage": {"data_root": str(tmp_path / "data")}},
    }
    ok = interactive_resolve_novel_for_design_phase(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config=runtime,
        world_config={},
        characters_config={"characters": []},
        log=_Log(),
        input_fn=lambda _: next(inputs),
    )
    assert ok is True
    data = yaml.safe_load((config_dir / "current_novel.yaml").read_text(encoding="utf-8")) or {}
    assert Path(data["root"]).resolve() == novel_root.resolve()
