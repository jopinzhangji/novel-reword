"""G4 大纲 / 节拍情志条（SDD D13 §4 章节·情志节拍）。

确定性，委托 outline_store：读 outline.yaml + progress.yaml，
产出当前章/拍指针与进度引用缺失标注（missing_ref）。
"""
from __future__ import annotations

from src.runtime.outline_store import load_outline_snapshot, resolve_current_beat


def outline(novel_root) -> dict:
    """整树大纲 + 当前指针。无大纲 → {"present": False}。"""
    snap = load_outline_snapshot(novel_root)
    if snap is None:
        return {"present": False}
    beat = resolve_current_beat(snap, soft_max_turns=3)
    current = _beat_to_dict(beat) if beat else None
    return {
        "present": True,
        "warnings": snap.warnings,
        "chapters": snap.outline.get("chapters") or [],
        "progress": snap.progress,
        "current": current,
    }


def progress(novel_root) -> dict:
    """进度指针视图（rhythm 页）：当前 beat + next_beat_hint + missing_ref。"""
    snap = load_outline_snapshot(novel_root)
    if snap is None:
        return {"present": False}
    beat = resolve_current_beat(snap, soft_max_turns=3)
    return {
        "present": True,
        "raw_progress": snap.progress or {},
        "current": _beat_to_dict(beat) if beat else None,
        "default_soft_max_turns": 3,
    }


def _beat_to_dict(beat) -> dict:
    return {
        "chapter_id": beat.chapter_id,
        "chapter_title": beat.chapter_title,
        "dramatic_question": beat.dramatic_question,
        "beat_id": beat.beat_id,
        "beat_intent": beat.beat_intent,
        "suggested_scope_id": beat.suggested_scope_id,
        "tags": beat.tags,
        "turns_in_beat": beat.turns_in_beat,
        "soft_max_turns": beat.soft_max_turns,
        "next_beat_hint": beat.next_beat_hint,
        "missing_ref": beat.missing_ref,
    }