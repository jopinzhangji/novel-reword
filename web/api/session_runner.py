"""G4c Session Runner：后台线程跑作者在环主流程，经 WebInputAdapter 桥接作者。

- WorkbenchSession：绑定一个 data_root（slug），持有一个 `WebInputAdapter`，
  把 `run_novel_with_author.main(input_fn=adapter.read)` 放到 daemon 线程执行。
- SessionRegistry：data_root → 活跃会话 一地对一映射；对已活跃 data_root 再建
  → 由 router 回 409（D9 §6.1 MUST 3 / §5.5：避免 CLI 与 Web 各跑一条作者在环
  循环、双写同一 data_root）。

`run_fn` 可注入（默认 = run_novel_with_author.main）：单测注入假回环，避免真 LLM；
生产走真实主流程，作者输入经 `input_fn=adapter.read` 全部桥到前端。
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from pathlib import Path
from typing import Callable

from src.author_harness.workbench_ingress import WebInputAdapter

RunFn = Callable[..., object]

_MAX_STREAM_LINES = 300  # 会话期缓冲的引擎日志尾部行数上限


class _StreamTailHandler(logging.Handler):
    """只读日志尾部缓冲：把日志行压入定长 deque，供 `state()["stream"]` 展示。

    挂到**根 logger**（覆盖 `src.*` 各模块 `logging.getLogger(__name__)` 的祖传传播路径），
    纯内存、无磁盘；会话结束由 `WorkbenchSession` 负责移除（防泄漏）。
    """

    def __init__(self, max_lines: int = _MAX_STREAM_LINES) -> None:
        super().__init__(level=logging.INFO)
        self._lines: deque[str] = deque(maxlen=max_lines)
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._lines.append(self.format(record))
        except Exception:  # noqa: BLE001 — 观测 handler 绝不让日志自身抛错
            self.handleError(record)

    def lines(self) -> list[str]:
        return list(self._lines)


def _default_run_fn() -> RunFn:
    from run_novel_with_author import main

    return main


class WorkbenchSession:
    """一本 data_root 上的一个作者在环会话。"""

    def __init__(self, *, data_root: str | Path, run_fn: RunFn | None = None) -> None:
        self.data_root = Path(data_root)
        self.slug = self.data_root.name or "novel"
        self.adapter = WebInputAdapter()
        self.run_fn = run_fn or _default_run_fn()
        self.status = "created"  # created | running | done | failed | aborted
        self.error: str | None = None
        self._thread: threading.Thread | None = None
        # GG-W #6：会话期挂到根 logger 的日志尾部缓冲（只读观测，见 _StreamTailHandler）
        self._stream_tail = _StreamTailHandler()
        self._prev_root_level: int | None = None

    def _attach_logger(self) -> None:
        """挂根 logger 捕获引擎 INFO 日志尾部；根默认 WARNING 会滤掉 INFO，故临时抬到 INFO，
        会话结束由 `_detach_logger` 还原。仅会话期内生效（显式开始 Session 才触发，default 不破）。"""
        root = logging.getLogger()
        self._prev_root_level = root.level
        root.setLevel(logging.INFO)
        root.addHandler(self._stream_tail)

    def _detach_logger(self) -> None:
        root = logging.getLogger()
        root.removeHandler(self._stream_tail)  # 幂等：abort 与 _run_guard finally 可能都调
        if self._prev_root_level is not None:
            root.setLevel(self._prev_root_level)
            self._prev_root_level = None

    def start(self) -> None:
        if self.status in ("running", "done", "failed", "aborted"):
            return
        self.status = "running"
        self._attach_logger()
        self._thread = threading.Thread(
            target=self._run_guard, name=f"wbench-{self.slug}", daemon=True
        )
        self._thread.start()

    def _run_guard(self) -> None:
        try:
            self.run_fn(input_fn=self.adapter.read)
            if self.status == "running":
                self.status = "done"
        except Exception as e:  # noqa: BLE001 — 会话级兜底，错误经 state() 可观测
            if self.status != "aborted":
                self.status = "failed"
                self.error = str(e)
                # 让失败也进入终端日志尾部（根 logger 仍在挂载 → 被 _StreamTailHandler 捕获），
                # 否则崩溃只见 status=failed、终端无任何打印（D13 §6.7 控制台终端可观性）。
                logging.getLogger("web.api.session_runner").error(
                    "作者在环会话失败: %s", e
                )
        finally:
            self._detach_logger()

    # -- Web 线程入口 --
    def submit(self, text: str) -> None:
        self.adapter.set_reply(text)

    def abort(self) -> None:
        self.adapter.abort()
        self._detach_logger()  # abort 即刻解除阻塞输入；日志尾部一并收口
        if self.status == "running":
            self.status = "aborted"

    # -- 快照（只读）--
    def state(self) -> dict:
        return {
            "slug": self.slug,
            "data_root": str(self.data_root),
            "status": self.status,
            "pending_prompt": self.adapter.pending_prompt,
            "error": self.error,
            # GG-W #6：会话期缓冲的引擎日志尾部（只读观测；未捕获实时流式）
            "stream": self._stream_tail.lines(),
        }


class SessionRegistry:
    """data_root → 活跃会话 一地对一映射（并发安全）。"""

    def __init__(self) -> None:
        self._sessions: dict[str, WorkbenchSession] = {}
        self._lock = threading.Lock()

    def create(
        self, key: str, *, data_root: str | Path | None = None, run_fn: RunFn | None = None
    ) -> tuple[WorkbenchSession, bool]:
        """建（或复用）一个会话。`fresh=False` 表示该 key 已有活跃会话。

        已 done/failed/aborted 的旧会话会被替换重建；正在 running 的返回 False，
        由调用方决定回 409。
        """
        key = str(key)
        with self._lock:
            cur = self._sessions.get(key)
            if cur is not None and cur.status == "running":
                return cur, False
        session = WorkbenchSession(
            data_root=data_root or key, run_fn=run_fn
        )
        with self._lock:
            self._sessions[key] = session
        return session, True

    def get(self, key: str) -> WorkbenchSession | None:
        with self._lock:
            return self._sessions.get(str(key))

    def remove(self, key: str) -> WorkbenchSession | None:
        key = str(key)
        with self._lock:
            session = self._sessions.pop(key, None)
        if session is not None:
            session.abort()
        return session