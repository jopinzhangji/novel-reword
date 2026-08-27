"""author_classified_memory：归类归一化、追加与索引。"""
from pathlib import Path

from src.author_loop import author_classified_memory as acm


def test_normalize_categories():
    spec = acm.get_author_classified_spec(None)
    assert acm._normalize_categories(["constraints", "narrative"], spec) == [
        "constraints",
        "narrative",
    ]
    assert acm._normalize_categories(["约束", "剧情"], spec) == ["constraints", "narrative"]
    assert acm._normalize_categories([], spec) == ["meta"]


def test_dynamic_categories_merge_defaults():
    cfg = {
        "runtime": {
            "author_classified_memory": {
                "include_defaults": True,
                "categories": [
                    {
                        "id": "romance",
                        "label_zh": "感情线",
                        "hint": "CP、暧昧节奏",
                    }
                ],
            }
        }
    }
    spec = acm.get_author_classified_spec(cfg)
    assert "romance" in spec.category_ids
    assert "setting" in spec.category_ids
    assert spec.defs_by_id["romance"]["label_zh"] == "感情线"


def test_dynamic_categories_replace():
    cfg = {
        "runtime": {
            "author_classified_memory": {
                "include_defaults": False,
                "fallback_id": "misc",
                "categories": [
                    {"id": "clues", "label_zh": "线索", "hint": "推理伏笔"},
                    {"id": "misc", "label_zh": "其它", "hint": ""},
                ],
            }
        }
    }
    spec = acm.get_author_classified_spec(cfg)
    assert spec.category_ids == ("clues", "misc")
    assert spec.fallback_id == "misc"
    out = acm._normalize_categories(["clues"], spec)
    assert out == ["clues"]
    out2 = acm._normalize_categories(["设定"], spec)
    assert out2 == ["misc"]


def test_extract_json_object():
    raw = '说明\n```json\n{"categories":["setting"],"one_line":"x"}\n```'
    d = acm._extract_json_object(raw)
    assert d == {"categories": ["setting"], "one_line": "x"}


def test_append_and_index(tmp_path):
    book = tmp_path / "book"
    acm.ensure_author_memory_layout(book)
    acm.append_classified_entries(
        book,
        "scope_a",
        "不要出现血腥描写",
        {"categories": ["constraints"], "one_line": "禁用血腥", "retrieval_query": "血腥"},
    )
    p = book / "memory" / "author_classified" / "constraints" / "entries.md"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "不要出现血腥描写" in text
    idx = acm.build_category_index_snippet(book)
    assert "constraints" in idx
    assert "不要出现血腥描写" in idx or "禁用血腥" in idx


def test_classify_author_input_empty():
    assert acm.classify_author_input("", {})["categories"] == ["meta"]


def test_progressive_empty_when_no_dir(tmp_path):
    # 无 author_classified 目录时索引为空，不加载
    book = tmp_path / "book"
    book.mkdir(parents=True)
    snippet = acm.progressive_author_memory_for_plan(
        tmp_path,
        {"runtime": {"storage": {"data_root": str(tmp_path)}}},
        "s",
        "",
    )
    assert snippet == ""
