"""author_interaction_state：M2 持久化与路径。"""

from pathlib import Path

import yaml

from src.author_loop.author_interaction_state import (
    AuthorPhaseState,
    LastRoundDigest,
    author_interaction_state_path,
    load_interaction_state,
    save_interaction_state,
)
from src.author_loop.author_session import AuthorSession


def test_author_interaction_state_path_global_when_no_novel(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    assert author_interaction_state_path(config_dir) == config_dir / "author_interaction_state.yaml"


def test_author_interaction_state_path_novel_when_bound(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    novel_root = tmp_path / "novels" / "n1"
    (novel_root / "config").mkdir(parents=True)
    (config_dir / "current_novel.yaml").write_text(
        yaml.dump({"root": str(novel_root.resolve())}, allow_unicode=True),
        encoding="utf-8",
    )
    assert author_interaction_state_path(config_dir) == novel_root / "config" / "author_interaction_state.yaml"


def test_save_load_roundtrip(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    ps = AuthorPhaseState(phase="DESIGN_MAIN", flags={"k": 1})
    dg = LastRoundDigest(
        interaction="y",
        system_response="结束",
        execution="return",
        open_issues=[],
    )
    save_interaction_state(config_dir, ps, dg)
    p = author_interaction_state_path(config_dir)
    assert p.is_file()
    ps2, dg2 = load_interaction_state(config_dir)
    assert ps2.phase == "DESIGN_MAIN"
    assert ps2.flags.get("k") == 1
    assert dg2.interaction == "y"
    assert dg2.execution == "return"


def test_author_session_for_design_phase_persists_digest(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    s = AuthorSession.for_design_phase(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config={},
        input_fn=None,
    )
    s.record_round_digest(
        interaction="test",
        system_response="resp",
        execution="exe",
        phase="DESIGN_MAIN",
    )
    s2 = AuthorSession.for_design_phase(config_dir, tmp_path, {})
    assert s2.last_round_digest.interaction == "test"
    assert s2.phase_state.phase == "DESIGN_MAIN"
