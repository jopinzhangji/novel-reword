from src.author_harness.policy_store import load_policy_store_from_runtime


def test_load_policy_store_defaults_empty() -> None:
    cfg = load_policy_store_from_runtime({})
    assert cfg.version == "v1"
    assert cfg.global_rules == []
    assert cfg.novel_rules == {}
    assert cfg.phase_rules == {}
    assert cfg.intent_rules == {}
    assert cfg.default_pace_mode == "balanced"
    assert cfg.allow_dynamic_pace_adjust is True


def test_load_policy_store_from_author_harness_path() -> None:
    runtime = {
        "runtime": {
            "author_harness": {
                "policy_store": {
                    "version": "v2",
                    "default_pace_mode": "balanced",
                    "allow_dynamic_pace_adjust": True,
                    "global_rules": ["A", "", "  ", "B"],
                    "novel_rules": {"xianxia": ["N1", "N2"]},
                    "phase_rules": {"MAIN_WRITING_REVIEW": ["P1"]},
                    "intent_rules": {"review_revise": ["I1"]},
                }
            }
        }
    }
    cfg = load_policy_store_from_runtime(runtime)
    assert cfg.version == "v2"
    assert cfg.global_rules == ["A", "B"]
    assert cfg.novel_rules == {"xianxia": ["N1", "N2"]}
    assert cfg.phase_rules == {"MAIN_WRITING_REVIEW": ["P1"]}
    assert cfg.intent_rules == {"review_revise": ["I1"]}
    assert cfg.default_pace_mode == "balanced"
    assert cfg.allow_dynamic_pace_adjust is True


def test_resolve_rules_stacks_and_dedupes() -> None:
    runtime = {
        "runtime": {
            "policy_store": {
                "global_rules": ["G1", "SAME"],
                "novel_rules": {"x": ["N1", "SAME"]},
                "phase_rules": {"P": ["P1", "SAME"]},
                "intent_rules": {"I": ["I1", "SAME"]},
            }
        }
    }
    cfg = load_policy_store_from_runtime(runtime)
    out = cfg.resolve_rules(novel_profile="x", phase="P", intent_id="I")
    assert out == ["G1", "SAME", "N1", "P1", "I1"]


def test_resolve_pace_mode_default_and_dynamic() -> None:
    cfg = load_policy_store_from_runtime(
        {
            "runtime": {
                "policy_store": {
                    "default_pace_mode": "balanced",
                    "allow_dynamic_pace_adjust": True,
                }
            }
        }
    )
    assert cfg.resolve_pace_mode(None) == "balanced"
    assert cfg.resolve_pace_mode("slow_burn") == "slow_burn"
    assert cfg.resolve_pace_mode("invalid") == "balanced"


def test_resolve_pace_mode_respects_disable_dynamic() -> None:
    cfg = load_policy_store_from_runtime(
        {
            "runtime": {
                "policy_store": {
                    "default_pace_mode": "balanced",
                    "allow_dynamic_pace_adjust": False,
                }
            }
        }
    )
    assert cfg.resolve_pace_mode("push") == "balanced"

