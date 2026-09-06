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


def _suggestion(phase: dict, synopsis: str, world: dict, settings: list, design_present: bool) -> str:
    """确定性「当前建议」：据阶段/简介/世界/设定方向推导下一步动作，无 LLM。"""
    ph = (phase or {}).get("phase")
    parts: list[str] = []
    if ph == "DESIGN_MAIN" and (phase or {}).get("subphase") == "setting_intent_bootstrap":
        parts.append("处于设定初始引导：建议先填一句话简介作种子，再说明作品类型/世界核心。")
    elif ph == "DESIGN_DISCUSSION":
        parts.append("正在设定讨论中——单轮原文在引擎线内存，保存/归档后会落到下方「最近归档讨论」。")
    if not synopsis:
        parts.append("尚未填写简介：先补一句话设定，作为设定讨论的初始种子。")
    if not (world.get("name") or "").strip() or not (world.get("era") or "").strip():
        parts.append("世界名称/时代 未填：建议进入设定讨论补齐基础世界观。")
    real = [s for s in settings if (s.get("levels_count") or 0) > 0 or (s.get("chapters_count") or 0) > 0]
    every_real = [s for s in settings if s.get("name") not in ("待定",)]
    if settings and design_present:
        parts.append(f"已生成 {len(settings)} 个设定方向（{len(real)} 个含实质内容），最近归档摘要见下方。")
    elif settings:
        parts.append(f"已生成 {len(settings)} 个方向（{len(real)} 个含实质内容）；继续讨论可深化，完成保存/归档后回到此处可查看摘要。")
    elif not design_present:
        parts.append("尚未生成设定方向：填简介后进入设定讨论即可生成。")
    if not design_present and every_real and not real:
        parts.append("方向多为占位（待定）：作者暂未说明剧情走向，建议先说明故事核心再继续。")
    return "；".join(parts) or "暂无特别建议。"


def discussion_snapshot(novel_root) -> dict:
    """返回当前小说的设定讨论/设定情况快照（确定性、无 LLM、全缺安全）。

    新增 `suggestion`（当前建议）与 `status`（紧凑情况摘要）供控制台面板顶部呈现；
    world/settings 保留详细 data 供「下转看详细情况」。
    """
    from src.workbench.common import novel_meta

    novel_root = Path(novel_root)
    meta = novel_meta(novel_root)
    phase = _phase_from_state(novel_root)
    synopsis = safe_str(meta.get("synopsis"))
    world = _world_from_file(novel_root)
    settings = _settings_from_file(novel_root)
    summary = _discussion_summary(novel_root)
    design_present = bool(summary.get("summary"))
    status = {
        "has_synopsis": bool(synopsis),
        "world_filled": bool((world.get("name") or "").strip() or (world.get("era") or "").strip()),
        "direction_count": len(settings),
        "directions_with_detail": sum(
            (s.get("levels_count") or 0) > 0 or (s.get("chapters_count") or 0) > 0 for s in settings
        ),
        "design_session_present": design_present,
    }
    return {
        "phase": phase,
        "synopsis": synopsis,
        "suggestion": _suggestion(phase, synopsis, world, settings, design_present),
        "status": status,
        "world": world,
        "settings": settings,
        "discussion_summary": summary,
    }