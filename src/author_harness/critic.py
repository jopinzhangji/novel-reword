"""
I3：Critic（最小实现）

当前先提供规则评分，不引入额外 LLM 调用。
目标：输出可观测字段 pace_deviation / subplot_reveal_deviation 及原因。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.author_harness.policy_assembler import PacingContract


@dataclass(frozen=True)
class CriticScore:
    pace_deviation: float
    subplot_reveal_deviation: float
    reason: str


def evaluate_body_against_pacing(
    contract: PacingContract,
    body: str,
    growth_standings: Any = None,
) -> CriticScore:
    """
    对正文进行轻量规则评分（0 越好，1 越差）。

    评分策略（最小版）：
    - 铺垫窗口出现强揭示关键词，判定暗线越级；
    - 兑现窗口几乎无推进词，判定节奏滞后；
    - 推进窗口过多强揭示词，判定节奏过快。

    G2（SDD D11）：`growth_standings`（成长站姿，可选）存在**兑现边缘**角色但正文未出现揭示词 → 判定「悬置回响」，
    小幅上调 `subplot_reveal_deviation`。默认 None → 行为与旧版逐字节一致。
    """
    text = (body or "").strip()
    if not text:
        return CriticScore(0.5, 0.5, "正文为空，无法评估节奏与暗线显露")

    reveal_hits = _count_hits(text, _REVEAL_KEYWORDS)
    progress_hits = _count_hits(text, _PROGRESS_KEYWORDS)

    # G2「悬置回响」：存在兑现边缘角色但正文未出现揭示词 → 判定该回响悬置未承接。
    hanging_note = ""
    if growth_standings is not None:
        edges = getattr(growth_standings, "payoff_edge", None)
        if edges and reveal_hits == 0:
            hanging_note = "；悬置回响（兑现边缘角色未承接）"

    if contract.goal_window == "铺垫":
        subplot_dev = 1.0 if reveal_hits > 0 else 0.0
        pace_dev = 0.8 if reveal_hits > 1 else 0.1
        subplot_dev, reason = _with_hanging(
            subplot_dev,
            "铺垫窗口应抑制揭示；检测到揭示词" if reveal_hits > 0 else "铺垫窗口未检测到越级揭示",
            hanging_note,
        )
        return CriticScore(pace_deviation=pace_dev, subplot_reveal_deviation=subplot_dev, reason=reason)

    if contract.goal_window == "兑现":
        pace_dev = 0.7 if progress_hits == 0 else 0.1
        subplot_dev = 0.0 if reveal_hits > 0 else 0.4
        subplot_dev, reason = _with_hanging(
            subplot_dev,
            "兑现窗口推进不足" if progress_hits == 0 else "兑现窗口推进强度正常",
            hanging_note,
        )
        return CriticScore(pace_deviation=pace_dev, subplot_reveal_deviation=subplot_dev, reason=reason)

    # 推进窗口：允许一定推进，但不宜强揭示过多
    subplot_dev = 0.7 if reveal_hits > 1 else (0.3 if reveal_hits == 1 else 0.0)
    pace_dev = 0.6 if reveal_hits > 2 else 0.1
    subplot_dev, reason = _with_hanging(
        subplot_dev,
        "推进窗口揭示强度偏高" if reveal_hits > 1 else "推进窗口节奏正常",
        hanging_note,
    )
    return CriticScore(pace_deviation=pace_dev, subplot_reveal_deviation=subplot_dev, reason=reason)


def _with_hanging(subplot_dev: float, reason: str, hanging_note: str) -> tuple[float, str]:
    """G2：悬置回响时小幅上调 subplot_reveal_deviation（+0.15，封顶 1.0）并追加原因。无则原样返回。"""
    if not hanging_note:
        return subplot_dev, reason
    return min(1.0, subplot_dev + 0.15), reason + hanging_note


def _count_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for k in keywords if k in text)


_REVEAL_KEYWORDS: tuple[str, ...] = (
    "真相",
    "揭开",
    "身份",
    "幕后",
    "原来",
    "揭示",
    "底牌",
)

_PROGRESS_KEYWORDS: tuple[str, ...] = (
    "决定",
    "行动",
    "推进",
    "达成",
    "冲突",
    "对峙",
    "转折",
)

