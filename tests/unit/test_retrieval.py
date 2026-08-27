"""
记忆与事件检索单元测试：retrieve_character_memory、format_scope_events_snippet。
与 TECH_IMPLEMENTATION §10 一致。
"""
import pytest
from src.retrieval import (
    retrieve_character_memory,
    format_scope_events_snippet,
    format_secondary_characters_snippet,
)
from src.runtime.storage import MemoryStorage


def test_retrieve_character_memory_empty():
    storage = MemoryStorage()
    got = retrieve_character_memory(storage, "a")
    assert got == ""


def test_retrieve_character_memory_includes_profile_and_events():
    storage = MemoryStorage()
    storage.update_profile("a", {"name": "林远", "role": "主角"})
    storage.append_event_refinement("a", {"summary": "曾在京城与苏婉见面"})
    got = retrieve_character_memory(storage, "a")
    assert "林远" in got
    assert "京城" in got or "苏婉" in got
    assert "[人物设定]" in got or "name=" in got
    assert "[事件提炼]" in got or "曾在" in got


def test_retrieve_character_memory_respects_events_limit():
    storage = MemoryStorage()
    for i in range(5):
        storage.append_event_refinement("a", {"summary": f"事件{i}"})
    got = retrieve_character_memory(storage, "a", events_limit=2)
    assert "事件" in got


def test_format_scope_events_snippet_empty():
    storage = MemoryStorage()
    got = format_scope_events_snippet(storage, "capital", k=5)
    assert got == ""


def test_format_scope_events_snippet_joins_summaries():
    storage = MemoryStorage()
    storage.append_events("capital", [{"summary": "春宴"}, {"summary": "宫变"}])
    got = format_scope_events_snippet(storage, "capital", k=5)
    assert "春宴" in got
    assert "宫变" in got
    assert " | " in got


def test_format_secondary_characters_snippet_storage_without_method():
    """Storage 无 get_secondary_characters 时返回空字符串。"""
    class NoSecondary:
        pass
    got = format_secondary_characters_snippet(NoSecondary(), scope_id="村庄", limit=10)
    assert got == ""


def test_format_secondary_characters_snippet_empty():
    storage = MemoryStorage()
    got = format_secondary_characters_snippet(storage, scope_id="村庄", limit=10)
    assert "暂无其他角色记录" in got or "可自由生成" in got


def test_format_secondary_characters_snippet_with_entries():
    storage = MemoryStorage()
    storage.append_secondary_character({"name": "村长", "brief": "青石村村长", "scope_id": "村庄"})
    storage.append_secondary_character({"name": "猎户老陈", "brief": "常进山打猎"})
    got = format_secondary_characters_snippet(storage, scope_id="村庄", limit=10)
    assert "村长" in got
    assert "青石村村长" in got
    assert "猎户老陈" in got
    assert "已出现的其他角色" in got or "供参考" in got
