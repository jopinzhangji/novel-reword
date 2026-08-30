"""G1 屏外线 / 并列主线：数据落盘 + 屏外演进（SDD D10，phase G1a）。"""
from pathlib import Path

from src.runtime.character_growth import (
    GrowthGuard,
    apply_off_screen_transitions,
    load_growth_state,
)
from src.runtime.file_sync import (
    append_off_screen_thread,
    load_off_screen_threads,
    off_screen_threads_yaml_path,
)
from src.runtime.memory_layers import (
    THREAD_OFF_SCREEN,
    THREAD_PARALLEL,
    build_layer_entry,
)
from src.runtime.storage import MemoryStorage


def _tmp_root(tmp_path) -> Path:
    return tmp_path / "novel"


# --- build_layer_entry：thread 字段（向后兼容） ---


def test_build_layer_entry_default_has_no_thread():
    e = build_layer_entry("我有一个计划", "L3", scope_id="main")
    assert "thread" not in e
    assert e["layer"] == "L3"


def test_build_layer_entry_thread_field_present():
    e = build_layer_entry("夜色渐深，我决意独自去查那地窖", "L2", thread=THREAD_OFF_SCREEN)
    assert e["thread"] == THREAD_OFF_SCREEN
    assert e["subject"]
    # thread 作为统一标签写入，与 layer/scope_id 并存
    assert e["layer"] == "L2"


# --- storage：屏外记忆桶（与主书事件分离） ---


def test_storage_append_get_recent_off_screen():
    st = MemoryStorage()
    st.append_off_screen_refinement("li", {"thread": THREAD_OFF_SCREEN, "summary": "独访地窖"})
    st.append_off_screen_refinement("li", {"thread": THREAD_PARALLEL, "summary": "修炼功法"})
    st.append_off_screen_refinement("li", {"thread": THREAD_OFF_SCREEN, "summary": "夜谈"})
    assert len(st.get_recent_off_screen("li", limit=100)) == 3
    off = st.get_recent_off_screen("li", thread=THREAD_OFF_SCREEN)
    assert [e["summary"] for e in off] == ["独访地窖", "夜谈"]
    # 与主书事件（在场事实卡）隔离
    st.append_event_refinement("li", {"summary": "在主书场中的事件"})
    assert all(e.get("thread") for e in st.get_recent_off_screen("li", limit=100))


# --- 屏外演进：数据落盘 round-trip + 成长迁移 ---


def test_append_load_off_screen_thread_roundtrip(tmp_path):
    root = _tmp_root(tmp_path)
    entry = {
        "thread": THREAD_OFF_SCREEN,
        "layer": "L1",
        "summary": "受柳家所邀夜访地窖，留意到一具被封存的棺椁。",
        "tags": ["romance", "resource_gain"],
        "turn_index": 37,
    }
    path = append_off_screen_thread(root, "li", entry)
    assert path == off_screen_threads_yaml_path(root, "li")
    assert path.is_file()
    back = load_off_screen_threads(root, "li")
    assert len(back) == 1 and back[0]["summary"] == entry["summary"]
    assert back[0]["thread"] == THREAD_OFF_SCREEN


def test_load_off_screen_threads_missing_returns_empty(tmp_path):
    assert load_off_screen_threads(_tmp_root(tmp_path), "nobody") == []


def test_apply_off_screen_transitions_grows_non_present_character(tmp_path):
    """G1a 验收：非在场角色可经屏外条目演进；成长落盘；主书事件簿不受影响。"""
    root = _tmp_root(tmp_path)
    st = MemoryStorage()
    # 屏外遭遇「重伤濒死 + 获救」→ 命中 near_death + rescue_debt
    entries = [
        {"thread": THREAD_OFF_SCREEN, "summary": "在巡查中遭埋伏，重伤濒死", "turn_index": 40},
        {"thread": THREAD_OFF_SCREEN, "summary": "被一名蒙面人仗义出手救走，欠下人情", "turn_index": 41},
    ]
    fired, audit = apply_off_screen_transitions(st, root, character_id="li", entries=entries, guard=GrowthGuard())
    assert "near_death" in fired
    assert "rescue_debt" in fired
    # 成长落盘且可读回
    state = load_growth_state("li", root)
    assert state.power_state.get("突破契机") == 1
    assert state.social_state.get("受恩于人") == 1
    # 主书事件簿不受影响（屏外演进不写 scope 事件）
    assert st.get_recent_events("main", k=100) == []
    # mind 变化写入 emotions 槽位
    assert st.get_emotions("li")


def test_apply_off_screen_transitions_guard_blocks_no_cost_benefit(tmp_path):
    """单个『获得至宝』若无代价/积欠 → 被 GrowthGuard 跳过并记告警（不假膨胀）。"""
    root = _tmp_root(tmp_path)
    st = MemoryStorage()
    entries = [{"thread": THREAD_OFF_SCREEN, "summary": "在一个山洞里得到至宝", "turn_index": 50}]
    fired, audit = apply_off_screen_transitions(st, root, character_id="wang", entries=entries, guard=GrowthGuard())
    # fired 报告命中的规则（与 apply_growth_transition_for_turn 一致的"命中上报"语义）：
    # 真正校验在 audit + 状态上——guard 已跳过该无代价收益，故状态不增长。
    assert "resource_gain" in fired
    assert any("无代价收益" in str(d.get("guard_reason") or d.get("reason") or "") for d in audit)
    state = load_growth_state("wang", root)
    assert state.resource_state.get("增益", 0) == 0


def test_apply_off_screen_transitions_cost_then_benefit_allowed(tmp_path):
    """批内先损耗后可收益：资源损失累积为积欠，后续『获得』获 GrowthGuard 放行（体现跨条目平衡）。"""
    root = _tmp_root(tmp_path)
    st = MemoryStorage()
    entries = [
        {"thread": THREAD_OFF_SCREEN, "summary": "行商失败，损失惨重", "turn_index": 60},
        {"thread": THREAD_OFF_SCREEN, "summary": "此后寻得一株灵草，得到回报", "turn_index": 61},
    ]
    fired, _ = apply_off_screen_transitions(st, root, character_id="zhao", entries=entries, guard=GrowthGuard())
    assert "resource_gain" in fired  # 有既有代价积欠（resource_state.损耗）→ 放行
    state = load_growth_state("zhao", root)
    assert state.resource_state.get("增益") == 1
    assert state.resource_state.get("损耗") == 1


def test_apply_off_screen_transitions_no_match_no_change(tmp_path):
    root = _tmp_root(tmp_path)
    st = MemoryStorage()
    entries = [{"thread": THREAD_OFF_SCREEN, "summary": "在驿站歇息，与掌柜闲谈几句", "turn_index": 70}]
    fired, audit = apply_off_screen_transitions(st, root, character_id="liu", entries=entries)
    assert fired == [] and audit == []
    assert load_growth_state("liu", root).power_state == {}