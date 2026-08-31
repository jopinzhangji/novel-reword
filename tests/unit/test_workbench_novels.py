"""G4 作品索引 / 进度总览（novels.py）：多小说卡片 + 单书摘要 + 索引缺失回退。"""
from pathlib import Path

from src.workbench import novels
from tests.unit.workbench_support import (
    make_project,
    write_graph,
    write_index,
    write_outline,
)


def test_index_novels_two_slugs_in_order(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha", "beta"))
    write_index(proj, ("alpha", "beta"))
    write_outline(roots["alpha"])
    write_graph(roots["alpha"])
    items = novels.index_novels(proj)
    assert [i["slug"] for i in items] == ["alpha", "beta"]
    a = items[0]
    assert a["title"] and a["status"] == "draft"
    assert a["character_count"] == 3
    assert a["edge_count"] == 3
    assert a["outline_pointer"]["had_any_beat"] is True
    assert a["outline_pointer"]["turns_in_beat"] == 2
    assert a["outline_pointer"]["chapter_id"] == "ch1"
    assert a["outline_pointer"]["beat_id"] == "b1"


def test_summary_has_growth_and_event_counts(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_outline(roots["alpha"])
    from tests.unit.workbench_support import write_growth, write_scope_event

    write_growth(roots["alpha"], "苏A", {"power_state": {"突破契机": 1}}, [{"rule": "突破", "turn": 1}])
    write_scope_event(roots["alpha"], "sc1", 1, ["苏A"], "交手")
    s = novels.novel_summary(roots["alpha"])
    assert s["growth"]["characters_with_growth"] == 1
    assert s["growth"]["transition_entries"] == 1
    assert s["scope_event_count"] == 1


def test_index_fallback_without_index_yaml(tmp_path):
    proj, roots = make_project(tmp_path, ("solo",))
    items = novels.index_novels(proj)
    assert [i["slug"] for i in items] == ["solo"]  # 无 index.yaml → glob 回退


def test_summary_no_outline(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    s = novels.novel_summary(roots["alpha"])
    assert s["outline_pointer"] == {}