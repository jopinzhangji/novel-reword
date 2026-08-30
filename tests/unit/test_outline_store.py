"""大纲加载与轻量校验。"""
from pathlib import Path

import yaml

from src.runtime.outline_store import (
    BeatContext,
    advance_to_next_beat,
    build_outline_prompt_snippet,
    bump_turns_in_beat,
    extract_chapter_outline_from_setting,
    load_outline_snapshot,
    materialize_outline_from_setting_research,
    normalize_progress,
    outline_dict_from_setting_chapter_outline,
    outline_injection_options,
    outline_yaml_path,
    progress_yaml_path,
    resolve_current_beat,
    resolve_outline_context,
    save_progress,
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


# --- MVP-2：progress.yaml 写回 + 节拍推进 ---

def _outline_dict_two_chapters():
    return {
        "version": 1,
        "chapters": [
            {
                "id": "c1",
                "title": "第一章",
                "beats": [
                    {"id": "c1_b1", "intent": "氛围", "status": "active"},
                    {"id": "c1_b2", "intent": "冲突", "status": "planned"},
                ],
            },
            {
                "id": "c2",
                "title": "第二章",
                "beats": [
                    {"id": "c2_b1", "intent": "转折", "status": "planned"},
                ],
            },
        ],
    }


def _snap(tmp_path, outline=None, progress=None):
    root = tmp_path / "novel"
    od = root / "book" / "outline"
    od.mkdir(parents=True)
    (od / "outline.yaml").write_text(yaml.safe_dump(outline or _outline_dict_two_chapters(), allow_unicode=True), encoding="utf-8")
    if progress is not None:
        (od / "progress.yaml").write_text(yaml.safe_dump(progress, allow_unicode=True), encoding="utf-8")
    snap = load_outline_snapshot(root)
    assert snap is not None
    return snap


def test_normalize_progress_defaults():
    assert normalize_progress({})["version"] == 1
    assert normalize_progress({"version": 3})["version"] == 3
    assert normalize_progress(None)["version"] == 1


def test_bump_turns_in_beat_increments_and_preserves():
    out = bump_turns_in_beat({"chapter_id": "c1", "beat_id": "c1_b1", "turns_in_beat": 2})
    assert out["turns_in_beat"] == 3
    assert out["chapter_id"] == "c1" and out["beat_id"] == "c1_b1"
    assert out["version"] == 1
    # 非 turns 自定义键保留
    out2 = bump_turns_in_beat({"chapter_id": "c9", "extra": "x"})
    assert out2["turns_in_beat"] == 1
    assert out2["extra"] == "x"


def test_advance_to_next_beat_same_chapter(tmp_path):
    snap = _snap(tmp_path, progress={"version": 1, "chapter_id": "c1", "beat_id": "c1_b1"})
    nxt = advance_to_next_beat(snap, {"chapter_id": "c1", "beat_id": "c1_b1", "turns_in_beat": 0})
    assert nxt is not None
    assert nxt["chapter_id"] == "c1" and nxt["beat_id"] == "c1_b2"
    assert nxt["turns_in_beat"] == 0


def test_advance_to_next_beat_cross_chapter(tmp_path):
    snap = _snap(tmp_path, progress={"version": 1, "chapter_id": "c1", "beat_id": "c1_b2"})
    nxt = advance_to_next_beat(snap, {"chapter_id": "c1", "beat_id": "c1_b2"})
    assert nxt is not None
    assert nxt["chapter_id"] == "c2" and nxt["beat_id"] == "c2_b1"


def test_advance_to_next_beat_last_returns_none(tmp_path):
    snap = _snap(tmp_path, progress={"version": 1, "chapter_id": "c2", "beat_id": "c2_b1"})
    assert advance_to_next_beat(snap, {"chapter_id": "c2", "beat_id": "c2_b1"}) is None


def test_resolve_outline_context(tmp_path):
    rc = {"runtime": {"outline": {"enabled": True}}, "agents": {"characters": {"enabled_ids": ["p"]}}}
    snap = _snap(tmp_path, progress={"version": 1, "chapter_id": "c1", "beat_id": "c1_b1"})
    snippet, beat = resolve_outline_context(rc, snap, {"characters": [{"id": "p", "name": "P", "is_protagonist": True}]},
                                            protagonist_id="p", protagonist_display_name="P")
    assert beat is not None and beat.beat_id == "c1_b1"
    assert "全书大纲" in snippet and "氛围" in snippet and "主角" in snippet
    # disabled → ("", None)
    rc_off = {"runtime": {"outline": {"enabled": False}}}
    s2, b2 = resolve_outline_context(rc_off, snap)
    assert s2 == "" and b2 is None
    # 无 snapshot → ("", None)
    s3, b3 = resolve_outline_context(rc, None)
    assert s3 == "" and b3 is None


def test_save_progress_reload_roundtrip(tmp_path):
    root = tmp_path / "novel"
    od = root / "book" / "outline"
    od.mkdir(parents=True)
    (od / "outline.yaml").write_text(yaml.safe_dump(_outline_dict_two_chapters(), allow_unicode=True), encoding="utf-8")
    pp = save_progress(root, {"chapter_id": "c1", "beat_id": "c1_b2", "turns_in_beat": 4})
    assert pp.exists()
    # 重启续读：MV-2 验收 §5.1 —— 读到上一轮写入的值 + updated_at
    snap = load_outline_snapshot(root)
    assert snap is not None and snap.progress is not None
    assert snap.progress["chapter_id"] == "c1"
    assert snap.progress["beat_id"] == "c1_b2"
    assert snap.progress["turns_in_beat"] == 4
    assert snap.progress.get("updated_at")  # I/O 层已补时间戳


def test_resolve_missing_chapter_ref(tmp_path):
    snap = _snap(tmp_path, progress={"version": 1, "chapter_id": "NO_SUCH", "beat_id": "x"})
    bc = resolve_current_beat(snap)
    assert bc is not None  # 仍回退不崩
    assert bc.missing_ref == "chapter"
    assert bc.chapter_id == "c1"


def test_resolve_missing_beat_ref(tmp_path):
    snap = _snap(tmp_path, progress={"version": 1, "chapter_id": "c1", "beat_id": "NO_SUCH"})
    bc = resolve_current_beat(snap)
    assert bc is not None
    assert bc.missing_ref == "beat"


def test_bump_then_resolve_reads_incremented(tmp_path):
    """MVP-2 验收 §5.2：进度与作者推进一致（bump 后 resolve 读到 +1）。"""
    root = tmp_path / "novel"
    od = root / "book" / "outline"
    od.mkdir(parents=True)
    (od / "outline.yaml").write_text(yaml.safe_dump(_outline_dict_two_chapters(), allow_unicode=True), encoding="utf-8")
    (od / "progress.yaml").write_text(
        yaml.safe_dump({"version": 1, "chapter_id": "c1", "beat_id": "c1_b1", "turns_in_beat": 2}),
        encoding="utf-8",
    )
    snap = load_outline_snapshot(root)
    bumped = bump_turns_in_beat(snap.progress)
    save_progress(root, bumped)
    assert resolve_current_beat(load_outline_snapshot(root)).turns_in_beat == 3
