"""G4 作品索引 / 进度总览（SDD D13 §4 多小说进度卡片）。

全部只读、确定性：委托 outline_store / relationship_graph / character_growth，
对 data/novels/<slug>/ 逐书聚合「章节/节拍/回合 + 成长爆发 + 关系边数 + 最近回合」。
"""
from __future__ import annotations

from pathlib import Path

from src.workbench.common import (
    characters_config,
    characters_roster,
    novel_meta,
    novel_roots,
    scope_event_dirs,
)
from src.runtime.character_growth import load_growth_state
from src.runtime.outline_store import load_outline_snapshot, resolve_current_beat
from src.runtime.relationship_graph import load_graph, relationship_graph_yaml_path


def _growth_totals(novel_root: Path) -> dict:
    """全书成长聚合：有 growth 状态的角色数 + transition_log 总条数。"""
    roster = characters_roster(novel_root)
    with_state = 0
    transitions = 0
    for c in roster:
        cid = c.get("id")
        if not cid:
            continue
        state = load_growth_state(cid, novel_root)
        if state.transition_log:
            with_state += 1
            transitions += len(state.transition_log)
    return {"characters_with_growth": with_state, "transition_entries": transitions}


def _outline_pointer(novel_root: Path) -> dict:
    """当前章/拍/回合指针；无大纲 → 空。"""
    snap = load_outline_snapshot(novel_root)
    if snap is None:
        return {}
    beat = resolve_current_beat(snap, soft_max_turns=3)
    if beat is None:
        return {"has_outline": True, "had_any_beat": False}
    return {
        "has_outline": True,
        "had_any_beat": True,
        "chapter_id": beat.chapter_id,
        "chapter_title": beat.chapter_title,
        "beat_id": beat.beat_id,
        "beat_intent": beat.beat_intent,
        "turns_in_beat": beat.turns_in_beat,
        "missing_ref": beat.missing_ref,
    }


def _graph_edge_count(novel_root: Path) -> int:
    path = relationship_graph_yaml_path(novel_root)
    graph = load_graph(path)
    return len(graph.get("edges") or [])


def _recent_event_count(novel_root: Path) -> int:
    total = 0
    for scope_dir in scope_event_dirs(novel_root):
        total += len(list((scope_dir / "events").glob("turn_*.md")))
    return total


def novel_summary(novel_root: Path) -> dict:
    """单书进度摘要卡（多小说总览 / dashboard 摘要卡共用）。"""
    growth = _growth_totals(novel_root)
    pointer = _outline_pointer(novel_root)
    return {
        **novel_meta(novel_root),
        "growth": growth,
        "outline_pointer": pointer,
        "edge_count": _graph_edge_count(novel_root),
        "scope_event_count": _recent_event_count(novel_root),
        "character_count": len(characters_roster(novel_root)),
    }


def index_novels(project_root: Path) -> list[dict]:
    """全部小说进度卡片（?center 排序：索引序）。"""
    out = []
    for root in novel_roots(project_root):
        out.append(novel_summary(root))
    return out