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


# --- GG-W #6：小说正文 read port（story_events）---
def _write_story_turns(root, events_dirs=("main",)):
    """写若干含「正文 body」的 scope 事件文件。"""
    for scope in events_dirs:
        d = root / "book" / "events" / scope / "events"
        d.mkdir(parents=True, exist_ok=True)
        (d / "turn_0001.md").write_text(
            "# 回合 1\n\nscope_id: 'main'\ntime: '夜'\nplace: '城门'\n\n## 摘要\n\n第一回摘要\n\n## 正文\n\n第一回正文就此展开……\n",
            encoding="utf-8",
        )
        (d / "turn_0002.md").write_text(
            "# 回合 2\n\nscope_id: 'main'\ntime: '晨'\n\n## 摘要\n\n第二回摘要\n\n## 正文\n\n第二回正文更长一些、这里就是正文章节。\n",
            encoding="utf-8",
        )


def test_story_events_order_body_and_pointer(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    root = roots["alpha"]
    write_outline(root)  # ch1/b1 → outline_pointer 有值
    _write_story_turns(root)
    r = novels.story_events(root, scope_id="main")
    assert r["count"] == 2
    assert r["events"][0]["turn"] == 2 and "第二回正文更长" in r["events"][0]["body"]  # 最新在前 + body
    assert r["events"][1]["turn"] == 1 and "第一回正文" in r["events"][1]["body"]
    assert r["events"][0]["time"] == "晨" and r["events"][0]["place"] == ""
    assert r["outline_pointer"]["chapter_id"] == "ch1"


def test_story_events_limit(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    _write_story_turns(roots["alpha"])
    r = novels.story_events(roots["alpha"], limit=1)
    assert len(r["events"]) == 1 and r["events"][0]["turn"] == 2
    assert r["count"] == 2  # count 反映总量，events 受 limit 截


def test_story_events_empty_no_dir(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    r = novels.story_events(roots["alpha"])
    assert r["events"] == [] and r["outline_pointer"] == {}