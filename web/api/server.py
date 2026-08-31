"""GG6 启动器（D13 §6.5）：按 config/web_api.yaml 的 server.host/port 起 web 工作台。

用法：
    python -m web.api.server                      # 读 config/web_api.yaml（默认 127.0.0.1:8000）
    python -m web.api.server --root /path/to/proj # 指定项目根（读其 config/web_api.yaml）

auth.enabled=true 且空口令 → 启动即报错（fail-fast，不静默无鉴权）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _project_root() -> Path:
    try:
        from src.config import PROJECT_ROOT

        return Path(PROJECT_ROOT)
    except Exception:  # noqa: BLE001
        return Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="Novel-Data Workbench web server")
    parser.add_argument("--root", default=None, help="项目根（默认仓库根）")
    args = parser.parse_args()
    root = Path(args.root) if args.root else _project_root()

    from web.api.app import create_app
    from web.api.security import load_web_settings, validate_auth_settings

    settings = load_web_settings(root)
    try:
        validate_auth_settings(settings)
    except ValueError as e:  # noqa: BLE001
        print(f"[web/server] 配置错误：{e}", file=sys.stderr)
        return 2

    host = str(settings["server"]["host"])
    port = int(settings["server"]["port"])
    auth_state = "开（Basic Auth）" if settings["auth"]["enabled"] else "关（本机直访 / 0.0.0.0+关=裸奔）"
    print(f"[web/server] 监听 {host}:{port} · auth={auth_state}")
    print(f"[web/server] 浏览器打开 http://127.0.0.1:{port}/")
    if settings["auth"]["enabled"]:
        print(f"[web/server] 使用前请确认 auth.username/password（shared secret，勿对公网裸奔）")

    import uvicorn

    uvicorn.run(create_app(root), host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())