"""G4c 作者在环传输层：Web 作者输入适配器 + CLI 仅日志入口（互斥模式）。

D9 §5.5/§8.4/§10 + D13 §6.1：当 `author_workbench.enabled=true` 时，作者的
一切交互只在前端进行，**终端不读 stdin、不打印作者菜单，仅日志**。

本模块提供两个「作者输入函数」，与 `AuthorSession.read_line(prompt)` 及
`run_novel_with_author.main(input_fn=...)` 的调用约定完全兼容（`Callable[[str],str]`）：

- WebInputAdapter：**阻塞式**桥——作者在环线程（回合引擎）调用 `read(prompt)`
  时设当前待答 prompt 并阻塞，直到 Web 端 `POST /session/{key}/reply` 经
  `set_reply(text)` 喂入答案唤醒；前端轮询 `pending_prompt` 显示问题。
- LogOnlyAuthorIngress：**永不读 stdin、永不阻塞**——任何 prompt 立即返回空串
  （沿用「回车继续 / 默认分支」语义），并把该作者交互点以 `[作者在环] AWAIT_AUTHOR`
  日志对外可观测。用于 `enabled=true` 且由 CLI 直跑（未接前端）时的互斥止血。

两者均为确定性、无 LLM、线程安全；`abort()` 让被阻塞的 read 立即返回。
"""
from __future__ import annotations

import queue
import threading
from typing import Callable

PromptFn = Callable[[str], str]


class WebInputAdapter:
    """把 `AuthorSession.read_line(prompt)` 桥接到 pending_prompt → POST /reply。

    线程模型：
    - 引擎线程调用 ``read(prompt)``：记录 pending → 阻塞在内部队列，直到收到回复。
    - Web 线程调用 ``set_reply(text)``：向队列塞答案，唤醒被阻塞的 read。
    - 任何一方可调用 ``abort()``：塞 None，令所有阻塞 read 立即返回隐含默认串。
    """

    def __init__(self, implied: str = "") -> None:
        self._q: queue.Queue[str | None] = queue.Queue()
        self._lock = threading.Lock()
        self._pending: str | None = None
        self._implied = implied

    # -- 传输方向：引擎线程调用（阻塞作者在环）--
    def read(self, prompt: str) -> str:
        with self._lock:
            self._pending = prompt
        try:
            item = self._q.get()
        except (EOFError, KeyboardInterrupt):
            return self._implied
        finally:
            with self._lock:
                self._pending = None
        return self._implied if item is None else item

    # -- 传输方向：Web 线程调用（喂答案 / 放弃）--
    def set_reply(self, text: str) -> None:
        self._q.put(text)

    def abort(self) -> None:
        self._q.put(None)

    @property
    def pending_prompt(self) -> str | None:
        with self._lock:
            return self._pending

    @property
    def is_awaiting(self) -> bool:
        with self._lock:
            return self._pending is not None

    def __call__(self, prompt: str) -> str:
        return self.read(prompt)


class LogOnlyAuthorIngress:
    """终端仅日志、不读 stdin 的作者输入（互斥模式 CLI 侧）。

    任何 ``read(prompt)`` 立即返回空串，并把该 author 交互点以
    ``[作者在环] AWAIT_AUTHOR`` 日志对外可观测——配合前端 Session Runner
    承担真实交互，避免 CLI 与 Web 各跑一条作者在环循环、造成双写 data_root。
    """

    _implied = ""

    def read(self, prompt: str) -> str:
        import logging

        logging.getLogger(__name__).info("[作者在环] AWAIT_AUTHOR（互斥：前端作答）: %s", prompt)
        return self._implied

    def __call__(self, prompt: str) -> str:
        return self.read(prompt)