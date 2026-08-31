"""G4c Session Router / Runner 端到端：建会话 → pending_prompt 轮询 → reply 推进 → 409 互斥。

用假回环 `fake_run`（隔离 LLM）：它先读两个提示并记录答案，模拟真实作者在环
`run_novel_with_author.main(input_fn=adapter.read)` 的两次 AWAIT_AUTHOR 交互。
无 fastapi 环境时整模块跳过（importorskip），船身不破。
"""
import threading
import time

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from web.api.app import create_app  # noqa: E402
from web.api.session_runner import SessionRegistry  # noqa: E402


def _until(cond, timeout=8.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond():
            return True
        time.sleep(0.02)
    return False


def _make_fake_run():
    """返回 (run_fn, store)：run_fn 读两个提示（Q1/Q2）并把答案记进 store。"""
    store = {"a1": None, "a2": None}
    lock = threading.Lock()

    def run(input_fn=None):
        store["a1"] = input_fn("Q1 请审定本章")
        store["a2"] = input_fn("Q2 请审定记忆")
        with lock:
            store["done"] = True

    def done():
        with lock:
            return store.get("done", False)

    run.__store__ = store  # type: ignore[attr-defined]
    run.__done__ = done  # type: ignore[attr-defined]
    return run, store


@pytest.fixture()
def app():
    a = create_app()
    fake, store = _make_fake_run()
    a.state.SESSION_RUN_FN = fake
    a.state.SESSION_REGISTRY = SessionRegistry()
    a._fake_store = store  # type: ignore[attr-defined]
    a._fake_done = fake.__done__  # type: ignore[attr-defined]
    return a


@pytest.fixture()
def client(app):
    return TestClient(app)


def _reply_all(client, key, answers):
    for prompt, ans in answers.items():
        assert _until(lambda: client.get(f"/api/session/{key}").json().get("pending_prompt") == prompt), \
            f"应出现待答 prompt={prompt}"
        client.post(f"/api/session/{key}/reply", json={"text": ans})


def test_session_reply_round_trip(client):
    r = client.post("/api/session", json={"slug": "tongka", "data_root": "tongka"})
    assert r.status_code == 200
    key = r.json()["key"]
    assert key == "tongka"
    assert r.json()["status"] == "running"

    _reply_all(client, key, {"Q1 请审定本章": "同意", "Q2 请审定记忆": "接受"})

    assert _until(client.app._fake_done)
    s = client.get(f"/api/session/{key}").json()
    assert s["status"] == "done"
    assert client.app._fake_store["a1"] == "同意"
    assert client.app._fake_store["a2"] == "接受"
    assert s["pending_prompt"] is None


def test_mutual_exclusion_409_on_active_data_root(client):
    # 建立首个会话（阻塞在 Q1，保持 running）
    r1 = client.post("/api/session", json={"slug": "one", "data_root": "one"})
    assert r1.status_code == 200
    key = r1.json()["key"]
    assert _until(lambda: client.get(f"/api/session/{key}").json().get("pending_prompt") == "Q1 请审定本章")

    # 同一 data_root 再建 → 409（互斥：避免双跑作者在环循环 / 双写 data_root）
    r2 = client.post("/api/session", json={"slug": "one", "data_root": "one"})
    assert r2.status_code == 409

    # 清理：回复或删除释放锁
    client.post(f"/api/session/{key}/reply", json={"text": "同意"})
    client.post(f"/api/session/{key}/reply", json={"text": "接受"})
    assert _until(client.app._fake_done)


def test_unknown_key_404(client):
    assert client.get("/api/session/nope").status_code == 404
    assert client.post("/api/session/nope/reply", json={"text": "x"}).status_code == 404
    assert client.delete("/api/session/nope").status_code == 404


def test_abort_unblocks_and_releases(client):
    r = client.post("/api/session", json={"slug": "ab", "data_root": "ab"})
    key = r.json()["key"]
    assert _until(lambda: client.get(f"/api/session/{key}").json().get("pending_prompt") == "Q1 请审定本章")
    # abort 令被阻塞 read 立即返回空串（不挂死），data_root 锁释放 → 可再建
    ar = client.post(f"/api/session/{key}/abort").json()
    assert ar["status"] in ("aborted", "running")
    d = client.delete(f"/api/session/{key}").json()
    assert d["deleted"] is True
    # 释放后同 data_root 可重建
    assert client.post("/api/session", json={"slug": "ab", "data_root": "ab"}).status_code == 200