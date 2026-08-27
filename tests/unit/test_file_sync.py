"""
file_sync 单元测试：data_root、回合计数器、回合内容与 scope/character 双写、README 索引。
"""
import pytest
from pathlib import Path

from src.runtime import file_sync


def test_get_data_root_none_when_unset(tmp_path):
    """未配置 storage.data_root 时返回 None。"""
    assert file_sync.get_data_root(tmp_path, {}) is None
    assert file_sync.get_data_root(tmp_path, {"runtime": {}}) is None


def test_get_data_root_returns_path_when_set(tmp_path):
    """配置 storage.data_root 时返回 project_root / 该值。"""
    cfg = {"storage": {"data_root": "novel_data"}}
    root = file_sync.get_data_root(tmp_path, cfg)
    assert root is not None
    assert root == tmp_path / "novel_data"


def test_get_book_root_none_when_data_root_unset(tmp_path):
    """未配置 data_root 时 get_book_root 返回 None。"""
    assert file_sync.get_book_root(tmp_path, {}) is None


def test_get_book_root_returns_book_under_data_root(tmp_path):
    """配置 data_root 时 get_book_root 返回 data_root/book。"""
    cfg = {"runtime": {"storage": {"data_root": "novel_data"}}}
    assert file_sync.get_book_root(tmp_path, cfg) == tmp_path / "novel_data" / "book"


def test_next_turn_index_increments(tmp_path):
    """next_turn_index 从 1 递增。"""
    assert file_sync.next_turn_index(tmp_path) == 1
    assert file_sync.next_turn_index(tmp_path) == 2
    assert file_sync.next_turn_index(tmp_path) == 3


def test_write_turn_content_creates_turn_md(tmp_path):
    """write_turn_content 创建 book/content/turns/turn_NNNN.md 并更新 README。"""
    file_sync.write_turn_content(
        tmp_path, 1, "scope1", "时间", "地点", "本回合摘要", {"角色A": {"dialogue_action": "说了什么"}}
    )
    path = tmp_path / "book" / "content" / "turns" / "turn_0001.md"
    assert path.is_file()
    assert "scope_id" in path.read_text(encoding="utf-8")
    assert "本回合摘要" in path.read_text(encoding="utf-8")
    assert (tmp_path / "book" / "content" / "turns" / "README.md").is_file()
    assert "turn_0001.md" in (tmp_path / "book" / "content" / "turns" / "README.md").read_text(encoding="utf-8")


def test_sync_scope_turn_creates_events_and_state(tmp_path):
    """sync_scope_turn 创建 book/events/<id>/events/turn_NNNN.md 与 state.md。"""
    file_sync.sync_scope_turn(
        tmp_path, "怪物来袭", 1, {"summary": "事件摘要"}, {"place": "村庄"}
    )
    events_dir = tmp_path / "book" / "events" / "怪物来袭" / "events"
    assert (events_dir / "turn_0001.md").is_file()
    assert (tmp_path / "book" / "events" / "怪物来袭" / "state.md").is_file()
    assert "事件摘要" in (events_dir / "turn_0001.md").read_text(encoding="utf-8")


def test_sync_character_turn_creates_events_md(tmp_path):
    """sync_character_turn 创建 book/characters/<id>/events/turn_NNNN.md。"""
    file_sync.sync_character_turn(tmp_path, "张凡", 1, {"summary": "本回合记忆提炼"})
    path = tmp_path / "book" / "characters" / "张凡" / "events" / "turn_0001.md"
    assert path.is_file()
    assert "本回合记忆提炼" in path.read_text(encoding="utf-8")


def test_ensure_memory_root_readmes_creates_listings(tmp_path):
    """ensure_memory_root_readmes 创建 book/README、content/setting/characters/events 索引。"""
    file_sync.ensure_memory_root_readmes(tmp_path, ["怪物来袭", "村庄"], ["张凡", "李墨"])
    assert (tmp_path / "book" / "README.md").is_file()
    assert (tmp_path / "book" / "characters" / "README.md").is_file()
    assert (tmp_path / "book" / "events" / "README.md").is_file()
    events_readme = (tmp_path / "book" / "events" / "README.md").read_text(encoding="utf-8")
    assert "怪物来袭" in events_readme and "村庄" in events_readme
