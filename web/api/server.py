"""GG6 启动器（D13 §6.5）：按 config/web_api.yaml 的 server.host/port 起 web 工作台。

用法：
    python -m web.api.server                      # 读 config/web_api.yaml（默认 127.0.0.1:8000）
    python -m web.api.server --root /path/to/proj # 指定项目根（读其 config/web_api.yaml）

auth.enabled=true 且空口令 → 启动即报错（fail-fast，不静默无鉴权）。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _project_root() -> Path:
    try:
        from src.config import PROJECT_ROOT

        return Path(PROJECT_ROOT)
    except Exception:  # noqa: BLE001
        return Path(__file__).resolve().parents[2]


def load_env_dotfile(root: Path) -> None:
    """服务进程启动时把项目根 .env 读入 os.environ（仅在未显式设置时 setdefault）。

    与 CLI 文档「.env 配置大模型密钥」的约定对齐：无依赖、纯 `K=V` 解析，
    隐式 shell 环境优先（不动已在环境里的值），不向终端回显值。
    """
    dotfile = root / ".env"
    if not dotfile.is_file():
        return
    try:
        for raw in dotfile.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key and value:
                os.environ.setdefault(key, value.strip())
    except OSError:  # noqa: BLE001 — .env 读取失败不阻断起服务
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Novel-Data Workbench web server")
    parser.add_argument("--root", default=None, help="项目根（默认仓库根）")
    args = parser.parse_args()
    root = Path(args.root) if args.root else _project_root()
    load_env_dotfile(root)  # 读项目根 .env（DASHSCOPE_API_KEY 等），使工作台用真实 LLM

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