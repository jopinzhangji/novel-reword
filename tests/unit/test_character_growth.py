"""成长状态：骨架（1a）+ 持久化 + mind→emotions；五维迁移（1b）；GrowthGuard 强约束（阶段 2）。"""
from src.runtime.character_growth import (
    CharacterGrowthState,
    GrowthGuard,
    apply_growth_transition,
    apply_growth_transition_for_turn,
    apply_growth_transition_guarded,
    default_growth_state,
    format_growth_snippet,
    growth_state_yaml_path,
    load_growth_state,
    match_rules_for_event,
    record_mind_emotion,
    save_growth_state,
)
from src.runtime.storage import MemoryStorage


def test_default_state_fields():
    state = default_growth_state("hero")
    assert state.character_id == "hero"
    assert state.power_state == {}
    assert state.mind_state == {}
    assert state.social_state == {}
    assert state.goal_state == {}
    assert state.resource_state == {}
    assert state.transition_log == []
    assert state.version == 1


def test_save_load_roundtrip(tmp_path):
    novel_root = tmp_path / "novel"
    state = default_growth_state("su_wan")
    state.mind_state = {"stability": "high", "doubts": ["见疑于林远"]}
    state.goal_state = {"short": "查明真相"}
    state.transition_log = [{"turn": 3, "rule": "trusted_betrayal"}]
    save_growth_state(state, novel_root)
    path = growth_state_yaml_path(novel_root, "su_wan")
    assert path.is_file()
    loaded = load_growth_state("su_wan", novel_root)
    assert loaded.character_id == "su_wan"
    assert loaded.mind_state == {"stability": "high", "doubts": ["见疑于林远"]}
    assert loaded.goal_state == {"short": "查明真相"}
    assert loaded.transition_log == [{"turn": 3, "rule": "trusted_betrayal"}]


def test_load_missing_returns_default(tmp_path):
    state = load_growth_state("nobody", tmp_path / "novel")
    assert state.character_id == "nobody"
    assert state.mind_state == {}


def test_record_mind_emotion_writes_storage_slot():
    storage = MemoryStorage()
    entry = {"target_id": "lin_yuan", "emotion": "警惕", "intensity": "med", "turn": 5}
    returned = record_mind_emotion(storage, "su_wan", entry)
    assert returned == entry
    emot = storage.get_emotions("su_wan")
    assert len(emot) == 1
    assert emot[0]["target_id"] == "lin_yuan"
    assert emot[0]["emotion"] == "警惕"


def test_record_mind_emotion_target_filter():
    storage = MemoryStorage()
    record_mind_emotion(storage, "c", {"target_id": "x", "emotion": "a"})
    record_mind_emotion(storage, "c", {"target_id": "y", "emotion": "b"})
    assert len(storage.get_emotions("c", target_id="y")) == 1


def test_format_growth_snippet_empty_and_nonempty():
    assert format_growth_snippet(default_growth_state("x")) == ""
    state = default_growth_state("x")
    state.social_state = {"luo_trust": "med"}
    text = format_growth_snippet(state)
    assert "成长状态" in text
    assert "关系" in text


def test_match_rules_for_event_hits_by_keyword():
    assert match_rules_for_event("他身负重伤，九死一生") == ["near_death"]
    assert match_rules_for_event("遭到挚友背叛与出卖") == ["trusted_betrayal"]
    assert match_rules_for_event("获得至宝与灵石，并寻得线索") == ["resource_gain"]
    assert match_rules_for_event("") == []
    assert match_rules_for_event("平淡的日常对话") == []


def test_apply_growth_transition_applies_deltas_and_logs():
    state = default_growth_state("su_wan")
    state, fired = apply_growth_transition(
        state,
        {"summary": "在剑拔弩张的对峙中劫后余生，对头反水栽赃",
         "scope_id": "capital", "turn_index": 7},
    )
    assert "near_death" in fired
    assert "conflict_showdown" in fired
    assert "trusted_betrayal" in fired
    assert state.power_state.get("突破契机") == 1
    assert state.power_state.get("交手经验") == 1
    assert state.social_state.get("人心之疑") == 1
    assert len(state.transition_log) == 3
    log = state.transition_log[0]
    assert log["turn"] == 7
    assert log["scope_id"] == "capital"


def test_apply_growth_transition_caps_counting_dims():
    state = default_growth_state("a")
    for _ in range(7):
        state, _ = apply_growth_transition(state, {"summary": "获得灵石"})
    assert state.resource_state.get("增益") == 5  # 计数维度软上限 _MAX_BUMP=5
    state, _ = apply_growth_transition(state, {"summary": "又被夺走亏空耗尽"})
    assert state.resource_state.get("增益") == 5  # 损耗维度与增益独立


def test_apply_growth_transition_no_fire_keeps_state_intact():
    state = default_growth_state("a")
    _, fired = apply_growth_transition(state, {"summary": "交代了一些背景"})
    assert fired == []
    assert state.power_state == {}
    assert state.transition_log == []


def test_apply_growth_transition_for_turn_writes_state_and_emotions(tmp_path):
    storage = MemoryStorage()
    data_root = tmp_path / "novel"
    results, guard_audit = apply_growth_transition_for_turn(
        storage,
        data_root,
        scope_id="capital",
        turn_index=3,
        present_character_ids=["su_wan"],
        event_entry={"summary": "苏晚寻得秘笈，又遭围困中毒"},
    )
    assert set(results) == {"su_wan"}
    assert "resource_gain" in results["su_wan"]
    assert "horror_trap" in results["su_wan"]
    # 在场且有迁移者落盘 growth_state.yaml
    path = growth_state_yaml_path(data_root, "su_wan")
    assert path.is_file()
    loaded = load_growth_state("su_wan", data_root)
    assert loaded.resource_state.get("增益") == 1
    assert loaded.resource_state.get("损耗") == 1
    assert len(loaded.transition_log) == 2  # 命中 resource_gain + horror_trap 两条规则
    # 不在场角色（未列入 present）不参与迁移，不落盘
    assert "lin_yuan" not in results
    assert not growth_state_yaml_path(data_root, "lin_yuan").is_file()
    # mind 变化写入 emotions 槽位
    assert storage.get_emotions("su_wan")
    assert storage.get_emotions("lin_yuan") == []


# --- 阶段 2：GrowthGuard 强约束（§6） ---


def _bundle(summary, turn=1, scope_id="capital"):
    return {"summary": summary, "turn_index": turn, "scope_id": scope_id}


def test_guard_none_equals_unguarded():
    state = default_growth_state("a")
    s1, f1 = apply_growth_transition(
        default_growth_state("a"), _bundle("获得至宝，也付出巨大损耗"))
    s2, f2, dec = apply_growth_transition_guarded(
        default_growth_state("a"), _bundle("获得至宝，也付出巨大损耗"), None)
    assert f1 == f2
    assert dec == []
    assert s1.to_dict() == s2.to_dict()


def test_guard_skips_no_cost_benefit():
    state = default_growth_state("a")
    _, fired, decisions = apply_growth_transition_guarded(
        state, _bundle("苏晚获得至宝与秘笈"), GrowthGuard())
    assert "resource_gain" in fired          # 规则确实命中
    # 但无代价收益被 guard 跳过一次写回
    skip = [d for d in decisions if d["action"] == "skipped"]
    assert any(d["rule"] == "resource_gain" and "代价" in d["reason"] for d in skip)
    assert state.resource_state.get("增益") is None  # 收益未落库
    # 告警条目已记入 transition_log，可审计
    assert any(e.get("guard") == "resource_gain" for e in state.transition_log)


def test_guard_allows_benefit_when_event_has_cost():
    state = default_growth_state("a")
    _, fired, decisions = apply_growth_transition_guarded(
        state, _bundle("获得至宝，却遭围困中毒损耗身体"), GrowthGuard())
    assert "resource_gain" in fired
    assert "horror_trap" in fired            # 内带损耗，抵消收益
    assert state.resource_state.get("增益") == 1
    assert state.resource_state.get("损耗") == 1
    skipped = [d for d in decisions if d["action"] != "allowed"]
    assert skipped == []                     # 无被拒规则


def test_guard_allows_benefit_when_prior_cost_exists():
    state = default_growth_state("a")
    state.resource_state = {"损耗": 1}        # 已有积欠代价
    _, fired, _ = apply_growth_transition_guarded(
        state, _bundle("苏晚获得灵石"), GrowthGuard())
    assert state.resource_state.get("增益") == 1


def test_guard_goal_cooldown_skips_rapid_goal_change():
    state = default_growth_state("a")
    state.transition_log = [{"rule": "goal_affirmed", "turn": 3, "scope_id": "capital",
                             "reason": "旧", "deltas": [1, 1]}]
    state.goal_state = {"里程碑": 1}
    # turn 5 距上次目标变动(3) 差 2 回合，在默认冷却窗口 3 内 → 跳过
    _, fired, decisions = apply_growth_transition_guarded(
        state, _bundle("再次顿悟起誓", turn=5), GrowthGuard(goal_cooldown_turns=3))
    assert "goal_affirmed" in fired
    skip = [d for d in decisions if d["action"] == "skipped"]
    assert any(d["rule"] == "goal_affirmed" and "冷却" in d["reason"] for d in skip)
    assert state.goal_state.get("里程碑") == 1  # 未再增长


def test_guard_no_goal_cooldown_when_interval_suffices():
    state = default_growth_state("a")
    state.transition_log = [{"rule": "goal_affirmed", "turn": 1, "scope_id": "capital",
                             "reason": "旧", "deltas": [1, 1]}]
    state.goal_state = {"里程碑": 1}
    _, fired, decisions = apply_growth_transition_guarded(
        state, _bundle("再次顿悟起誓", turn=10),
        GrowthGuard(goal_cooldown_turns=3, balance_required=False))  # 隔离测试只检冷却
    assert state.goal_state.get("里程碑") == 2  # 超过冷却窗口 → 允许
    assert all(d["action"] == "allowed" for d in decisions)


def test_guard_skips_positive_relation_on_same_turn_flip():
    state = default_growth_state("a")
    _, fired, decisions = apply_growth_transition_guarded(
        state, _bundle("与旧友剑拔弩张反目，却于危难中相救"), GrowthGuard())
    assert {"conflict_showdown", "rescue_debt"} <= set(fired)
    skip = [d for d in decisions if d["action"] == "skipped"]
    assert any(d["rule"] == "rescue_debt" for d in skip)   # 正向关系被跳过（同回合立场反转）
    assert state.social_state.get("受恩于人") is None
    assert state.social_state.get("敌对") == 1


def test_guard_clamps_per_turn_delta_cap_within_bound():
    guard = GrowthGuard(per_turn_delta_cap=2)
    state = default_growth_state("a")
    state.resource_state = {"损耗": 2}
    # 单规则 +1 净增，在 cap=2 之内 → 不钳制
    _, fired, decisions = apply_growth_transition_guarded(
        state, _bundle("损失惨重，耗尽资源"), guard)
    assert state.resource_state.get("损耗") == 3
    clamps = [d for d in decisions if d["action"] == "clamp"]
    assert clamps == []


def test_guard_records_clamp_when_crossing_cap():
    guard = GrowthGuard(per_turn_delta_cap=1)
    state = default_growth_state("a")
    state.resource_state = {"损耗": 0}
    # 同一事件命中 horror_trap（中毒）+ resource_loss（耗尽），都累加 resource.损耗 → 净增 2 > cap=1 → 钳制
    _, fired, decisions = apply_growth_transition_guarded(
        state, _bundle("中毒被困，又被彻底耗尽亏空"), guard)
    assert {"horror_trap", "resource_loss"} <= set(fired)
    assert state.resource_state.get("损耗") <= 0 + guard.per_turn_delta_cap  # 被钳制不越界
    clamps = [d for d in decisions if d["action"] == "clamp"]
    assert clamps and any("损耗" in k for d in clamps for k in d.get("keys", []))