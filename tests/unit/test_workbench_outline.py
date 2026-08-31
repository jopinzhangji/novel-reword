"""G4 大纲/节拍（outline.py）：当前指针 + missing_ref 标注 + 无大纲降级。"""
from src.workbench import outline
from tests.unit.workbench_support import make_project, write_outline


def test_outline_current_pointer(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_outline(roots["alpha"])
    o = outline.outline(roots["alpha"])
    assert o["present"] is True
    assert len(o["chapters"]) == 2
    cur = o["current"]
    assert cur["chapter_id"] == "ch1" and cur["beat_id"] == "b1"
    assert cur["turns_in_beat"] == 2
    assert cur["beat_intent"] == "开场遇袭"
    assert cur["tags"] == ["动作"]
    assert cur["missing_ref"] == ""


def test_progress_missing_beat_ref(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_outline(roots["alpha"], ch_refs="ch1", beat_refs="nonexistent")
    p = outline.progress(roots["alpha"])
    assert p["present"] is True
    assert p["current"]["missing_ref"] == "beat"


def test_progress_missing_chapter_ref(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_outline(roots["alpha"], ch_refs="chX", beat_refs="b1")
    p = outline.progress(roots["alpha"])
    assert p["current"]["missing_ref"] == "chapter"


def test_outline_absent(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    assert outline.outline(roots["alpha"]) == {"present": False}
    assert outline.progress(roots["alpha"]) == {"present": False}