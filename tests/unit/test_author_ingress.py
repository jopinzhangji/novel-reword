"""G4c 作者在环传输层单测：WebInputAdapter（阻塞读/回喂/放弃）+ LogOnlyAuthorIngress。

纯确定性、无 LLM、无 Web 依赖——对应 D9 §8.4/§10 + D13 §6.1「互斥模式」的桥接层。
"""
import threading

import pytest

from src.author_harness.workbench_ingress import LogOnlyAuthorIngress, WebInputAdapter


def _spawn_read(adapter: WebInputAdapter, prompt: str, out: dict, key: str):
    out[key] = adapter.read(prompt)


def test_web_adapter_pending_then_reply_round_trip():
    adapter = WebInputAdapter()
    out = {}
    t = threading.Thread(target=_spawn_read, args=(adapter, "请审定本章？", out, "a1"))
    t.start()
    assert adapter.pending_prompt == "请审定本章？"
    assert adapter.is_awaiting is True
    adapter.set_reply("同意")
    t.join(timeout=5)
    assert not t.is_alive()
    assert out["a1"] == "同意"
    assert adapter.pending_prompt is None


def test_web_adapter_reply_before_read_is_consumed_later():
    adapter = WebInputAdapter()
    adapter.set_reply("预填")
    assert adapter.read("任意提示") == "预填"


def test_web_adapter_abort_unblocks_with_implied():
    adapter = WebInputAdapter(implied="")
    out = {}
    t = threading.Thread(target=_spawn_read, args=(adapter, "Q", out, "a"))
    t.start()
    # 等待 read 真正进入阻塞
    while adapter.pending_prompt is None:
        pass
    adapter.abort()
    t.join(timeout=5)
    assert not t.is_alive()
    assert out["a"] == ""


def test_web_adapter_callable_usable_as_input_fn():
    adapter = WebInputAdapter()
    adapter.set_reply("y")
    assert adapter("审定？") == "y"


def test_log_only_ingress_never_blocks_returns_empty():
    ingress = LogOnlyAuthorIngress()
    # 立即可返回，不阻塞，返回空串（「回车继续 / 默认分支」语义）
    assert ingress.read("请审定本章？") == ""
    assert ingress("切换镜头到？") == ""


@pytest.mark.parametrize("implied", ["", "next"])
def test_web_adapter_implied_used_on_abort(implied):
    adapter = WebInputAdapter(implied=implied)
    adapter.abort()
    assert adapter.read("Q") == implied