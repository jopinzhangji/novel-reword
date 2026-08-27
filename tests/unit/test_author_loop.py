"""
作者在环 CLI 单元测试：review_turn_result、review_memory_plan 的同意/驳回返回值。
与 NEXT_ITERATION 第 7 项一致。
"""
import pytest
from src.author_loop import review_turn_result, review_memory_plan
from src.orchestrator import TurnResult
from src.agents.character import CharacterTurnOutput
from src.agents.world import ScopeTurnOutput


def _make_result() -> TurnResult:
    return TurnResult(
        scope_output=ScopeTurnOutput(
            constraints=["约束1"],
            event_summary="本回合事件摘要",
            state_delta=None,
        ),
        character_outputs={
            "a": CharacterTurnOutput(inner_monologue="内心", dialogue_action="言行A", metadata=None),
            "b": CharacterTurnOutput(inner_monologue="", dialogue_action="言行B", metadata=None),
        },
    )


def test_review_turn_result_accept():
    result = _make_result()
    approved, result_to_use = review_turn_result(result, "capital", "永和十年春", "京城", input_fn=lambda _: "y")
    assert approved is True
    assert result_to_use is not None


def test_review_turn_result_reject():
    result = _make_result()
    approved, result_to_use = review_turn_result(result, "capital", "永和十年春", "京城", input_fn=lambda _: "n")
    assert approved is False
    assert result_to_use is None


def test_review_turn_result_default_yes():
    result = _make_result()
    approved, result_to_use = review_turn_result(result, "capital", "永和十年春", "京城", input_fn=lambda _: "")
    assert approved is True
    assert result_to_use is not None


def test_review_memory_plan_accept():
    result = _make_result()
    confirmed, result_to_use = review_memory_plan(result, "capital", "永和十年春", "京城", input_fn=lambda _: "yes")
    assert confirmed is True
    assert result_to_use is not None


def test_review_memory_plan_reject():
    result = _make_result()
    confirmed, result_to_use = review_memory_plan(result, "capital", "永和十年春", "京城", input_fn=lambda _: "n")
    assert confirmed is False
    assert result_to_use is None


def test_review_memory_plan_default_yes():
    result = _make_result()
    confirmed, result_to_use = review_memory_plan(result, "capital", "永和十年春", "京城", input_fn=lambda _: "")
    assert confirmed is True
    assert result_to_use is not None


def test_review_turn_result_edit_path_returns_modified_result(tmp_path):
    """输入 e 且提供 edit_output_dir 时，写入文件后按回车读回，返回 (True, result_to_use)。"""
    result = _make_result()
    responses = iter(["e", ""])
    input_fn = lambda _: next(responses)
    approved, result_to_use = review_turn_result(
        result, "capital", "永和十年春", "京城",
        input_fn=input_fn,
        edit_output_dir=tmp_path,
    )
    assert approved is True
    assert result_to_use is not None
    assert result_to_use.scope_output.event_summary == result.scope_output.event_summary


def test_review_turn_result_supplement_then_accept():
    """选 s 补充设定时调用 supplement_callback，再选 y 返回 (True, result)。"""
    result = _make_result()
    calls = []
    def supplement_callback(sid: str, t: str, p: str, summary: str) -> None:
        calls.append((sid, t, p, summary))
    responses = iter(["s", "y"])
    input_fn = lambda _: next(responses)
    approved, result_to_use = review_turn_result(
        result, "capital", "永和十年春", "京城",
        input_fn=input_fn,
        supplement_callback=supplement_callback,
    )
    assert len(calls) == 1
    assert calls[0] == ("capital", "永和十年春", "京城", "本回合事件摘要")
    assert approved is True
    assert result_to_use is not None
