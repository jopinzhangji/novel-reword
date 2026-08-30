"""阶段 1a 接线：编排器事件打可见性标签 + CharacterAgent 注入信息视野（§4.6）。"""
from src.context import build_turn_context
from src.agents.character import CharacterAgent
from src.agents.world import ScopeAgent
from src.orchestrator import Orchestrator
from src.runtime.storage import MemoryStorage


def _make_orchestrator(storage, characters_config=None):
    runtime = {"agents": {"characters": {"enabled_ids": ["a", "b"]}}}
    chars = characters_config or {"characters": [{"id": "a", "name": "甲"}, {"id": "b", "name": "乙"}]}
    orch = Orchestrator(
        storage=storage,
        character_agents={cid: CharacterAgent(cid) for cid in ["a", "b"]},
        scope_agents={"capital": ScopeAgent("capital")},
        world_config={},
        runtime_config=runtime,
        characters_config=chars,
        data_root=None,
    )
    return orch, runtime, chars


def test_event_entry_tagged_with_present_characters():
    storage = MemoryStorage()
    orch, _, _ = _make_orchestrator(storage)
    result = orch.run_one_turn(
        scope_id="capital", time="春", place="京城",
        present_character_ids=["a", "b"], auto_write=True,
    )
    events = storage.get_recent_events("capital")
    assert len(events) == 1
    assert set(events[0]["present_characters"]) == {"a", "b"}


class _SpyProvider:
    def __init__(self, raw):
        self.raw = raw
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.raw


def test_character_agent_injects_own_info_view_only():
    storage = MemoryStorage()
    # 事件 a 在场、b 不在场：b 不应看到 a 的专属秘密
    storage.append_events("capital", [
        {"summary": "甲的秘密行动传遍全城", "present_characters": ["a"]},
    ])
    spy = _SpyProvider("内心独白：我知晓大事\n言行：我四处打探\n")
    agent = CharacterAgent(
        "b", storage=storage, runtime_config={}, characters_config={}, data_root=None,
    )
    ctx = build_turn_context(
        scope_id="capital", time="春", place="京城", present_character_ids=["a", "b"],
        shared_story_snippet="甲的秘密行动传遍全城",
    )
    import unittest.mock as mock
    with mock.patch("src.llm.get_llm_provider", return_value=spy):
        out = agent.turn(ctx)
    prompt = spy.calls[0]
    assert "【你的信息视野】" in prompt
    # 信息视野下，未亲自参与的事件内容不得注入给 b
    assert "秘密行动" not in prompt
    # 有"不在场不发生"的提示，避免 b 虚构其不知道的细节
    assert "不在场" in prompt
    assert out.dialogue_action.startswith("我四处打探")


def test_character_agent_injects_own_growth_state_when_data_root(tmp_path):
    from src.runtime.character_growth import save_growth_state, default_growth_state
    from src.runtime.storage import MemoryStorage

    data_root = tmp_path / "novel"
    state = default_growth_state("b")
    state.mind_state = {"警惕": 2, "防御倾向": 1}
    state.goal_state = {"目标重估": 1}
    save_growth_state(state, data_root)

    storage = MemoryStorage()
    spy = _SpyProvider("内心独白：我戒心更重\n言行：我审视周遭\n")
    agent = CharacterAgent(
        "b", storage=storage, runtime_config={}, characters_config={}, data_root=data_root,
    )
    ctx = build_turn_context(
        scope_id="capital", time="春", place="京城", present_character_ids=["b"],
        shared_story_snippet="",
    )
    import unittest.mock as mock
    with mock.patch("src.llm.get_llm_provider", return_value=spy):
        out = agent.turn(ctx)
    prompt = spy.calls[0]
    # 成长状态注入该角色自身五维快照；空模板时不注入
    assert "【成长状态】" in prompt
    assert "警惕" in prompt
    assert "目标重估" in prompt
    # 不应把其他无关维度的空展示带出
    assert "能力（power_state）" not in prompt
    assert out.dialogue_action.startswith("我审视周遭")


def test_character_agent_omits_growth_when_no_state_file(tmp_path):
    from src.runtime.storage import MemoryStorage

    data_root = tmp_path / "novel"
    storage = MemoryStorage()
    spy = _SpyProvider("内心独白：一切如常\n言行：我点头\n")
    agent = CharacterAgent(
        "b", storage=storage, runtime_config={}, characters_config={}, data_root=data_root,
    )
    ctx = build_turn_context(
        scope_id="capital", time="春", place="京城", present_character_ids=["b"],
        shared_story_snippet="",
    )
    import unittest.mock as mock
    with mock.patch("src.llm.get_llm_provider", return_value=spy):
        agent.turn(ctx)
    prompt = spy.calls[0]
    assert "【成长状态】" not in prompt


def test_format_present_growth_snippet_aggregates_only_nonempty(tmp_path):
    from src.runtime.character_growth import (
        default_growth_state, format_present_growth_snippet, save_growth_state,
    )

    data_root = tmp_path / "novel"
    chars = {"characters": [{"id": "a", "name": "甲"}, {"id": "b", "name": "乙"}, {"id": "c", "name": "丙"}]}
    st = default_growth_state("a")
    st.mind_state = {"警惕": 2}
    save_growth_state(st, data_root)          # a 有状态
    # b/c 无状态文件
    snippet = format_present_growth_snippet(data_root, chars, ["b", "c"])
    assert snippet == ""                        # 在场角色全无成长 → 空串
    snippet2 = format_present_growth_snippet(data_root, chars, ["a", "b"])
    assert "在场角色成长状态" in snippet2
    assert "甲（a）" in snippet2
    assert "警惕" in snippet2
    assert "乙（b）" not in snippet2            # b 无状态不出现在聚合里


def test_scope_agent_injects_present_growth_snippet():
    from src.agents.world.agent import _build_scope_prompt
    from src.context import build_turn_context

    ctx = build_turn_context(
        scope_id="capital", time="春", place="京城", present_character_ids=["a", "b"],
        shared_story_snippet="",
        present_growth_snippet="【在场角色成长状态】\n- 甲（a）：\n心理（mind_state）：警惕=2",
    )
    prompt = _build_scope_prompt("capital", {"name": "京城"}, "（无事件）", ctx)
    assert "在场角色成长状态" in prompt
    assert "警惕" in prompt


def test_scope_agent_omits_growth_when_empty():
    from src.agents.world.agent import _build_scope_prompt
    from src.context import build_turn_context

    ctx = build_turn_context(
        scope_id="capital", time="春", place="京城", present_character_ids=["a"],
        shared_story_snippet="", present_growth_snippet="",
    )
    prompt = _build_scope_prompt("capital", {"name": "京城"}, "（无事件）", ctx)
    assert "在场角色成长状态" not in prompt