"""
I3：Critic（最小实现）

当前先提供规则评分，不引入额外 LLM 调用。
目标：输出可观测字段 pace_deviation / subplot_reveal_deviation 及原因。
"""
from __future__ import annotations

from dataclasses import dataclass

from src.author_harness.policy_assembler import PacingContract


@dataclass(frozen=True)
class CriticScore:
    pace_deviation: float
    subplot_reveal_deviation: float
    reason: str


def evaluate_body_against_pacing(contract: PacingContract, body: str) -> CriticScore:
    """
    对正文进行轻量规则评分（0 越好，1 越差）。

    评分策略（最小版）：
    - 铺垫窗口出现强揭示关键词，判定暗线越级；
    - 兑现窗口几乎无推进词，判定节奏滞后；
    - 推进窗口过多强揭示词，判定节奏过快。
    """
    text = (body or "").strip()
    if not text:
        return CriticScore(0.5, 0.5, "正文为空，无法评估节奏与暗线显露")

    reveal_hits = _count_hits(text, _REVEAL_KEYWORDS)
    progress_hits = _count_hits(text, _PROGRESS_KEYWORDS)

    if contract.goal_window == "铺垫":
        subplot_dev = 1.0 if reveal_hits > 0 else 0.0
        pace_dev = 0.8 if reveal_hits > 1 else 0.1
        return CriticScore(
            pace_deviation=pace_dev,
            subplot_reveal_deviation=subplot_dev,
            reason="铺垫窗口应抑制揭示；检测到揭示词" if reveal_hits > 0 else "铺垫窗口未检测到越级揭示",
        )

    if contract.goal_window == "兑现":
        pace_dev = 0.7 if progress_hits == 0 else 0.1
        subplot_dev = 0.0 if reveal_hits > 0 else 0.4
        return CriticScore(
            pace_deviation=pace_dev,
            subplot_reveal_deviation=subplot_dev,
            reason="兑现窗口推进不足" if progress_hits == 0 else "兑现窗口推进强度正常",
        )

    # 推进窗口：允许一定推进，但不宜强揭示过多
    subplot_dev = 0.7 if reveal_hits > 1 else (0.3 if reveal_hits == 1 else 0.0)
    pace_dev = 0.6 if reveal_hits > 2 else 0.1
    return CriticScore(
        pace_deviation=pace_dev,
        subplot_reveal_deviation=subplot_dev,
        reason="推进窗口揭示强度偏高" if reveal_hits > 1 else "推进窗口节奏正常",
    )


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

