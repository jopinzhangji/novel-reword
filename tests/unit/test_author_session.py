"""AuthorSession：统一 read_line（M1）。"""
from pathlib import Path

from src.author_loop.author_session import AuthorSession


def test_read_line_uses_input_fn(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    inputs = iter(["  hello  ", "y"])
    session = AuthorSession(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config={},
        input_fn=lambda _: next(inputs),
    )
    assert session.read_line("p1") == "hello"
    assert session.read_line("p2") == "y"


def test_read_line_strips_builtin_input(monkeypatch, tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    calls: list[str] = []

    def fake_input(p: str) -> str:
        calls.append(p)
        return "  ok  "

    monkeypatch.setattr("builtins.input", fake_input)
    session = AuthorSession(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config={},
        input_fn=None,
    )
    assert session.read_line("?") == "ok"
    assert calls == ["?"]


def test_for_main_loop_same_as_design_phase_loader(tmp_path: Path):
    """M5：for_main_loop 与 for_design_phase 共用同一套状态加载。"""
    config_dir = tmp_path / "c"
    config_dir.mkdir()
    d = AuthorSession.for_design_phase(config_dir, tmp_path, {"runtime": {}})
    m = AuthorSession.for_main_loop(config_dir, tmp_path, {"runtime": {}})
    assert type(d) is type(m)
    assert d.phase_state.phase == m.phase_state.phase
