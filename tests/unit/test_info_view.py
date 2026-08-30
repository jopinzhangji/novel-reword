"""信息视野 / 感知不对称（§4.6）：按角色过滤事件视图，未知部分不泄内容。"""
from src.runtime.storage import MemoryStorage
from src.retrieval.info_view import (
    build_character_event_view,
    event_visible_to_character,
    format_unknown_hint,
)


def _storage_with_events() -> MemoryStorage:
    s = MemoryStorage()
    s.append_events("capital", [
        {"summary": "林远向苏婉坦白身世", "present_characters": ["lin_yuan", "su_wan"]},
        {"summary": "林远独自潜入宫禁被发现", "present_characters": ["lin_yuan"]},
        {"summary": "许默在城郊独自猎杀妖兽", "present_characters": ["xu_mo"]},
    ])
    return s


def test_event_visible_to_character_present():
    assert event_visible_to_character({"present_characters": ["a", "b"]}, "a") is True
    assert event_visible_to_character({"present_characters": ["a", "b"]}, "c") is False


def test_event_visible_to_character_public():
    assert event_visible_to_character({"visibility": "public", "summary": "x"}, "c") is True


def test_event_visible_to_character_untagged_defaults_visible():
    # 无 present_characters/visibility 的旧事件默认可见（兼容，不做剧透收缩）
    assert event_visible_to_character({"summary": "x"}, "c") is True


def test_build_character_event_view_filters_by_presence():
    s = _storage_with_events()
    view = build_character_event_view(s, "su_wan", scope_id="capital")
    assert "坦白身世" in view
    # 林远独自事件与许默独自事件对苏婉不可见 → 不应泄露内容给苏婉
    assert "宫禁" not in view
    assert "妖兽" not in view
    # 记录有"未亲自参与"的计数说明
    assert "未亲身参与" in view


def test_build_character_event_view_excludes_other_narrow_event():
    s = _storage_with_events()
    view = build_character_event_view(s, "xu_mo", scope_id="capital")
    assert "妖兽" in view
    assert "坦白" not in view


def test_build_character_event_view_empty_when_nothing_known():
    s = MemoryStorage()
    view = build_character_event_view(s, "nobody", scope_id="capital")
    assert "没有亲身经历" in view


def test_format_unknown_hint():
    assert format_unknown_hint("a", "capital", known_count=0, unknown_count=2) != ""
    assert "未亲身参与" in format_unknown_hint("a", "capital", known_count=1, unknown_count=2)
    assert format_unknown_hint("a", "capital", known_count=1, unknown_count=0) == ""