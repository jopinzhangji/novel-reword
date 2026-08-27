import pytest

from src.llm.call import call_with_user_retry


class _Log:
    def warning(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None


def test_call_with_user_retry_success_after_retries():
    state = {"n": 0}

    def _op():
        state["n"] += 1
        if state["n"] < 3:
            raise RuntimeError("tmp")
        return "ok"

    out = call_with_user_retry(_op, input_fn=lambda _: "y", log=_Log(), attempts_per_round=3)
    assert out == "ok"
    assert state["n"] == 3


def test_call_with_user_retry_ask_then_abort():
    state = {"n": 0}

    def _op():
        state["n"] += 1
        raise RuntimeError("err")

    with pytest.raises(RuntimeError, match="连续重试后仍失败"):
        call_with_user_retry(
            _op,
            input_fn=lambda _: "n",
            log=_Log(),
            action_name="书名生成",
            attempts_per_round=2,
        )
    assert state["n"] == 2

