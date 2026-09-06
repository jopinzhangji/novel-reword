"""设定讨论/设定情况 确定性读口（G4 工作台，无 LLM）。

供控制台面板呈现当前设定阶段快照：阶段/简介/world/设定方向/最近已归档讨论摘要。
所有读口缺文件安全（空值兜底），不写盘。
"""
from __future__ import annotations

from pathlib import Path

from src.workbench.common import read_yaml, safe_str


def _phase_from_state(novel_root: Path) -> dict:
    """读 config/author_interaction_state.yaml 的 phase_state.phase/subphase。"""
    data = read_yaml(Path(novel_root) / "config" / "author_interaction_state.yaml")
    if not isinstance(data, dict):
        return {"phase": None, "subphase": None}
    ps = data.get("phase_state")
    if not isinstance(ps, dict):
        return {"phase": None, "subphase": None}
    return {
        "phase": ps.get("phase"),
        "subphase": ps.get("subphase"),
    }


def _settings_from_file(novel_root: Path) -> list[dict]:
    """读 config/setting_research_output.yaml，每方向 → {name, description, levels_count, chapters_count}。"""
    path = Path(novel_root) / "config" / "setting_research_output.yaml"
    data = read_yaml(path)
    if not isinstance(data, dict):
        return []
    _skip = {"world_id", "version", "genre", "theme", "reference"}
    out = []
    for key, val in data.items():
        if key in _skip or not isinstance(val, dict):
            continue
        out.append(
            {
                "name": safe_str(val.get("name")) or key,
                "description": safe_str(val.get("description")),
                "levels_count": _size(val.get("levels")),
                "chapters_count": _size(val.get("chapters")),
            }
        )
    return out


def _size(value) -> int:
    return len(value) if isinstance(value, (list, dict)) else 0


def _world_from_file(novel_root: Path) -> dict:
    """读 config/world.yaml：name/era/rules + scopes。"""
    data = read_yaml(Path(novel_root) / "config" / "world.yaml")
    if not isinstance(data, dict):
        return {"name": "", "era": "", "rules": "", "scopes": []}
    world = data.get("world")
    if not isinstance(world, dict):
        world = data
    scopes = data.get("scopes") or []
    scope_list = [
        {
            "id": safe_str(s.get("id")),
            "name": safe_str(s.get("name")),
            "description": safe_str(s.get("description")),
        }
        for s in scopes
        if isinstance(s, dict)
    ]
    return {
        "name": safe_str(world.get("name")),
        "era": safe_str(world.get("era")),
        "rules": safe_str(world.get("rules")),
        "scopes": scope_list,
    }


def _discussion_summary(novel_root: Path) -> dict:
    """读 config/design_session.yaml 的 summary + last_updated + session_file。"""
    data = read_yaml(Path(novel_root) / "config" / "design_session.yaml")
    if not isinstance(data, dict):
        return {"summary": "", "last_updated": "", "session_file": ""}
    return {
        "summary": safe_str(data.get("summary")),
        "last_updated": safe_str(data.get("last_updated")),
        "session_file": safe_str(data.get("session_file")),
    }


def discussion_snapshot(novel_root) -> dict:
    """返回当前小说的设定讨论/设定情况快照（确定性、无 LLM、全缺安全）。"""
    from src.workbench.common import novel_meta

    novel_root = Path(novel_root)
    meta = novel_meta(novel_root)
    return {
        "phase": _phase_from_state(novel_root),
        "synopsis": safe_str(meta.get("synopsis")),
        "world": _world_from_file(novel_root),
        "settings": _settings_from_file(novel_root),
        "discussion_summary": _discussion_summary(novel_root),
    }