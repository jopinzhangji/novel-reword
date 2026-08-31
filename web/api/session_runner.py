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

import threading
from pathlib import Path
from typing import Callable

from src.author_harness.workbench_ingress import WebInputAdapter

RunFn = Callable[..., object]


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

    def start(self) -> None:
        if self.status in ("running", "done", "failed", "aborted"):
            return
        self.status = "running"
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

    # -- Web 线程入口 --
    def submit(self, text: str) -> None:
        self.adapter.set_reply(text)

    def abort(self) -> None:
        self.adapter.abort()
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