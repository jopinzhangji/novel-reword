"""G4 人物情况（characters.py）：成长五维 / 信息视野 / L1 记忆 / 屏外线 / 运行期态标注。"""
from src.runtime.memory_layers import classify_memory_layer
from src.workbench import characters
from tests.unit.workbench_support import (
    make_project,
    write_char_event,
    write_growth,
    write_off_screen,
    write_scope_event,
)


def test_character_detail_growth_and_threads(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_growth(
        roots["alpha"], "苏A",
        {"power_state": {"突破契机": 1}, "mind_state": {"应激": 2}},
        [{"rule": "突破", "turn": 1, "note": "交手"}],
    )
    write_off_screen(roots["alpha"], "苏A", [{"summary": "暗中查叛徒", "consumed": False}])
    d = characters.character_detail(roots["alpha"], "苏A")
    assert d["id"] == "苏A"
    assert d["growth"]["power_state"] == {"突破契机": 1}
    assert d["growth"]["transition_log"] == [{"rule": "突破", "turn": 1, "note": "交手"}]
    assert isinstance(d["off_screen_threads"], list)
    assert d["off_screen_threads"][0]["consumed"] is False
    assert d["runtime_only_layers"] is True  # L2/L3 未落盘


def test_character_view_known_unknown(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_scope_event(roots["alpha"], "sc1", 1, ["苏A", "李B"], "并肩作战")
    write_scope_event(roots["alpha"], "sc1", 2, ["李B"], "苏A不在场密谋")  # 苏A 未知
    v = characters.character_view(roots["alpha"], "苏A")
    assert v["total_events"] == 2
    assert v["known"] == 1 and v["unknown"] == 1
    assert len(v["per_scope"]) == 1 and v["per_scope"][0]["scope_id"] == "sc1"


def test_memories_l1_layer(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_char_event(roots["alpha"], "苏A", 1, "她明白了叛徒是谁")
    mems = characters.character_events_on_disk(roots["alpha"], "苏A")
    assert len(mems) == 1
    assert mems[0]["turn_file"] == "turn_0001.md"
    assert classify_memory_layer(mems[0]["summary"]) in ("L1", "L2", "L3")
    assert mems[0]["layer"] in ("L1", "L2", "L3")


def test_characters_index_empty_when_no_roster(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    (roots["alpha"] / "config" / "characters.yaml").unlink()
    assert characters.characters_index(roots["alpha"]) == []