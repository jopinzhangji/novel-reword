"""GG6 / 远程访问与鉴权单测：可配监听 + Basic Auth 密码登录。

- load_web_settings 默认（关）与 override（config/web_api.yaml 启用）。
- verify_credentials 常量时间：正/误/未启用恒放行。
- validate_auth_settings：enabled=true 但空口令 → 抛错（不裸奔）。
- create_app：auth.enabled=false 默认不变（船身不破）；enabled=true 时 /api + 静态页全站
  401（无凭据）/ 200（正确 Basic）；写入凭据后写口可过。
无 fastapi 环境整模块跳过（importorskip），核心 pytest 不受影响。
"""
import base64

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from tests.unit.workbench_support import make_project, write_yaml  # noqa: E402
from web.api import security  # noqa: E402
from web.api.app import create_app  # noqa: E402


def _b64(u, p):
    return "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()


def _web_config(root, *, enabled=False, username="", password=""):
    write_yaml(
        root / "config" / "web_api.yaml",
        {"server": {"host": "127.0.0.1", "port": 8000},
         "auth": {"enabled": enabled, "username": username, "password": password,
                  "realm": "Novel-Data Workbench"}},
    )


@pytest.fixture()
def project(tmp_path):
    make_project(tmp_path, ("alpha",))
    return tmp_path


# --- load_web_settings / defaults ---


def test_load_web_settings_defaults(tmp_path):
    s = security.load_web_settings(tmp_path)  # 无配置文件
    assert s["server"]["host"] == "127.0.0.1" and s["server"]["port"] == 8000
    assert s["auth"]["enabled"] is False


def test_load_web_settings_override(project):
    _web_config(project, enabled=True, username="me", password="s3cret")
    s = security.load_web_settings(project)
    assert s["auth"]["enabled"] is True
    assert s["auth"]["username"] == "me"
    assert s["auth"]["password"] == "s3cret"


# --- verify_credentials / validate ---


def test_verify_disabled_always_allow(project):
    s = security.load_web_settings(project)
    assert security.verify_credentials(s, None, None) is True
    assert security.verify_credentials(s, "x", "y") is True


def test_verify_correct_and_wrong(project):
    _web_config(project, enabled=True, username="me", password="s3cret")
    s = security.load_web_settings(project)
    assert security.verify_credentials(s, "me", "s3cret") is True
    assert security.verify_credentials(s, "me", "wrong") is False
    assert security.verify_credentials(s, "other", "s3cret") is False
    assert security.verify_credentials(s, None, None) is False


def test_validate_rejects_empty_when_enabled(project):
    _web_config(project, enabled=True, username="", password="s3cret")
    with pytest.raises(ValueError):
        security.validate_auth_settings(security.load_web_settings(project))
    _web_config(project, enabled=True, username="me", password="")
    with pytest.raises(ValueError):
        security.validate_auth_settings(security.load_web_settings(project))


def test_validate_passes_when_disabled_or_full(project):
    _web_config(project, enabled=False)
    security.validate_auth_settings(security.load_web_settings(project))  # 不抛
    _web_config(project, enabled=True, username="me", password="p")
    security.validate_auth_settings(security.load_web_settings(project))  # 不抛


# --- create_app 走中间件（默认关 / 启用后全站保护） ---


def test_create_app_default_off_still_serves(project):
    client = TestClient(create_app(project))
    assert client.get("/api/system").status_code == 200  # auth 关 → 直访


def test_create_app_auth_on_protects_all(project):
    _web_config(project, enabled=True, username="me", password="s3cret")
    client = TestClient(create_app(project))
    # 无凭据 → 401（/api + 静态页）
    assert client.get("/api/system").status_code == 401
    assert client.get("/").status_code == 401
    assert client.get("/api/system").headers.get("www-authenticate", "").startswith("Basic")
    # 正确 Basic → 放行；写口也能过
    ok = {"headers": {"Authorization": _b64("me", "s3cret")}}
    assert client.get("/api/system", **ok).status_code == 200
    assert client.get("/", **ok).status_code == 200


def test_create_app_auth_on_wrong_credentials_401(project):
    _web_config(project, enabled=True, username="me", password="s3cret")
    client = TestClient(create_app(project))
    assert client.get(
        "/api/system", headers={"Authorization": _b64("me", "nope")}
    ).status_code == 401


def test_create_app_auth_empty_fails_fast(project):
    _web_config(project, enabled=True, username="", password="s3cret")
    with pytest.raises(ValueError):
        create_app(project)  # 空口令 → install_auth fail-fast，不静默无鉴权