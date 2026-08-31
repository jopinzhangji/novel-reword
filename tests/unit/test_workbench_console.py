"""G4 作者控制台写口（console.py）：能力开关 / 镜头 / 备选稿读写。"""
from pathlib import Path

from src.runtime.capabilities import load_features
from src.workbench import console
from tests.unit.workbench_support import make_project


def test_console_status_default(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    s = console.console_status(roots["alpha"])
    # 默认无主角显式镜头；能力默认全关
    assert s["lens"]["protagonist_id"] is not None or s["lens"]["is_override"] is False
    assert s["features"]["flags"]["info_view"] is False
    assert s["drafts"] == [] and s["draft_count"] == 0


def test_patch_features_persists(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    res = console.patch_features(roots["alpha"], {"info_view": True, "semantic_edges": True})
    assert res["flags"]["info_view"] is True
    assert res["flags"]["semantic_edges"] is True
    assert res["persisted_override"]["info_view"] is True
    assert load_features(roots["alpha"]).get("info_view") is True
    # 只写真布尔键，字符串不污染的
    console.patch_features(roots["alpha"], {"react_chain": "yes"})
    assert load_features(roots["alpha"]).get("react_chain") is not True


def test_switch_lens_persists_protagonist(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    res = console.switch_lens(roots["alpha"], "李B")
    assert res["protagonist_id"] == "李B" and res["display_name"] == "李B"
    s = console.console_status(roots["alpha"])
    assert s["lens"]["is_override"] is True
    assert s["lens"]["protagonist_id"] == "李B"
    # 无效镜头 → 保持原镜头
    res2 = console.switch_lens(roots["alpha"], "不存在")
    st = console.console_status(roots["alpha"])
    assert st["lens"]["protagonist_id"] == "李B"


def test_drafts_write_list_promote(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    w = console.write_draft(roots["alpha"], "ch1", "李B", "李B视角正文")
    assert Path(w["path"]).is_file()
    drafts = console.list_drafts(roots["alpha"], chapter_id="ch1")
    assert len(drafts) == 1 and drafts[0]["lens_id"] == "李B" and drafts[0]["status"] == "draft"
    res = console.promote_draft(roots["alpha"], "ch1", "李B")
    assert res["promoted"] is True and res["lens_id"] == "李B"
    assert Path(w["path"]).exists()  # 提升不改文件名，仅置 status
    # 跨章列出也含它
    all_d = console.list_drafts(roots["alpha"])
    assert any(d["status"] == "promoted" for d in all_d)


def test_promote_unknown_is_false(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    res = console.promote_draft(roots["alpha"], "chX", "李B")
    assert res["promoted"] is False