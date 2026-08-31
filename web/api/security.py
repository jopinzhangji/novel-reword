"""GG6 远程访问与鉴权（D13 §6.5）：可配监听 + 密码登录（HTTP Basic Auth）。

- `load_web_settings(project_root)`：读 `config/web_api.yaml`（server.host/port + auth.*），
  缺省给安全默认（host=127.0.0.1 仅本机、auth.enabled=false）。
- `validate_auth_settings(settings)`：auth.enabled=true 但 username/password 空 → 抛错，
  确保启动 fail-fast、绝不静默无鉴权裸奔。
- `verify_credentials(settings, username, password)`：常量时间比较（hmac.compare_digest）；
  auth 未启用时恒放行。
- `install_auth(app, settings)`：enabled 时挂全站 Basic Auth 中间件（/api/* + 静态页一并保护，
  401 + WWW-Authenticate，浏览器原生「密码登录」弹窗）。

口令为服务器明文共享口令，适合单作者局域网/反代后自用；不建议直接对公网
（公网请前置反代 + 更强认证，或用 ssh -L 隧道零暴露写口）。
"""
from __future__ import annotations

import base64
import hmac
from pathlib import Path

import yaml

_DEFAULTS_SERVER = {"host": "127.0.0.1", "port": 8000}
_DEFAULTS_AUTH = {
    "enabled": False,
    "username": "",
    "password": "",
    "realm": "Novel-Data Workbench",
}


def load_web_settings(project_root: Path | str) -> dict:
    """读 config/web_api.yaml → 嵌套 dict（server/auth，缺省合并默认）。"""
    project_root = Path(project_root)
    path = project_root / "config" / "web_api.yaml"
    raw: dict = {}
    if path.is_file():
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                raw = loaded
        except yaml.YAMLError:
            raw = {}
    server = raw.get("server") if isinstance(raw.get("server"), dict) else {}
    auth = raw.get("auth") if isinstance(raw.get("auth"), dict) else {}
    return {
        "server": {
            "host": str(server.get("host") or _DEFAULTS_SERVER["host"]).strip(),
            "port": int(server.get("port") or _DEFAULTS_SERVER["port"]),
        },
        "auth": {
            "enabled": bool(auth.get("enabled", _DEFAULTS_AUTH["enabled"])),
            "username": str(auth.get("username") or ""),
            "password": str(auth.get("password") or ""),
            "realm": str(auth.get("realm") or _DEFAULTS_AUTH["realm"]),
        },
    }


def validate_auth_settings(settings: dict) -> None:
    auth = settings.get("auth") or {}
    if auth.get("enabled"):
        if not str(auth.get("username") or "").strip():
            raise ValueError("config/web_api.yaml: auth.enabled=true 但 username 为空；拒绝启动（不裸奔）")
        if not str(auth.get("password") or ""):
            raise ValueError("config/web_api.yaml: auth.enabled=true 但 password 为空；拒绝启动（不裸奔）")


def verify_credentials(settings: dict, username: str | None, password: str | None) -> bool:
    """auth 未启用 → 恒放行；启用 → 常量时间比较 user/password。"""
    auth = settings.get("auth") or {}
    if not auth.get("enabled"):
        return True
    want_u = str(auth.get("username") or "")
    want_p = str(auth.get("password") or "")
    got_u = username or ""
    got_p = password or ""
    u_ok = len(want_u) == len(got_u) and hmac.compare_digest(got_u, want_u)
    p_ok = len(want_p) == len(got_p) and hmac.compare_digest(got_p, want_p)
    return bool(u_ok and p_ok)


def _decode_basic(authorization: str) -> tuple[str | None, str | None]:
    if not authorization.startswith("Basic "):
        return None, None
    try:
        raw = base64.b64decode(authorization[6:]).decode("utf-8")
    except Exception:  # noqa: BLE001
        return None, None
    u, _, p = raw.partition(":")
    return u, p


def install_auth(app, settings: dict) -> None:
    """enabled 时给 app 挂全站 Basic Auth 中间件；空口令 fail-fast。"""
    validate_auth_settings(settings)
    if not settings.get("auth", {}).get("enabled"):
        return
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response

    realm = str(settings.get("auth", {}).get("realm") or "Novel-Data Workbench")

    class _BasicAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            auth_header = request.headers.get("Authorization", "")
            u, p = _decode_basic(auth_header)
            if verify_credentials(settings, u, p):
                return await call_next(request)
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": f'Basic realm="{realm}"'},
            )

    app.add_middleware(_BasicAuthMiddleware)