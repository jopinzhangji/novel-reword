"""GG5 /system Web 端点（FastAPI TestClient）：GET/PATCH round-trip + LLM 只读。

无 fastapi 环境时整模块跳过（importorskip），核心 pytest 不受影响（船身不破）。
"""
import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from tests.unit.test_system import _setup  # noqa: E402
from web.api.app import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    _setup(tmp_path)
    return TestClient(create_app(tmp_path))


def test_get_system(client):
    r = client.get("/api/system")
    assert r.status_code == 200
    data = r.json()
    assert data["current_novel"]["slug"] == "alpha"
    assert data["framework"]["readonly"] is True
    assert "internet_search" in data and "workbench" in data


def test_patch_workbench_via_http(client):
    r = client.patch("/api/system", json={"author_workbench_enabled": True})
    assert r.status_code == 200
    assert r.json()["workbench"]["author_workbench_enabled"] is True
    # GET 反映
    assert client.get("/api/system").json()["workbench"]["author_workbench_enabled"] is True


def test_patch_internet_validation_400(client):
    r = client.patch("/api/system", json={"internet_search": {"max_chars": 50}})
    assert r.status_code == 400


def test_patch_empty_body_400(client):
    r = client.patch("/api/system", json={})
    assert r.status_code == 400