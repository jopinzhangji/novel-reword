"""G2 演进层↔叙事策略层耦闸（SDD D11）：成长站姿前馈 + 节拍标签反馈。默认关→行为不变，开启→可断言。"""
from pathlib import Path

from src.author_harness.critic import evaluate_body_against_pacing
from src.author_harness.evolution_pacing import (
    GrowthStandings,
    format_standings_hint,
    load_growth_standings,
)
from src.author_harness.policy_assembler import PacingContract, resolve_pacing_contract
from src.runtime.character_growth import (
    GrowthGuard,
    default_growth_state,
    match_rules_for_event,
    save_growth_state,
)
from src.runtime.storage import MemoryStorage


def _tmp_root(tmp_path) -> Path:
    return tmp_path / "novel"


def _empty_standings() -> GrowthStandings:
    return GrowthStandings(by_character={}, payoff_edge=[])


# --- load_growth_standings：裁决兑现边缘 ---


def test_load_growth_standings_payoff_edge(tmp_path):
    root = _tmp_root(tmp_path)
    st = default_growth_state("li")
    st.goal_state = {"里程碑": 1}  # goal_affirmed 命中的维度键
    save_growth_state(st, root)
    cfg = {"characters": [{"id": "li", "name": "李逍"}]}
    s = load_growth_standings(root, cfg, ["li"])
    assert "li" in s.payoff_edge
    assert s.by_character["li"]["goal_state"] == 1
    assert format_standings_hint(s).startswith("【成长站姿】")


def test_load_growth_standings_empty(tmp_path):
    s = load_growth_standings(_tmp_root(tmp_path), None, [])
    assert s.empty()
    assert format_standings_hint(s) == ""
    # 在场但全零 → 无维度值故无可展示，提示为空串
    s2 = load_growth_standings(_tmp_root(tmp_path), None, ["nobody"])
    assert s2.payoff_edge == [] and format_standings_hint(s2) == ""


# --- 前馈 · 成长→节奏：契约偏置 ---


def test_contract_override_toward_cue_on_payoff_edge():
    base = resolve_pacing_contract({"pacing": {}}, chapter_goal="", requested_mode=None)
    assert base.goal_window == "推进"
    gs = GrowthStandings(by_character={"li": {}}, payoff_edge=["li"])
    c = resolve_pacing_contract({"pacing": {}}, chapter_goal="", growth_standings=gs)
    assert c.goal_window == "兑现"
    assert any("勿悬置已到兑现边缘" in m for m in c.forbidden_moves)


def test_contract_override_noop_when_standings_empty_or_already_cue():
    base = resolve_pacing_contract({"pacing": {}}, chapter_goal="", requested_mode=None)
    empty = GrowthStandings(by_character={"li": {"goal_state": 0}}, payoff_edge=[])
    assert resolve_pacing_contract({"pacing": {}}, chapter_goal="", growth_standings=empty) == base
    # 基契约已是兑现窗（chapter_goal 含"兑现"）→ 不因成长站姿改写
    cue_base = resolve_pacing_contract({"pacing": {}}, chapter_goal="龙脉兑现", requested_mode=None)
    assert cue_base.goal_window == "兑现"
    gs = GrowthStandings(by_character={}, payoff_edge=["li"])
    assert resolve_pacing_contract({"pacing": {}}, chapter_goal="龙脉兑现", growth_standings=gs) == cue_base


def test_contract_override_none_default_unchanged():
    assert resolve_pacing_contract({"pacing": {}}, chapter_goal="", growth_standings=None) == PacingContract(
        pace_mode=resolve_pacing_contract({"pacing": {}}, chapter_goal="").pace_mode,
        goal_window="推进",
        plot_exposure_budget="medium",
        subplot_reveal_budget="partial",
        character_action_caps={"protagonist_high_impact_max": 1, "supporting_high_impact_max": 1},
        forbidden_moves=["避免跳过关键因果桥接"],
    )


# --- 前馈 · 成长→审阅：Critic 悬置回响 ---


def test_critic_hanging_payoff_bumps_deviation():
    contract = PacingContract(
        pace_mode="normal", goal_window="推进", plot_exposure_budget="medium",
        subplot_reveal_budget="partial",
        character_action_caps={"protagonist_high_impact_max": 1, "supporting_high_impact_max": 1},
        forbidden_moves=[],
    )
    base = evaluate_body_against_pacing(contract, "平淡无波地走在长街")
    assert base.subplot_reveal_deviation == 0.0
    gs = GrowthStandings(by_character={}, payoff_edge=["li"])
    hung = evaluate_body_against_pacing(contract, "平淡无波地走在长街", growth_standings=gs)
    assert hung.subplot_reveal_deviation > base.subplot_reveal_deviation
    assert hung.subplot_reveal_deviation == min(1.0, base.subplot_reveal_deviation + 0.15)
    assert "悬置回响" in hung.reason
    # 正文已揭示 → 不判悬置
    covered = evaluate_body_against_pacing(contract, "他猛地揭开真相下落", growth_standings=gs)
    assert "悬置回响" not in covered.reason
    # 默认 None → 与基版本一致
    assert evaluate_body_against_pacing(contract, "平淡无波地走在长街", growth_standings=None) == base


# --- 反馈 · 节拍→成长：标签补足命中 ---


def test_match_rules_supplement_by_beat_tags():
    assert match_rules_for_event("平凡日常，采买米粮") == []
    fired = match_rules_for_event("平凡日常，采买米粮", extra_tags=["growth:gain"])
    assert "resource_gain" in fired
    # 未知标签忽略
    assert match_rules_for_event("平凡日常，采买米粮", extra_tags=["not_a_tag"]) == []


def test_growth_for_turn_beat_tags_actually_applies(tmp_path):
    """章节节拍标 growth:gain 且事件无关键词 → 该规则被补足并经无 guard 迁移（有既有损耗可放行）。"""
    root = _tmp_root(tmp_path)
    st = MemoryStorage()
    # 先损耗累积，使 resource_gain 有代价可放行（避免无代价收益被拒）
    from src.runtime.character_growth import apply_off_screen_transitions

    apply_off_screen_transitions(st, root, character_id="li", entries=[{"summary": "行商失败，损失惨重"}])
    # 事件本身无"获得/寻得"等关键词
    from src.runtime.character_growth import apply_growth_transition_for_turn

    results, audit = apply_growth_transition_for_turn(
        st, root, scope_id="main", turn_index=70,
        present_character_ids=["li"],
        event_entry={"summary": "他一如既往地处理琐事"},
        guard=GrowthGuard(),
        beat_tags=["growth:gain"],
    )
    assert "resource_gain" in results["li"]
    # 补足命中已实际施加状态：resources 增益 1
    from src.runtime.character_growth import load_growth_state

    state = load_growth_state("li", root)
    assert state.resource_state.get("增益", 0) == 1