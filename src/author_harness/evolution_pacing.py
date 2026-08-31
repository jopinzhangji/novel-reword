"""
G2 演进层 ↔ 叙事策略层耦闸（SDD D11）：成长站姿（GrowthStandings）前馈给节奏契约/Critic。

把在场关键角色的成长状态（`growth_state.yaml`）聚合成紧凑、可判定的「成长站姿」：
- `load_growth_standings`：读各在场角色成长 state，汇总五维计数与「兑现边缘」标记（payoff_edge）。
- `format_standings_hint`：转一行提示（供 Critic 解释 / 日志观测）；空则返回空串。
确定性、无 LLM、不写盘。默认由上层 gated（`runtime.evolution_pacing.enabled=false` 时调用方不传参）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 会改目标/纠缠到回响的维度键（由 _GOAL_RULES 规则命中累积）。计数 ≥1 即视为「兑现边缘」信号。
_PAYOFF_KEYS = ("里程碑", "目标重估", "动机转变")
_GOAL_DIM = "goal_state"


@dataclass(frozen=True)
class GrowthStandings:
    """成长站姿：每在场角色的维度计数快照 + 处于兑现边缘的角色 id 集合。不可变、可判空。"""

    by_character: dict[str, dict[str, int]] = field(default_factory=dict)
    payoff_edge: list[str] = field(default_factory=list)

    def empty(self) -> bool:
        return not self.by_character and not self.payoff_edge


def load_growth_standings(
    data_root: Path,
    characters_config: dict[str, Any] | None,
    present_character_ids: list[str] | tuple[str, ...],
) -> GrowthStandings:
    """
    读在场关键角色成长 state（缺省回退默认）→ 生成 GrowthStandings。
    - by_character[cid] = 五维计数总和（无则该维为 0），助力轻量「此刻推进偏向」判定。
    - payoff_edge：goal_state 命中 _PAYOFF_KEYS 任一 ≥1 的角色（其回响应在本轮正文兑现，未承接则判定悬置）。
    确定性：仅读文件 + 简单聚合，无 LLM、无写盘。
    """
    from src.runtime.character_growth import _COUNTING_DIMS, load_growth_state

    by_char: dict[str, dict[str, int]] = {}
    payoff: list[str] = []
    for cid in sorted({str(x) for x in present_character_ids if x}):
        st = load_growth_state(cid, data_root)
        counts: dict[str, int] = {}
        for dim in _COUNTING_DIMS:
            d = dict(getattr(st, dim) or {})
            counts[dim] = sum(int(v) for v in d.values() if isinstance(v, int) and v > 0)
        by_char[cid] = counts
        goal = dict(getattr(st, _GOAL_DIM) or {})
        if any(int(goal.get(k) or 0) >= 1 for k in _PAYOFF_KEYS):
            payoff.append(cid)
    return GrowthStandings(by_character=by_char, payoff_edge=payoff)


def format_standings_hint(standings: GrowthStandings) -> str:
    """转一行紧凑提示（付费边缘 + 在场角色维度摘要）；无可展示内容则返回空串。"""
    if not standings or standings.empty():
        return ""
    lines: list[str] = []
    if standings.payoff_edge:
        lines.append("兑现边缘角色：" + "、".join(standings.payoff_edge))
    for cid in sorted(standings.by_character):
        counts = standings.by_character[cid]
        summary = "，".join(f"{k.replace('_state','')}={v}" for k, v in counts.items() if v)
        if summary:
            lines.append(f"{cid}：{summary}")
    if not lines:
        return ""
    return "【成长站姿】" + " | ".join(lines)