"""
I4b：Policy Gate（最小实现）

对 candidate patch 做基础门禁校验，仅输出校验结论。
"""
from __future__ import annotations

from dataclasses import dataclass

from src.author_harness.policy_updater import PolicyCandidatePatch

_ALLOWED_SCOPES: set[str] = {"global", "novel", "phase", "intent"}
_ALLOWED_OPERATIONS: set[str] = {"add_rule", "remove_rule", "update_rule"}
_IMMUTABLE_RULE_HINTS: tuple[str, ...] = (
    "两阶段审阅",
    "作者确认门闩",
    "不可变核心规则",
)


@dataclass(frozen=True)
class GateResult:
    accepted: bool
    reasons: list[str]
    manual_review_required: bool


def validate_candidate_patch(patch: PolicyCandidatePatch) -> GateResult:
    reasons: list[str] = []

    if not patch.patch_id.strip():
        reasons.append("缺少 patch_id")
    if patch.scope not in _ALLOWED_SCOPES:
        reasons.append(f"scope 不合法: {patch.scope}")
    if patch.operation not in _ALLOWED_OPERATIONS:
        reasons.append(f"operation 不合法: {patch.operation}")
    if not patch.target.strip():
        reasons.append("缺少 target")
    if not patch.content.strip():
        reasons.append("缺少 content")
    if not patch.trigger_input.strip():
        reasons.append("缺少 trigger_input 证据")
    if not patch.source_refs:
        reasons.append("缺少 source_refs 证据")

    content = patch.content.strip()
    if any(hint in content for hint in _IMMUTABLE_RULE_HINTS):
        reasons.append("命中不可变核心规则，禁止自动通过")

    accepted = len(reasons) == 0
    return GateResult(
        accepted=accepted,
        reasons=reasons,
        manual_review_required=(not accepted) or patch.manual_review_required,
    )

