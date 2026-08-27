"""
TurnContext 及构建方式测试：与 TECH_IMPLEMENTATION §6、§9 一致。
"""
import pytest
from src.context import TurnContext, build_turn_context, build_turn_context_from_storage
from src.runtime.storage import MemoryStorage


class TestTurnContext:
    def test_required_fields(self):
        ctx = build_turn_context(
            scope_id="capital",
            time="永和十年春",
            place="京城",
            present_character_ids=["a", "b"],
        )
        assert ctx.scope_id == "capital"
        assert ctx.time == "永和十年春"
        assert ctx.place == "京城"
        assert ctx.present_character_ids == ("a", "b")
        assert ctx.last_turn_summary == ""
        assert ctx.shared_story_snippet is None
        assert ctx.world_constraints is None

    def test_optional_fields(self):
        ctx = build_turn_context(
            scope_id="jianghu",
            time="永和十年夏",
            place="江边",
            present_character_ids=["a"],
            last_turn_summary="上回林远与苏婉相遇。",
            shared_story_snippet="林远来到江边。",
            world_constraints="无魔法，冷兵器。",
            secondary_characters_snippet="村长：青石村村长；猎户：常进山。",
        )
        assert ctx.last_turn_summary == "上回林远与苏婉相遇。"
        assert ctx.shared_story_snippet == "林远来到江边。"
        assert ctx.world_constraints == "无魔法，冷兵器。"
        assert ctx.secondary_characters_snippet == "村长：青石村村长；猎户：常进山。"

    def test_present_character_ids_tuple(self):
        ctx = build_turn_context(
            scope_id="s",
            time="t",
            place="p",
            present_character_ids=("a", "b"),
        )
        assert ctx.present_character_ids == ("a", "b")

    def test_empty_scope_id_raises(self):
        with pytest.raises(ValueError, match="scope_id 不能为空"):
            TurnContext(
                scope_id="",
                time="t",
                place="p",
                present_character_ids=(),
            )

    def test_frozen(self):
        ctx = build_turn_context("s", "t", "p", [])
        with pytest.raises(AttributeError):
            ctx.scope_id = "other"


class TestBuildTurnContextFromStorage:
    def test_without_events_uses_last_turn_summary(self):
        storage = MemoryStorage()
        ctx = build_turn_context_from_storage(
            scope_id="capital",
            time="永和十年春",
            place="京城",
            present_character_ids=["a"],
            storage=storage,
            last_turn_summary="上回入宫。",
        )
        assert ctx.scope_id == "capital"
        assert ctx.last_turn_summary == "上回入宫。"
        assert ctx.shared_story_snippet == "上回入宫。"

    def test_with_events_appends_to_snippet(self):
        storage = MemoryStorage()
        storage.append_events("capital", [
            {"summary": "林远入宫"},
            {"text": "面圣"},
        ])
        ctx = build_turn_context_from_storage(
            scope_id="capital",
            time="永和十年春",
            place="京城",
            present_character_ids=["a"],
            storage=storage,
            last_turn_summary="",
            recent_events_k=5,
        )
        assert "林远入宫" in (ctx.shared_story_snippet or "")
        assert "面圣" in (ctx.shared_story_snippet or "")

    def test_with_events_and_last_turn_concatenates(self):
        storage = MemoryStorage()
        storage.append_events("capital", [{"summary": "入宫"}])
        ctx = build_turn_context_from_storage(
            scope_id="capital",
            time="t",
            place="p",
            present_character_ids=[],
            storage=storage,
            last_turn_summary="上回",
            recent_events_k=2,
        )
        assert ctx.shared_story_snippet is not None
        assert "上回" in ctx.shared_story_snippet
        assert "入宫" in ctx.shared_story_snippet

    def test_secondary_characters_snippet_populated_from_storage(self):
        storage = MemoryStorage()
        storage.append_secondary_character({"name": "村长", "brief": "青石村村长", "scope_id": "村庄"})
        ctx = build_turn_context_from_storage(
            scope_id="村庄",
            time="末法时代",
            place="青石村",
            present_character_ids=["张凡"],
            storage=storage,
            secondary_characters_limit=20,
        )
        assert ctx.secondary_characters_snippet is not None
        assert "村长" in ctx.secondary_characters_snippet
        assert "青石村村长" in ctx.secondary_characters_snippet
