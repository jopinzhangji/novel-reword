"""
Storage 抽象（内存版）测试：角色 profile/relations/events/emotions，范围 events/state。
与 TECH_IMPLEMENTATION §7 键结构一致。
"""
import pytest
from src.runtime.storage import MemoryStorage


class TestMemoryStorageProfile:
    def test_get_profile_empty(self):
        s = MemoryStorage()
        assert s.get_profile("c1") == {}

    def test_update_profile_and_get(self):
        s = MemoryStorage()
        s.update_profile("c1", {"name": "林远", "role": "主角"})
        assert s.get_profile("c1") == {"name": "林远", "role": "主角"}
        s.update_profile("c1", {"role": "配角"})
        assert s.get_profile("c1") == {"name": "林远", "role": "配角"}


class TestMemoryStorageRelations:
    def test_get_relations_empty(self):
        s = MemoryStorage()
        assert s.get_relations("c1") == []

    def test_append_relation_and_get(self):
        s = MemoryStorage()
        s.append_relation("c1", {"target_id": "c2", "type": "friend", "intensity": 0.8})
        rel = s.get_relations("c1")
        assert len(rel) == 1
        assert rel[0]["target_id"] == "c2"


class TestMemoryStorageEvents:
    def test_get_events_empty(self):
        s = MemoryStorage()
        assert s.get_events("c1") == []

    def test_append_event_refinement_and_get(self):
        s = MemoryStorage()
        s.append_event_refinement("c1", {"scope_id": "capital", "summary": "入宫"})
        s.append_event_refinement("c1", {"scope_id": "capital", "summary": "离宫"})
        ev = s.get_events("c1", limit=10)
        assert len(ev) == 2
        assert ev[0]["summary"] == "入宫"
        assert ev[1]["summary"] == "离宫"

    def test_get_events_respects_limit(self):
        s = MemoryStorage()
        for i in range(5):
            s.append_event_refinement("c1", {"n": i})
        assert len(s.get_events("c1", limit=2)) == 2


class TestMemoryStorageEmotions:
    def test_get_emotions_empty(self):
        s = MemoryStorage()
        assert s.get_emotions("c1") == []

    def test_append_emotion_and_get(self):
        s = MemoryStorage()
        s.append_emotion("c1", {"target_id": "c2", "emotion": "trust"})
        em = s.get_emotions("c1")
        assert len(em) == 1
        assert em[0]["target_id"] == "c2"
        assert s.get_emotions("c1", target_id="c2") == em
        assert s.get_emotions("c1", target_id="c3") == []


class TestMemoryStorageScopeEvents:
    def test_append_events_and_get_recent(self):
        s = MemoryStorage()
        s.append_events("scope1", [{"turn": 1, "text": "事件1"}, {"turn": 2, "text": "事件2"}])
        ev = s.get_recent_events("scope1", k=10)
        assert len(ev) == 2
        assert ev[0]["text"] == "事件1"
        assert ev[1]["text"] == "事件2"

    def test_get_recent_respects_k(self):
        s = MemoryStorage()
        s.append_events("scope1", [{"n": i} for i in range(10)])
        assert len(s.get_recent_events("scope1", k=3)) == 3


class TestMemoryStorageScopeState:
    def test_get_state_empty(self):
        s = MemoryStorage()
        assert s.get_state("scope1") == {}

    def test_set_state_and_get(self):
        s = MemoryStorage()
        s.set_state("scope1", {"location": "京城", "faction": "朝廷"})
        assert s.get_state("scope1") == {"location": "京城", "faction": "朝廷"}
        s.set_state("scope1", {"location": "皇宫"})
        assert s.get_state("scope1") == {"location": "皇宫"}


class TestMemoryStorageSecondaryCharacters:
    """次要角色列表：非配置关键角色，可自由追加与按 scope 查阅。"""

    def test_get_secondary_characters_empty(self):
        s = MemoryStorage()
        assert s.get_secondary_characters() == []
        assert s.get_secondary_characters(scope_id="村庄") == []

    def test_append_secondary_character_and_get(self):
        s = MemoryStorage()
        s.append_secondary_character({"name": "村长", "brief": "青石村村长，五十余岁", "scope_id": "村庄"})
        lst = s.get_secondary_characters(limit=10)
        assert len(lst) == 1
        assert lst[0]["name"] == "村长"
        assert lst[0]["brief"] == "青石村村长，五十余岁"
        assert lst[0]["scope_id"] == "村庄"

    def test_get_secondary_characters_filter_by_scope(self):
        s = MemoryStorage()
        s.append_secondary_character({"name": "村长", "brief": "村长", "scope_id": "村庄"})
        s.append_secondary_character({"name": "猎户", "brief": "猎户", "scope_id": "村庄"})
        s.append_secondary_character({"name": "路人", "brief": "路人", "scope_id": "京城"})
        lst = s.get_secondary_characters(scope_id="村庄", limit=10)
        assert len(lst) == 2
        names = [e["name"] for e in lst]
        assert "村长" in names and "猎户" in names and "路人" not in names

    def test_get_secondary_characters_respects_limit(self):
        s = MemoryStorage()
        for i in range(5):
            s.append_secondary_character({"name": f"角色{i}", "brief": ""})
        assert len(s.get_secondary_characters(limit=2)) == 2
