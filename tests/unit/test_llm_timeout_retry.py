"""传输层超时重试与用户确认（设定讨论等）。"""
import pytest

from src.llm.call import (
    LLMTransportTimeoutExhausted,
    _is_llm_transport_timeout,
    llm_invoke_with_transport_timeout_retry,
)


def test_is_llm_transport_timeout_httpx_read():
    httpx = pytest.importorskip("httpx")
    assert _is_llm_transport_timeout(httpx.ReadTimeout("read timed out")) is True


def test_llm_invoke_silent_retries_then_success():
    httpx = pytest.importorskip("httpx")
    calls = []

    def op():
        calls.append(1)
        if len(calls) < 3:
            raise httpx.ReadTimeout("slow")
        return "done"

    out = llm_invoke_with_transport_timeout_retry(
        op,
        input_fn=None,
        timeout_retry_budget=3,
        action_label="test",
    )
    assert out == "done"
    assert len(calls) == 3


def test_llm_invoke_prompt_user_abort():
    httpx = pytest.importorskip("httpx")

    def op():
        raise httpx.ReadTimeout("slow")

    prompts = []

    def input_fn(prompt: str) -> str:
        prompts.append(prompt)
        return "n"

    with pytest.raises(LLMTransportTimeoutExhausted, match="放弃"):
        llm_invoke_with_transport_timeout_retry(
            op,
            input_fn=input_fn,
            timeout_retry_budget=3,
            action_label="test",
        )

    assert len(prompts) == 1
    assert "超时" in prompts[0]
    assert "重试" in prompts[0]


def test_llm_invoke_non_timeout_raises():
    def op():
        raise ValueError("not a timeout")

    with pytest.raises(ValueError, match="not a timeout"):
        llm_invoke_with_transport_timeout_retry(
            op,
            input_fn=lambda _: "y",
            timeout_retry_budget=3,
            action_label="test",
        )
