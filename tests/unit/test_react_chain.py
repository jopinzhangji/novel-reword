"""U-6 回合内二次反应/对话链：react_chain 开关、两波合并、私有内心不泄。"""
import re

from src.agents.character import CharacterAgent
from src.agents.world import ScopeAgent
from src.orchestrator import Orchestrator
from src.runtime.storage import MemoryStorage


def _make_orchestrator(runtime, chars):
    return Orchestrator(
        storage=MemoryStorage(),
        character_agents={
            cid: CharacterAgent(cid, runtime_config=runtime, characters_config=chars)
            for cid in ["a", "b"]
        },
        scope_agents={"capital": ScopeAgent("capital")},
        world_config={},
        runtime_config=runtime,
        characters_config=chars,
        data_root=None,
    )


def _chars():
    return {"characters": [
        {"id": "a", "name": "甲"},
        {"id": "b", "name": "乙"},
    ]}


_CHAR_RE = re.compile(r"（([a-z]+)）")


class _PhaseSpy:
    """按被调用角色名与阶段返回不同 LLM 文本：区分先发批（wave1）与二次反应（react）。"""

    def __init__(self):
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        name = self._name(prompt)
        if "你又听到在场其他角色的公开言行" in prompt:  # react 二次批
            return f"内心独白：我回应对方的话\n言行：我向{name}郑重回一句\n"
        # wave1 先发批：甲（a）说私密内心，乙（b）公开应声（私有内心不应对他人可见）
        if name == "甲":
            return "内心独白：我的私密计划是暗算对手\n言行：我宣称要整顿秩序\n"
        return "内心独白：我观察局面\n言行：我应声观望\n"

    @staticmethod
    def _name(prompt):
        # 首行形如「你是甲，角色。」(wave1) 或「你是甲（a）。」(react)
        m = re.match(r"你是([^，。（]*)", prompt)
        return m.group(1) if m else "?"


def _react_prompts(spy):
    return [p for p in spy.calls if "你又听到在场其他角色的公开言行" in p]


def test_react_chain_off_by_default_no_second_wave():
    runtime = {"agents": {"characters": {"enabled_ids": ["a", "b"]}}}  # 无 react_chain → 默认关
    chars = _chars()
    spy = _PhaseSpy()
    import unittest.mock as mock
    with mock.patch("src.llm.get_llm_provider", return_value=spy):
        orch = _make_orchestrator(runtime, chars)
        result = orch.run_one_turn(
            scope_id="capital", time="春", place="京城",
            present_character_ids=["a", "b"], auto_write=False,
        )
    assert _react_prompts(spy) == []  # 未触发二波
    assert result.character_outputs["a"].dialogue_action == "我宣称要整顿秩序"
    assert result.character_outputs["a"].reaction == ""


def test_react_chain_on_merges_reaction():
    runtime = {"agents": {"characters": {"enabled_ids": ["a", "b"], "react_chain": True}}}
    chars = _chars()
    spy = _PhaseSpy()
    import unittest.mock as mock
    with mock.patch("src.llm.get_llm_provider", return_value=spy):
        orch = _make_orchestrator(runtime, chars)
        result = orch.run_one_turn(
            scope_id="capital", time="春", place="京城",
            present_character_ids=["a", "b"], auto_write=False,
        )
    assert len(_react_prompts(spy)) == 2  # a、b 各一次二次批
    wave1 = {"a": "我宣称要整顿秩序", "b": "我应声观望"}
    for cid in ["a", "b"]:
        out = result.character_outputs[cid]
        assert wave1[cid] in out.dialogue_action   # 首波仍在
        assert "郑重回一句" in out.dialogue_action  # 反应并入
        assert out.reaction  # reaction 字段已观测


def test_react_chain_does_not_leak_peer_inner_monologue():
    runtime = {"agents": {"characters": {"enabled_ids": ["a", "b"], "react_chain": True}}}
    chars = _chars()
    spy = _PhaseSpy()
    import unittest.mock as mock
    with mock.patch("src.llm.get_llm_provider", return_value=spy):
        orch = _make_orchestrator(runtime, chars)
        orch.run_one_turn(
            scope_id="capital", time="春", place="京城",
            present_character_ids=["a", "b"], auto_write=False,
        )
    # A 的私有内心只出现在其自身 wave1 prompt（或 A 自身的 react prompt），
    # 但绝不应出现在 B 的二次批 peers_snippet 中（B 只应对 A 的公开言行）。
    for s in spy.calls:
        if "你又听到在场其他角色的公开言行" in s and "乙（b）" in s:
            assert "我的私密计划" not in s


def test_react_chain_single_present_character_no_loop():
    runtime = {"agents": {"characters": {"enabled_ids": ["a", "b"], "react_chain": True}}}
    chars = _chars()
    spy = _PhaseSpy()
    import unittest.mock as mock
    with mock.patch("src.llm.get_llm_provider", return_value=spy):
        orch = _make_orchestrator(runtime, chars)
        result = orch.run_one_turn(
            scope_id="capital", time="春", place="京城",
            present_character_ids=["a"], auto_write=False,
        )
    assert len(result.character_outputs) == 1
    assert _react_prompts(spy) == []  # 仅 1 个在场 → 不触发二波