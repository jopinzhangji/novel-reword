"""GG-W #6：WorkbenchSession 会话期日志尾部缓冲（_StreamTailHandler）。

- 挂根 logger 捕获引擎 INFO 日志尾部（`state()["stream"]`），会话结束/中止即移除 handler、
  并把临时抬起的根日志级别还原。纯 session_runner，不依赖 fastapi。
"""
import logging
import time

from web.api.session_runner import WorkbenchSession


def _fake_run(lines):
    def run(input_fn=None):
        lg = logging.getLogger("novel.test")
        for ln in lines:
            lg.info(ln)
    return run


def test_session_captures_stream_and_detaches():
    root_level = logging.getLogger().level
    s = WorkbenchSession(data_root="x", run_fn=_fake_run(["引擎: 启动回合 1", "引擎: 写回完成"]))
    s.start()
    s._thread.join(timeout=5)
    st = s.state()
    assert st["status"] == "done", st
    joined = "\n".join(st["stream"])
    assert "引擎: 启动回合 1" in joined and "引擎: 写回完成" in joined, st["stream"]
    # 结束后 handler 移除、根级别还原（default 不破）
    assert s._stream_tail not in logging.getLogger().handlers
    assert logging.getLogger().level == root_level


def test_abort_detaches_and_no_session_no_handler():
    def slow(input_fn=None):
        time.sleep(5)

    s = WorkbenchSession(data_root="y", run_fn=slow)
    s.start()
    s.abort()
    # abort 即刻 detach：handler 不再挂根 logger
    assert s._stream_tail not in logging.getLogger().handlers
    assert s.status == "aborted"


def test_no_session_attaches_nothing():
    before = logging.getLogger().level
    # 构造后未 start：不挂 handler、不抬级别
    s = WorkbenchSession(data_root="z", run_fn=lambda input_fn=None: None)
    assert s._stream_tail not in logging.getLogger().handlers
    assert logging.getLogger().level == before