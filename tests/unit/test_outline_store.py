"""大纲加载与轻量校验。"""
from pathlib import Path

import yaml

from src.runtime.outline_store import (
    BeatContext,
    build_outline_prompt_snippet,
    extract_chapter_outline_from_setting,
    load_outline_snapshot,
    materialize_outline_from_setting_research,
    outline_dict_from_setting_chapter_outline,
    outline_injection_options,
    outline_yaml_path,
    progress_yaml_path,
    resolve_current_beat,
    validate_outline,
    validate_progress,
)


def test_paths(tmp_path):
    root = tmp_path / "novel"
    assert outline_yaml_path(root) == root / "book" / "outline" / "outline.yaml"
    assert progress_yaml_path(root) == root / "book" / "outline" / "progress.yaml"


def test_load_outline_snapshot_missing_returns_none(tmp_path):
    assert load_outline_snapshot(tmp_path / "novel") is None


def test_load_outline_snapshot_loads_and_warns(tmp_path):
    root = tmp_path / "novel"
    od = root / "book" / "outline"
    od.mkdir(parents=True)
    outline = {
        "version": 1,
        "chapters": [
            {
                "id": "c1",
                "title": "第一章",
                "beats": [{"id": "b1", "intent": "试", "status": "planned"}],
            }
        ],
    }
    (od / "outline.yaml").write_text(yaml.safe_dump(outline, allow_unicode=True), encoding="utf-8")
    prog = {"version": 1, "chapter_id": "c1", "beat_id": "b1", "turns_in_beat": 1}
    (od / "progress.yaml").write_text(yaml.safe_dump(prog, allow_unicode=True), encoding="utf-8")

    snap = load_outline_snapshot(root)
    assert snap is not None
    assert snap.outline["chapters"][0]["id"] == "c1"
    assert snap.progress["beat_id"] == "b1"
    line = snap.log_line()
    assert "大纲文件" in line
    assert "c1" in line and "b1" in line


def test_validate_outline_empty_ok():
    w = validate_outline({"version": 1})
    assert any("未定义" in x for x in w)


def test_validate_progress_bad_turns():
    w = validate_progress({"chapter_id": "a", "turns_in_beat": "x"})
    assert any("turns_in_beat" in x for x in w)


def test_resolve_current_beat_with_progress(tmp_path):
    root = tmp_path / "novel"
    od = root / "book" / "outline"
    od.mkdir(parents=True)
    outline = {
        "version": 1,
        "chapters": [
            {
                "id": "c1",
                "title": "第一章",
                "dramatic_question": "能活吗？",
                "beats": [
                    {"id": "b1", "intent": "建立氛围", "status": "active", "tags": ["a"]},
                    {"id": "b2", "intent": "冲突爆发", "status": "planned"},
                ],
            }
        ],
    }
    (od / "outline.yaml").write_text(yaml.safe_dump(outline, allow_unicode=True), encoding="utf-8")
    prog = {"version": 1, "chapter_id": "c1", "beat_id": "b1", "turns_in_beat": 2}
    (od / "progress.yaml").write_text(yaml.safe_dump(prog, allow_unicode=True), encoding="utf-8")
    snap = load_outline_snapshot(root)
    assert snap is not None
    bc = resolve_current_beat(snap, soft_max_turns=3)
    assert isinstance(bc, BeatContext)
    assert bc.chapter_id == "c1"
    assert bc.beat_id == "b1"
    assert bc.beat_intent == "建立氛围"
    assert bc.turns_in_beat == 2
    assert "冲突爆发" in bc.next_beat_hint


def test_build_outline_prompt_snippet_disabled(tmp_path):
    root = tmp_path / "novel"
    od = root / "book" / "outline"
    od.mkdir(parents=True)
    outline = {"version": 1, "chapters": [{"id": "c1", "title": "T", "beats": [{"id": "b1", "intent": "x"}]}]}
    (od / "outline.yaml").write_text(yaml.safe_dump(outline, allow_unicode=True), encoding="utf-8")
    snap = load_outline_snapshot(root)
    rc = {"runtime": {"outline": {"enabled": False}}, "agents": {"characters": {"enabled_ids": ["p"]}}}
    assert build_outline_prompt_snippet(rc, snap, {"characters": [{"id": "p", "name": "P", "is_protagonist": True}]}) == ""


def test_outline_injection_options_defaults():
    o = outline_injection_options({"runtime": {}})
    assert o["enabled"] is True
    assert o["soft_max_turns"] == 3


def test_build_turn_plan_prompt_contains_outline():
    from src.context import TurnContext
    from src.author_loop.turn_planning import build_turn_plan_prompt

    ctx = TurnContext(
        scope_id="main",
        time="t",
        place="p",
        present_character_ids=("protagonist",),
        last_turn_summary="",
        shared_story_snippet="",
        secondary_characters_snippet="",
    )
    snip = "【全书大纲·当前节拍】\n- 本节拍意图：测试"
    p = build_turn_plan_prompt(ctx, {"name": "范围", "description": "d"}, "事件", outline_snippet=snip)
    assert "全书大纲" in p
    assert "测试" in p


def test_outline_dict_from_setting_chapter_outline():
    block = {
        "name": "卷一",
        "chapters": [
            {"chapter_number": 1, "title": "入山", "summary": "落地"},
            {"chapter_number": 2, "title": "认路", "summary": "熟识"},
        ],
    }
    out = outline_dict_from_setting_chapter_outline(block)
    assert out["version"] == 1
    assert len(out["chapters"]) == 2
    assert out["chapters"][0]["id"] == "ch01"
    assert out["chapters"][0]["beats"][0]["intent"] == "落地"
    assert out["chapters"][0]["beats"][0]["id"] == "ch01_b1"
    assert out["chapters"][1]["id"] == "ch02"


def test_materialize_outline_from_setting_research_writes_and_loads(tmp_path):
    root = tmp_path / "novel"
    setting = {
        "章节大纲": {
            "chapters": [{"chapter_number": 1, "title": "开场", "summary": "钩子"}],
        }
    }
    ok, msg = materialize_outline_from_setting_research(root, setting)
    assert ok
    assert "outline.yaml" in msg
    snap = load_outline_snapshot(root)
    assert snap is not None
    bc = resolve_current_beat(snap, soft_max_turns=3)
    assert bc is not None
    assert bc.beat_intent == "钩子"


def test_materialize_skips_when_outline_exists(tmp_path):
    root = tmp_path / "novel"
    od = root / "book" / "outline"
    od.mkdir(parents=True)
    (od / "outline.yaml").write_text(yaml.safe_dump({"version": 1, "chapters": []}), encoding="utf-8")
    setting = {"章节大纲": {"chapters": [{"chapter_number": 1, "title": "A", "summary": "B"}]}}
    ok, msg = materialize_outline_from_setting_research(root, setting, overwrite=False)
    assert not ok
    assert "未覆盖" in msg or "已存在" in msg


def test_extract_chapter_outline_none_when_empty():
    assert extract_chapter_outline_from_setting({}) is None
    assert extract_chapter_outline_from_setting({"章节大纲": {"chapters": []}}) is None
