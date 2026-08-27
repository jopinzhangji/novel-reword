"""
LLM 调用统一入口（含交互式重试）。

设计原则：
- Provider 层可配置底层 HTTP/SDK 超时与自动重试；
- 本层负责传输层超时后「再问作者是否继续」与重试计数，避免业务层重复实现。
"""
from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

T = TypeVar("T")

_ll = logging.getLogger(__name__)


class LLMTransportTimeoutExhausted(Exception):
    """在「读/连接超时」链上用尽重试预算后仍失败。"""


def _is_llm_transport_timeout(exc: BaseException) -> bool:
    """判断是否为底层 HTTP/socket 等非业务类超时。"""
    try:
        import httpx
    except ImportError:
        httpx = None  # type: ignore[assignment]

    timeout_types: tuple[type, ...] = ()
    if httpx is not None:
        timeout_types = getattr(httpx, "TimeoutException", ())
        tx = (
            getattr(httpx, "ReadTimeout", ()),
            getattr(httpx, "ConnectTimeout", ()),
            getattr(httpx, "WriteTimeout", ()),
            getattr(httpx, "PoolTimeout", ()),
        )
        timeout_types = tuple(t for t in tx if isinstance(t, type))

    api_timeout_type: tuple[type, ...] = ()
    try:
        from openai import APITimeoutError

        api_timeout_type = (APITimeoutError,)
    except Exception:
        api_timeout_type = ()

    import socket

    seen: set[int] = set()
    chain: list[BaseException] = []

    # __cause__ 链（含 PEP 692 多层）
    e: BaseException | None = exc
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        chain.append(e)
        e = e.__cause__

    for e in chain:
        if api_timeout_type and isinstance(e, api_timeout_type):
            return True
        if isinstance(e, (TimeoutError, socket.timeout)):
            return True
        for t in timeout_types:
            if isinstance(e, t):
                return True

    return False


def llm_invoke_with_transport_timeout_retry(
    operation: Callable[[], T],
    *,
    input_fn: Callable[[str], str] | None = None,
    log: Any = None,
    timeout_retry_budget: int = 3,
    action_label: str = "LLM 调用",
) -> T:
    """
    执行 operation；若异常为传输层超时，最多再经历 ``timeout_retry_budget`` 次失败
    （即共 ``1 + timeout_retry_budget`` 次超时）后放弃。

    - ``input_fn`` 非空时：每次超时后提示作者是否继续（y/回车=再试，n=放弃）；
    - ``input_fn`` 为空时：直接重试直至耗尽（单测/非交互流水线）。
    非超时类异常原样上抛；``LLMQuotaExhaustedError`` 原样上抛。
    """
    try:
        from src.llm.base import LLMQuotaExhaustedError
    except Exception:
        LLMQuotaExhaustedError = type(None)  # type: ignore[misc, assignment]

    logger = log or _ll
    budget = max(0, int(timeout_retry_budget))
    max_failures = 1 + budget
    timeouts_seen = 0
    last_err: BaseException | None = None

    while True:
        try:
            return operation()
        except Exception as e:
            if LLMQuotaExhaustedError is not type(None) and isinstance(
                e, LLMQuotaExhaustedError
            ):
                raise
            if not _is_llm_transport_timeout(e):
                raise
            last_err = e
            timeouts_seen += 1
            logger.warning(
                "%s 传输超时（第 %s/%s 次）：%s",
                action_label,
                timeouts_seen,
                max_failures,
                e,
            )
            if timeouts_seen >= max_failures:
                raise LLMTransportTimeoutExhausted(
                    f"{action_label}在 {max_failures} 次超时后仍失败"
                ) from last_err
            if input_fn is not None:
                remaining = max_failures - timeouts_seen
                prompt = (
                    f"【{action_label}】请求超时（第 {timeouts_seen} 次，还可再试至多 {remaining} 次）。"
                    f"是否继续重试？(y/回车=是，n=否放弃)："
                )
                ans = (input_fn(prompt).strip().lower() or "y")
                if ans in ("n", "no", "否"):
                    raise LLMTransportTimeoutExhausted(
                        f"{action_label}：作者选择放弃重试"
                    ) from last_err


def call_with_user_retry(
    operation: Callable[[], T],
    *,
    input_fn: Callable[[str], str] | None = None,
    log: Any = None,
    action_name: str = "LLM 调用",
    attempts_per_round: int = 3,
) -> T:
    """
    调用 operation；单轮失败会自动重试 attempts_per_round 次。
    若仍失败，询问用户是否继续下一轮重试（默认 y）。
    """
    fn = input_fn or input
    attempts_per_round = max(1, int(attempts_per_round))

    while True:
        last_err: Exception | None = None
        for _ in range(attempts_per_round):
            try:
                return operation()
            except Exception as e:
                last_err = e
        if log:
            log.warning("%s 连续失败 %s 次：%s", action_name, attempts_per_round, last_err)
            log.info("是否继续重试%s？(y=继续, n=取消并抛错, 默认 y)", action_name)
        ans = (fn(f"继续重试{action_name}？(y/n，默认 y)：").strip().lower() or "y")
        if ans in ("n", "no", "否"):
            raise RuntimeError(f"{action_name}失败：连续重试后仍失败：{last_err}") from last_err

