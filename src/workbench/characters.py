"""G4 人物情况视图（SDD D13 §4 人物·成长五维 / 视野 / 记忆 / 屏外线）。

确定性，委托 character_growth / info_view / file_sync。
记忆分层：盘上仅 L1 事实（book/characters/<id>/events/turn_*.md 与 scope 事件）持久化；
L2 解释 / L3 策略为运行期内存态，未落盘 → 一律给 `runtime_only_layers: true` 标，
前端据此刻意展示「会话内可见、重启即失」而非虚构历史。（G4a 只读盘上既有数据，不新增持久化。）
"""
from __future__ import annotations

from pathlib import Path

from src.retrieval.info_view import event_visible_to_character
from src.runtime.character_growth import load_growth_state
from src.runtime.file_sync import load_off_screen_threads, load_scope_events_from_disk
from src.runtime.memory_layers import classify_memory_layer
from src.workbench.common import (
    characters_roster,
    novel_meta,
    scope_event_dirs,
)


def character_events_on_disk(novel_root: Path, character_id: str) -> list[dict]:
    """读 book/characters/<id>/events/turn_*.md（L1 事实持久化源）。"""
    cid_dir = Path(novel_root) / "book" / "characters" / str(character_id) / "events"
    out: list[dict] = []
    if not cid_dir.is_dir():
        return out
    for path in sorted(cid_dir.glob("turn_*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
        body = text.split("\n\n", 1)[1] if "\n\n" in text else text
        summary = body.strip("\n ")
        out.append(
            {
                "turn_file": path.name,
                "summary": summary,
                "layer": classify_memory_layer(summary),
            }
        )
    return out


def character_view(novel_root: Path, character_id: str) -> dict:
    """信息视野：对每 scope 事件统计 已知 vs 未知（复用 info_view 可见性判定）。"""
    total = known = 0
    per_scope: list[dict] = []
    sample: list[dict] = []
    for scope_dir in scope_event_dirs(novel_root):
        sid = scope_dir.name
        events = load_scope_events_from_disk(novel_root, sid)
        scope_known = scope_total = 0
        for e in events:
            scope_total += 1
            total += 1
            if event_visible_to_character(e, character_id):
                scope_known += 1
                known += 1
                if len(sample) < 5:
                    sample.append(
                        {
                            "scope_id": sid,
                            "summary": (e.get("summary") or "").strip()[:200],
                        }
                    )
        per_scope.append(
            {
                "scope_id": sid,
                "total_events": scope_total,
                "known": scope_known,
                "unknown": max(0, scope_total - scope_known),
            }
        )
    return {
        "total_events": total,
        "known": known,
        "unknown": max(0, total - known),
        "per_scope": per_scope,
        "sample_known": sample,
    }


_DIM_LABELS = {
    "power_state": "能力",
    "mind_state": "心理",
    "social_state": "关系",
    "goal_state": "目标",
    "resource_state": "资源",
}
# 单维「深」的成长量基准：level = min(1.0, Σ(子状态值) / scale)。可调；见 D13 §6.6 #2。
_GROWTH_DEPTH_SCALE = 6.0


def radar_vector(growth: dict) -> list[dict]:
    """五维成长深度雷达向量（确定性，无 LLM）。

    每维 `intensity = Σ(数值型子状态值)`，`level = min(1, intensity / scale)`（0..1，
    四舍五入 3 位）。语义为「成长深度」（无状态=0、多个成熟子状态=1），**非绝对特质分**。
    返回 5 项 `{dim, label, level, intensity, attributes}`（缺失维给空 attributes、0）。
    """
    out: list[dict] = []
    for key in ("power_state", "mind_state", "social_state", "goal_state", "resource_state"):
        d = growth.get(key) if isinstance(growth, dict) else None
        d = d if isinstance(d, dict) else {}
        numeric = {k: v for k, v in d.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)}
        intensity = float(sum(numeric.values()))
        out.append(
            {
                "dim": key,
                "label": _DIM_LABELS[key],
                "level": round(min(1.0, intensity / _GROWTH_DEPTH_SCALE), 3),
                "intensity": intensity,
                "attributes": list(numeric),
            }
        )
    return out


def character_detail(novel_root: Path, character_id: str) -> dict:
    """单人物完整卡：五维成长 + 雷达 + 视野 + L1 记忆 + 屏外线 + 运行期态标注。"""
    cid = str(character_id)
    state = load_growth_state(cid, novel_root)
    growth = {
        "power_state": state.power_state,
        "mind_state": state.mind_state,
        "social_state": state.social_state,
        "goal_state": state.goal_state,
        "resource_state": state.resource_state,
        "transition_log": state.transition_log,
    }
    return {
        "id": cid,
        "growth": growth,
        "growth_radar": radar_vector(growth),
        "view": character_view(novel_root, cid),
        "memories_l1": character_events_on_disk(novel_root, cid),
        "off_screen_threads": load_off_screen_threads(novel_root, cid),
        "runtime_only_layers": True,  # L2/L3 未落盘，见模块 docstring
    }


def characters_index(novel_root: Path) -> list[dict]:
    """全书人物索引：名册 + 每角色成长摘要 + 盘上 L1 记忆数。"""
    out = []
    for c in characters_roster(novel_root):
        cid = c.get("id")
        if not cid:
            continue
        state = load_growth_state(cid, novel_root)
        dims_with_state = sum(1 for d in state.to_dict().values() if isinstance(d, dict) and d)
        out.append(
            {
                "id": cid,
                "name": c.get("name") or cid,
                "role": c.get("role") or "",
                "growth_dims_with_state": dims_with_state,
                "transition_entries": len(state.transition_log),
                "memory_count": len(character_events_on_disk(novel_root, cid)),
            }
        )
    return out