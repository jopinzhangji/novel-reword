from types import SimpleNamespace

from src.author_loop.turn_planning import TurnPlan, build_turn_body_prompt, build_turn_plan_prompt


def test_build_turn_plan_prompt_includes_pacing_block() -> None:
    ctx = SimpleNamespace(
        scope_id="main",
        time="夜",
        place="城门",
        shared_story_snippet="上一回合主角入城。",
        secondary_characters_snippet="",
    )
    prompt = build_turn_plan_prompt(
        ctx,
        {"name": "主线", "description": "城内局势复杂。"},
        "事件摘要",
        pacing_prompt_block="【节奏约束（Pacing Contract）】\n- pace_mode: balanced",
    )
    assert "【节奏约束（Pacing Contract）】" in prompt
    assert "pace_mode: balanced" in prompt


def test_build_turn_body_prompt_includes_pacing_block() -> None:
    plan = TurnPlan(analysis="分析", estimated_chars=1200)
    result = SimpleNamespace(
        scope_output=SimpleNamespace(event_summary="回合事件", constraints=["约束1"]),
        character_outputs={"a": SimpleNamespace(inner_monologue="", dialogue_action="点头")},
    )
    ctx = SimpleNamespace(scope_id="main")
    prompt = build_turn_body_prompt(
        plan,
        result,
        ctx,
        pacing_prompt_block="【节奏约束（Pacing Contract）】\n- goal_window: 推进",
    )
    assert "【节奏约束（Pacing Contract）】" in prompt
    assert "goal_window: 推进" in prompt

