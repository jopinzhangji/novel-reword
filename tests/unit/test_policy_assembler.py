from src.author_harness.policy_assembler import resolve_pacing_contract


def test_resolve_pacing_contract_default_balanced() -> None:
    c = resolve_pacing_contract({})
    assert c.pace_mode == "balanced"
    assert c.goal_window == "推进"
    assert c.subplot_reveal_budget == "partial"


def test_resolve_pacing_contract_goal_prefers_pudian() -> None:
    c = resolve_pacing_contract({}, chapter_goal="这一章主要做铺垫与埋伏笔")
    assert c.goal_window == "铺垫"
    assert c.subplot_reveal_budget == "signal"


def test_resolve_pacing_contract_respects_dynamic_mode() -> None:
    runtime = {
        "runtime": {
            "author_harness": {
                "policy_store": {
                    "default_pace_mode": "balanced",
                    "allow_dynamic_pace_adjust": True,
                }
            }
        }
    }
    c = resolve_pacing_contract(runtime, requested_mode="push")
    assert c.pace_mode == "push"
    assert c.goal_window == "兑现"

