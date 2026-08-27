from src.author_harness.critic import CriticScore
from src.author_harness.policy_gate import validate_candidate_patch
from src.author_harness.policy_updater import build_candidate_patch


def test_build_candidate_patch_high_risk() -> None:
    critic = CriticScore(
        pace_deviation=0.9,
        subplot_reveal_deviation=0.8,
        reason="铺垫窗口出现越级揭示",
    )
    patch = build_candidate_patch(
        critic=critic,
        trigger_input="这段太快了，暗线暴露太多",
        source_refs=["turn:12", "critic:pace"],
    )
    assert patch.operation == "add_rule"
    assert patch.risk_level == "high"
    assert patch.manual_review_required is True


def test_validate_candidate_patch_accepts_valid_patch() -> None:
    critic = CriticScore(0.2, 0.1, "节奏正常")
    patch = build_candidate_patch(
        critic=critic,
        trigger_input="保持节奏",
        source_refs=["turn:13"],
    )
    result = validate_candidate_patch(patch)
    assert result.accepted is True
    assert result.reasons == []
    assert result.manual_review_required is True


def test_validate_candidate_patch_rejects_invalid_scope_and_empty_evidence() -> None:
    critic = CriticScore(0.7, 0.7, "偏差较高")
    patch = build_candidate_patch(
        critic=critic,
        trigger_input="",
        source_refs=[],
        scope="invalid_scope",
    )
    result = validate_candidate_patch(patch)
    assert result.accepted is False
    assert any("scope 不合法" in reason for reason in result.reasons)
    assert any("缺少 trigger_input 证据" in reason for reason in result.reasons)
    assert any("缺少 source_refs 证据" in reason for reason in result.reasons)

