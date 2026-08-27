from src.author_harness.critic import evaluate_body_against_pacing
from src.author_harness.policy_assembler import PacingContract


def test_critic_flags_reveal_in_pudian_window() -> None:
    contract = PacingContract(
        pace_mode="slow_burn",
        goal_window="铺垫",
        plot_exposure_budget="low",
        subplot_reveal_budget="signal",
        character_action_caps={},
        forbidden_moves=[],
    )
    body = "他终于揭开了幕后真相，原来对方就是隐藏多年的身份。"
    score = evaluate_body_against_pacing(contract, body)
    assert score.subplot_reveal_deviation >= 0.9
    assert score.pace_deviation >= 0.8


def test_critic_accepts_normal_progress_window_text() -> None:
    contract = PacingContract(
        pace_mode="balanced",
        goal_window="推进",
        plot_exposure_budget="medium",
        subplot_reveal_budget="partial",
        character_action_caps={},
        forbidden_moves=[],
    )
    body = "主角决定先行动试探，双方在街角短暂对峙，冲突略有推进。"
    score = evaluate_body_against_pacing(contract, body)
    assert score.pace_deviation <= 0.2
    assert score.subplot_reveal_deviation <= 0.3

