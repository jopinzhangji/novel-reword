"""G3 候选备选稿（SDD D12 §4.1）：写/列/提升生命周期；提升替稿并返回 lens；dry-run 不立库语义由 run_novel 侧抑制。"""
from src.runtime.alt_draft import list_alt_drafts, promote_alt_draft, write_alt_draft


def _root(tmp_path):
    return tmp_path / "novel"


def test_write_and_list(tmp_path):
    root = _root(tmp_path)
    p = write_alt_draft(root, "ch1", "mo", "墨音视角正文")
    assert p.exists()
    drafts = list_alt_drafts(root, "ch1")
    assert len(drafts) == 1
    d = drafts[0]
    assert d.lens_id == "mo" and d.status == "draft" and d.body == "墨音视角正文"


def test_promote_writes_canonical_and_flips_status(tmp_path):
    root = _root(tmp_path)
    write_alt_draft(root, "ch1", "li", "李逍视角正文")
    _seen = {}

    def w(body):
        fp = root / "book" / "content" / "drafts" / "ch1.md"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(body, encoding="utf-8")
        _seen["body"] = body
        return fp

    res = promote_alt_draft(root, "ch1", "li", canonical_writer=w)
    assert res is not None
    cp, lens = res
    assert cp.exists() and lens == "li"
    assert _seen["body"] == "李逍视角正文"
    assert list_alt_drafts(root, "ch1")[0].status == "promoted"
    # 已提升 → 再次提升返回 None
    assert promote_alt_draft(root, "ch1", "li") is None


def test_promote_unknown_returns_none(tmp_path):
    assert promote_alt_draft(_root(tmp_path), "chX", "mo") is None


def test_promote_without_canonical_writer(tmp_path):
    root = _root(tmp_path)
    write_alt_draft(root, "ch1", "mo", "正文")
    res = promote_alt_draft(root, "ch1", "mo")
    assert res is not None
    cp, lens = res
    assert cp == __import__("pathlib").Path(root) / "state" / "drafts" / "ch1_mo.md"
    assert lens == "mo"


def test_no_drafts_empty(tmp_path):
    assert list_alt_drafts(_root(tmp_path), "ch1") == []