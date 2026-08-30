"""
三层记忆（L1/L2/L3）落库 + 写入校验 + 检索消费——单元测试（确定性、无 LLM）。

覆盖：
- classify_memory_layer / interpretation_subject / strategy_expires_turn / build_layer_entry（memory_layers.py）
- MemoryStorage L2 upsert 原地更新 / L3 过期过滤 / get_event_count（storage.py）
- Orchestrator.apply_memory_write 开关门：默认关→仅 L1；开启→L2/L3 已入库（含 expires_turn）
- retrieve_character_memory include_layers 两态（retrieval/memory.py）
"""
import pytest

from src.agents.character.agent import CharacterTurnOutput
from src.orchestrator import Orchestrator
from src.runtime.memory_layers import (
    build_layer_entry,
    classify_memory_layer,
    interpretation_subject,
    strategy_expires_turn,
)
from src.runtime.storage import MemoryStorage
from src.retrieval.memory import retrieve_character_memory


# ---- memory_layers.py：确定性分类 ----

@pytest.mark.parametrize("text,layer", [
    ("我下一步计划在清明动手", "L3"),
    ("我打算先囤积粮草再发兵", "L3"),
    ("提防西域商队另有图谋", "L3"),
    ("我觉得他不怀好意", "L2"),
    ("我意识到那份密信被调包了", "L2"),
    ("他对我有明显的敌意", "L2"),
    ("冬夜她披着鹤氅走进庭院", "L1"),
    ("", "L1"),
])
def test_classify_memory_layer(text, layer):
    assert classify_memory_layer(text) == layer


def test_l3_keyword_takes_precedence_over_l2():
    # L3 计划词优先于 L2 解释词
    assert classify_memory_layer("我认为该把提防他作为下一步计划") == "L3"


def test_interpretation_subject():
    assert interpretation_subject("我觉得李统领在说谎") == "李统领在说谎"
    assert interpretation_subject("我判断朝中必有内应", max_len=6) == "朝中必有内应"[:6]
    assert interpretation_subject("") == "general"
    assert interpretation_subject("我") == "general"


def test_strategy_expires_turn_and_build_layer_entry():
    assert strategy_expires_turn(10, ttl=5) == 15
    assert strategy_expires_turn(0, ttl=5) == 5
    assert strategy_expires_turn(None, ttl=2) == 2  # 缺省按 0（turn_index or 0）+ ttl
    # build_layer_entry L3 带 expires_turn / plan
    e3 = build_layer_entry("我打算今夜偷袭", "L3", scope_id="main", turn_index=7, time="夜", place="岭", ttl=4)
    assert e3["layer"] == "L3" and e3["expires_turn"] == 11 and e3["plan"] == "我打算今夜偷袭"
    assert e3["scope_id"] == "main" and e3["impact_level"] == "med"
    # L2 带 subject / statement
    e2 = build_layer_entry("我觉得他值得信任", "L2", scope_id="main", turn_index=7)
    assert e2["layer"] == "L2" and e2["subject"] and e2["statement"] == "我觉得他值得信任"


# ---- storage.py：upsert / 过期过滤 ----

def test_upsert_interpretation_updates_in_place():
    s = MemoryStorage()
    e1 = build_layer_entry("我怀疑这是圈套", "L2", turn_index=1)
    e2 = build_layer_entry("我确认这是圈套，他早有预谋", "L2", turn_index=3)
    # 强制同一条 subject，验证 upsert 原地更新（解释随认知更新、不叠加历史）
    e1["subject"] = e2["subject"] = "圈套疑云"
    s.upsert_interpretation("a", e1)
    s.upsert_interpretation("a", e2)
    got = s.get_interpretations("a")
    assert len(got) == 1, "同 subject 应原地替换、不叠加历史"
    assert got[0]["statement"].startswith("我确认这是圈套")
    assert got[0]["turn_index"] == 3


def test_upsert_interpretation_diff_subject_appends():
    s = MemoryStorage()
    s.upsert_interpretation("a", build_layer_entry("我觉得乙可信", "L2", turn_index=1))
    s.upsert_interpretation("a", build_layer_entry("我认为朝中有人", "L2", turn_index=2))
    assert len(s.get_interpretations("a")) == 2


def test_get_active_strategies_ttl_expiry():
    s = MemoryStorage()
    s.append_strategy("a", build_layer_entry("我准备出发", "L3", turn_index=1, ttl=2))   # expires 3
    s.append_strategy("a", build_layer_entry("我打算死守", "L3", turn_index=10, ttl=2))  # expires 12
    assert len(s.get_active_strategies("a", current_turn=2)) == 2  # 都未过期
    assert len(s.get_active_strategies("a", current_turn=3)) == 1  # 第 1 条已过期
    assert len(s.get_active_strategies("a")) == 2                  # 未传回合不过滤


def test_get_event_count():
    s = MemoryStorage()
    assert s.get_event_count("main") == 0
    s.append_events("main", [{"summary": "x"}])
    assert s.get_event_count("main") == 1


# ---- apply_memory_write：开关门 ----

def _make_orch(with_layers: bool) -> Orchestrator:
    runtime = {"agents": {"characters": {"enabled_ids": ["a"], "react_chain": False, "memory_layers": with_layers}}}
    return Orchestrator(
        storage=MemoryStorage(),
        character_agents={},
        scope_agents={},
        world_config={},
        runtime_config=runtime,
        characters_config={},
    )


def _turn_result(summaries: dict[str, str]) -> tuple:
    from src.agents.world import ScopeTurnOutput
    outputs = {}
    for cid, text in summaries.items():
        outputs[cid] = CharacterTurnOutput(
            inner_monologue="", dialogue_action=text, reaction="", metadata={"character_id": cid}
        )
    scope = ScopeTurnOutput(constraints=[], event_summary="scope", state_delta={})
    from src.orchestrator import TurnResult
    return TurnResult(scope_output=scope, character_outputs=outputs)


def test_apply_memory_write_off_only_l1():
    orch = _make_orch(with_layers=False)
    result = _turn_result({"a": "我决定先查那封密信再动手"})
    # 先落 scope 事件以便 turn_index 基准（即便 off 也会走 get_event_count 路径）
    orch.storage.append_events("main", [{"summary": "sc"}])
    orch.apply_memory_write(result, "main", "晨", "府中")
    events = orch.storage.get_events("a")
    assert len(events) == 1
    assert events[0]["layer"] == "L1", "默认关时只写 L1"
    assert orch.storage.get_interpretations("a") == []
    assert orch.storage.get_active_strategies("a") == []


def test_apply_memory_write_on_writes_l2_and_l3():
    orch = _make_orch(with_layers=True)
    result = _turn_result({
        "a": "我觉得他不可信",               # L2 解释
        "b": "我打算明日劫营",               # L3 策略
        "c": "她送来一壶温酒",               # L1 事实
    })
    orch.storage.append_events("main", [{"summary": "sc"}])  # turn_index 基准 +1
    orch.apply_memory_write(result, "main", "晨", "府中")
    # L1 三条仍在
    assert len(orch.storage.get_events("a")) == 1
    # L2 已入库（upsert 语义）
    interp = orch.storage.get_interpretations("a")
    assert len(interp) == 1 and interp[0]["layer"] == "L2"
    # L3 已入库且带 expires_turn（turn_index=1, ttl=5 → expires 6）
    strat = orch.storage.get_active_strategies("b")
    assert len(strat) == 1
    assert strat[0]["layer"] == "L3"
    assert strat[0]["expires_turn"] == 1 + 5
    # L1 事实不进 L2/L3
    assert orch.storage.get_interpretations("c") == []
    assert orch.storage.get_active_strategies("c") == []


# ---- retrieve_character_memory：include_layers 两态 ----

def test_retrieve_character_memory_include_layers_off():
    s = MemoryStorage()
    s.append_event_refinement("a", {"summary": "冬夜入府", "layer": "L1"})
    s.upsert_interpretation("a", build_layer_entry("我觉得他可疑", "L2"))
    s.append_strategy("a", build_layer_entry("我打算先静观", "L3"))
    out = retrieve_character_memory(s, "a")
    assert "事件提炼" in out
    assert "解释（L2）" not in out
    assert "短期计划（L3）" not in out


def test_retrieve_character_memory_include_layers_on():
    s = MemoryStorage()
    s.append_event_refinement("a", {"summary": "冬夜入府", "layer": "L1"})
    s.upsert_interpretation("a", build_layer_entry("我觉得他可疑", "L2"))
    s.append_strategy("a", build_layer_entry("我打算先静观", "L3"))
    out = retrieve_character_memory(s, "a", include_layers=True)
    assert "解释（L2）" in out
    assert "短期计划（L3）" in out
    assert "可疑" in out and "静观" in out