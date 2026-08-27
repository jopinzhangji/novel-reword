"""
冲突裁决单元测试：resolve_turn_conflict 合并 scope 摘要与角色言行。
与 TECH_IMPLEMENTATION 冲突裁决、NEXT_ITERATION 第 6 项一致。
"""
import pytest
from src.orchestrator import resolve_turn_conflict
from src.agents.character import CharacterTurnOutput
from src.agents.world import ScopeTurnOutput


def test_resolve_empty_characters():
    scope = ScopeTurnOutput(constraints=[], event_summary="本回合无事件", state_delta=None)
    got = resolve_turn_conflict(scope, {})
    assert "本回合无事件" in got
    assert got.strip() == "本回合无事件"


def test_resolve_merges_scope_and_character_actions():
    scope = ScopeTurnOutput(constraints=[], event_summary="场景：京城", state_delta=None)
    chars = {
        "a": CharacterTurnOutput(dialogue_action="林远开口。", inner_monologue="", metadata=None),
        "b": CharacterTurnOutput(dialogue_action="苏婉点头。", inner_monologue="", metadata=None),
    }
    got = resolve_turn_conflict(scope, chars)
    assert "场景：京城" in got
    assert "林远开口" in got
    assert "苏婉点头" in got
    assert " | " in got
    # 按 character_id 字典序，a 在 b 前
    parts = got.split(" | ")
    assert len(parts) >= 2
    assert parts[0].strip() == "场景：京城"
    assert "林远开口" in parts[1]
    assert "苏婉点头" in parts[2]


def test_resolve_skips_empty_dialogue_action():
    scope = ScopeTurnOutput(constraints=[], event_summary="事件", state_delta=None)
    chars = {
        "a": CharacterTurnOutput(dialogue_action="", inner_monologue="有", metadata=None),
        "b": CharacterTurnOutput(dialogue_action="   ", inner_monologue="", metadata=None),
        "c": CharacterTurnOutput(dialogue_action="说话", inner_monologue="", metadata=None),
    }
    got = resolve_turn_conflict(scope, chars)
    assert "事件" in got
    assert "说话" in got
    assert got.count(" | ") >= 1
