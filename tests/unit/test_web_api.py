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

def test_rename_via_http(project, client):
    # 建 current_novel 指针指向 alpha，验证 rename 更新指针 + 落盘
    import yaml
    from pathlib import Path

    # project.state.WORKBENCH_ROOT -> tmp_path（make_project 的项目根）
    root = project.state.WORKBENCH_ROOT
    from tests.unit.workbench_support import write_yaml

    write_yaml(
        Path(root) / "config" / "current_novel.yaml",
        {"slug": "alpha", "title": "旧名", "root": str(Path(root) / "data" / "novels" / "alpha")},
    )
    r = client.patch("/api/novels/alpha/rename", json={"title": "夜行灵官"})
    assert r.status_code == 200
    data = r.json()
    assert data["slug"] == "夜行灵官" and data["title"] == "夜行灵官"
    # 指数刷新：旧 slug alpha 移除、新 slug 追加到末端（beta 保留）
    got = [i["slug"] for i in client.get("/api/novels").json()]
    assert "alpha" not in got and "夜行灵官" in got and "beta" in got
    assert got == ["beta", "夜行灵官"]  # 旧行移除、新行追加到末端
    cur = yaml.safe_load((Path(root) / "config" / "current_novel.yaml").read_text(encoding="utf-8"))
    assert cur["slug"] == "夜行灵官" and cur["provisional"] is False


def test_rename_empty_via_http_400(project, client):
    r = client.patch("/api/novels/alpha/rename", json={"title": "  "})
    assert r.status_code == 400


def test_discussion_and_synopsis_via_http(project, client):
    # §6.9 GET /discussion 确定性快照 + PATCH /synopsis 落 meta
    d = client.get("/api/novels/alpha/discussion").json()
    assert d["synopsis"] == ""          # make_project 无 synopsis
    assert "world" in d and "settings" in d and "discussion_summary" in d
    assert d["phase"]["phase"] is None
    # 写 synopsis
    r = client.patch("/api/novels/alpha/synopsis", json={"text": "近未来火星殖民官场"}).json()
    assert r["synopsis"] == "近未来火星殖民官场"
    d2 = client.get("/api/novels/alpha/discussion").json()
    assert d2["synopsis"] == "近未来火星殖民官场"
    # 空简介拒绝
    assert client.patch("/api/novels/alpha/synopsis", json={"text": "  "}).status_code == 400
