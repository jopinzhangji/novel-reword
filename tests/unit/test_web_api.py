"""G4b Web API（FastAPI 薄包装于 src/workbench/）：全端点 JSON 断言 + 写口落盘。

无 fastapi 环境时整模块跳过（importorskip），核心 pytest 不受影响（船身不破）。
"""
import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from web.api.app import create_app  # noqa: E402
from tests.unit.workbench_support import (  # noqa: E402
    make_project,
    write_growth,
    write_index,
    write_off_screen,
    write_outline,
    write_scope_event,
)


@pytest.fixture()
def project(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha", "beta"))
    write_index(proj, ("alpha", "beta"))
    write_outline(roots["alpha"])
    write_scope_event(roots["alpha"], "sc1", 1, ["苏A", "李B"], "并肩")
    write_scope_event(roots["alpha"], "sc1", 2, ["李B"], "密谋")
    write_growth(roots["alpha"], "苏A", {"power_state": {"突破契机": 1}}, [{"rule": "突破", "turn": 1}])
    write_off_screen(roots["alpha"], "苏A", [{"summary": "查叛徒", "consumed": False}])
    return create_app(proj)


@pytest.fixture()
def client(project):
    return TestClient(project)


def test_list_novels(client):
    items = client.get("/api/novels").json()
    assert [i["slug"] for i in items] == ["alpha", "beta"]
    assert items[0]["edge_count"] is not None


def test_summary(client):
    r = client.get("/api/novels/alpha/summary").json()
    assert r["outline_pointer"]["had_any_beat"] is True
    assert r["outline_pointer"]["turns_in_beat"] == 2


def test_graph_full_ego_pair(client):
    g = client.get("/api/novels/alpha/graph").json()
    assert "nodes" in g and "edges" in g
    ego = client.get("/api/novels/alpha/graph/ego", params={"center": "苏A"}).json()
    assert ego["center"] == "苏A" and ego["hops"] == 2
    p = client.get("/api/novels/alpha/graph/pair", params={"a": "苏A", "b": "李B"}).json()
    assert "relation" in p and "change_log" in p


def test_characters_index_and_detail(client):
    idx = client.get("/api/novels/alpha/characters").json()
    assert any(c["id"] == "苏A" for c in idx)
    d = client.get("/api/novels/alpha/characters/%E8%8B%8FA").json()  # 苏A
    assert d["growth"]["power_state"] == {"突破契机": 1}
    assert "view" in d and "memories_l1" in d and "off_screen_threads" in d
    v = client.get("/api/novels/alpha/characters/%E8%8B%8FA/view").json()
    assert v["total_events"] == 2 and v["known"] == 1 and v["unknown"] == 1


def test_outline_and_progress(client):
    o = client.get("/api/novels/alpha/outline").json()
    assert o["present"] is True and len(o["chapters"]) == 2
    p = client.get("/api/novels/alpha/progress").json()
    assert p["current"]["chapter_id"] == "ch1" and p["current"]["beat_id"] == "b1"
    absent = client.get("/api/novels/beta/progress").json()
    assert absent["present"] is False


def test_console_read_write_feature(client):
    s = client.get("/api/novels/alpha/console").json()
    assert s["features"]["flags"]["info_view"] is False
    r = client.patch("/api/novels/alpha/features", json={"features": {"info_view": True}}).json()
    assert r["flags"]["info_view"] is True
    s2 = client.get("/api/novels/alpha/console").json()
    assert s2["features"]["persisted_override"]["info_view"] is True


def test_console_switch_lens(client):
    r = client.put("/api/novels/alpha/protagonist", json={"target_id": "李B"}).json()
    assert r["protagonist_id"] == "李B"
    s = client.get("/api/novels/alpha/console").json()
    assert s["lens"]["is_override"] is True and s["lens"]["protagonist_id"] == "李B"


def test_drafts_write_list_promote(client):
    w = client.post("/api/novels/alpha/drafts", json={"chapter_id": "ch1", "lens_id": "李B", "body": "正文"}).json()
    assert w["status"] == "draft"
    dr = client.get("/api/novels/alpha/drafts").json()
    assert any(d["lens_id"] == "李B" for d in dr)
    p = client.post("/api/novels/alpha/drafts/promote", json={"chapter_id": "ch1", "lens_id": "李B"}).json()
    assert p["promoted"] is True


def test_unknown_slug_404(client):
    assert client.get("/api/novels/nope/summary").status_code == 404
    assert client.get("/api/novels/nope/graph").status_code == 404


def test_static_root_served(project):
    c = TestClient(project)
    r = c.get("/")
    assert r.status_code == 200 and "Novel-Data 工作台" in r.text