"""
I4a：PolicyUpdater（最小实现）

仅生成 candidate patch，不自动生效。
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from src.author_harness.critic import CriticScore


Scope = str
Operation = str
RiskLevel = str


@dataclass(frozen=True)
class PolicyCandidatePatch:
    patch_id: str
    scope: Scope
    target: str
    operation: Operation
    content: str
    trigger_input: str
    critic_scores: dict[str, float]
    source_refs: list[str]
    risk_level: RiskLevel
    manual_review_required: bool


def build_candidate_patch(
    *,
    critic: CriticScore,
    trigger_input: str,
    source_refs: list[str] | None = None,
    scope: Scope = "phase",
    target: str = "phase:MAIN_WRITING",
) -> PolicyCandidatePatch:
    """
    根据 Critic 分数生成最小候选补丁。

    规则（最小版）：
    - 偏差较高时建议 add_rule；
    - 偏差较低时建议 update_rule（微调提醒）；
    - 不自动生效，默认人工审阅。
    """
    refs = [r for r in (source_refs or []) if str(r).strip()]
    max_dev = max(critic.pace_deviation, critic.subplot_reveal_deviation)

    if max_dev >= 0.7:
        operation = "add_rule"
        risk_level = "high"
        content = (
            "本轮命中高偏差：加强节奏约束，限制暗线揭示等级；"
            f"原因：{critic.reason}"
        )
    elif max_dev >= 0.4:
        operation = "update_rule"
        risk_level = "medium"
        content = (
            "本轮命中中偏差：建议提高铺垫窗口下的揭示抑制与推进预算约束；"
            f"原因：{critic.reason}"
        )
    else:
        operation = "update_rule"
        risk_level = "low"
        content = (
            "本轮偏差较低：建议维持当前策略并微调提示语，避免节奏漂移。"
        )

    return PolicyCandidatePatch(
        patch_id=f"patch-{uuid4().hex[:12]}",
        scope=scope,
        target=target,
        operation=operation,
        content=content,
        trigger_input=(trigger_input or "").strip(),
        critic_scores={
            "pace_deviation": float(critic.pace_deviation),
            "subplot_reveal_deviation": float(critic.subplot_reveal_deviation),
        },
        source_refs=refs,
        risk_level=risk_level,
        manual_review_required=True,
    )

