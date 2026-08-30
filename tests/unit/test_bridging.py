"""G1 屏外线 / 并列主线：桥接摘要注入（SDD D10，phase G1b）。"""
from pathlib import Path

from src.context import build_turn_context, build_turn_context_from_storage
from src.retrieval.bridging import (
    DEFAULT_BRIDGE_BUDGET_CHARS,
    build_bridging_snippet_from_storage,
    format_bridging_snippet,
)
from src.runtime.memory_layers import THREAD_OFF_SCREEN, THREAD_PARALLEL
from src.runtime.storage import MemoryStorage


def _tmp_root(tmp_path) -> Path:
    return tmp_path / "novel"


def _ctx():
    return build_turn_context(
        scope_id="main",
        time="夜",
        place="城北驿站",
        present_character_ids=["li"],
        last_turn_summary="迷雾渐浓",
        bridging_snippet="【桥接摘要（wang 屏外结果）】\n- 在那座地窖里发现一封密信",
    )


# --- format_bridging_snippet：纯格式化 ---


def test_format_bridging_snippet_empty_returns_empty():
    assert format_bridging_snippet([], name="wang") == ""
    assert format_bridging_snippet([{"summary": "  "}], name="wang") == ""


def test_format_bridging_snippet_label_and_bullets():
    entries = [
        {"thread": THREAD_OFF_SCREEN, "summary": "独访地窖"},
        {"thread": THREAD_PARALLEL, "plan": "修炼功法有成"},
    ]
    out = format_bridging_snippet(entries, name="王二")
    assert "【桥接摘要（王二 屏外结果）】" in out
    assert "- 独访地窖" in out
    assert "- 修炼功法有成" in out
    assert "【" in out


def test_format_bridging_snippet_truncates_budget():
    entries = [{"summary": "长" * 500}]
    out = format_bridging_snippet(entries, budget_chars=30)
    assert len(out) <= 30 + 1
    assert out.endswith("…")


# --- build_bridging_snippet_from_storage：默认关 + 明示 bridge_ids ---


def test_bridging_snippet_disabled_by_default():
    st = MemoryStorage()
    st.append_off_screen_refinement("wang", {"thread": THREAD_OFF_SCREEN, "summary": "屏外发现密信"})
    out = build_bridging_snippet_from_storage(st, ["li"], parallel_threads_cfg={"enabled": False})
    assert out == ""
    out = build_bridging_snippet_from_storage(st, ["li"], parallel_threads_cfg={"enabled": True})
    assert out == ""  # 未给 bridge_ids → 空串


def test_bridging_snippet_enabled_explicit_ids():
    st = MemoryStorage()
    st.append_off_screen_refinement("wang", {"thread": THREAD_OFF_SCREEN, "summary": "屏外发现密信"})
    st.append_off_screen_refinement("li", {"thread": THREAD_OFF_SCREEN, "summary": "屏外练功"})
    chars_cfg = {"characters": [{"id": "li", "name": "李逍"}, {"id": "wang", "name": "王二"}]}
    out = build_bridging_snippet_from_storage(
        st,
        ["li"],
        parallel_threads_cfg={"enabled": True, "bridge_ids": ["wang"]},
        characters_config=chars_cfg,
    )
    assert "【桥接摘要（王二 屏外结果）】" in out
    assert "屏外发现密信" in out
    # 已在场角色 li 虽也在 bridge_ids，但其屏外结果不用于本场景 → 跳过
    out2 = build_bridging_snippet_from_storage(
        st,
        ["li"],
        parallel_threads_cfg={"enabled": True, "bridge_ids": ["li", "wang"]},
        characters_config=chars_cfg,
    )
    assert "屏外练功" not in out2
    assert "屏外发现密信" in out2


def test_bridging_snippet_no_off_screen_entries_empty():
    st = MemoryStorage()
    out = build_bridging_snippet_from_storage(
        st, ["li"], parallel_threads_cfg={"enabled": True, "bridge_ids": ["wang"]}
    )
    assert out == ""


# --- TurnContext：bridging_snippet 字段往返 ---


def test_turn_context_carries_bridging_snippet():
    ctx = _ctx()
    assert ctx.bridging_snippet.startswith("【桥接摘要")


def test_build_turn_context_from_storage_default_bridging_empty():
    st = MemoryStorage()
    ctx = build_turn_context_from_storage(
        scope_id="main", time="夜", place="城", present_character_ids=["li"], storage=st
    )
    assert ctx.bridging_snippet == ""


# --- 正文 prompt：桥接块注入位置 ---


def test_build_turn_body_prompt_includes_bridge_block():
    from src.agents.character.agent import CharacterTurnOutput
    from src.agents.world.agent import ScopeTurnOutput
    from src.author_loop.turn_planning import TurnPlan, build_turn_body_prompt
    from src.orchestrator import TurnResult

    plan = TurnPlan(analysis="夜色宁静", estimated_chars=100)
    scope = ScopeTurnOutput(event_summary="城北驿站发生命案", constraints=["呼叫巡城司"])
    out = CharacterTurnOutput(
        inner_monologue="血泊边有一枚令牌",
        dialogue_action="蹲下拾起令牌",
    )
    result = TurnResult(scope_output=scope, character_outputs={"li": out})
    ctx = _ctx()
    prompt = build_turn_body_prompt(plan, result, ctx, bridging_snippet=ctx.bridging_snippet)
    assert "【桥接摘要（wang 屏外结果）】" in prompt
    assert "在那座地窖里发现一封密信" in prompt
    # 默认空 → 正文 prompt 无桥接（保持无桥接场景行为）
    ctx_plain = build_turn_context("main", "夜", "城", ["li"])
    prompt_plain = build_turn_body_prompt(plan, result, ctx_plain)
    assert "桥接摘要" not in prompt_plain