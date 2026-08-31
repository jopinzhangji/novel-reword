"""G4b Web 工作台入口：FastAPI 应用工厂 + 静态仪表盘挂载。

`create_app(project_root)`：把全部 G4b router 以 `/api` 前缀挂到
`app.state.WORKBENCH_ROOT`（默认仓库根），并在根路径挂 `web/static/` 静态页。
模块级 `app = create_app()` 供 uvicorn 直接启动：
    python -m uvicorn web.api.app:app
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.api import security
from web.api.routers import characters, console, graph, novels, outline, session, system
from web.api.routers.session import SessionRegistry


def _default_root() -> Path:
    try:
        from src.config import PROJECT_ROOT

        return Path(PROJECT_ROOT)
    except Exception:  # noqa: BLE001
        return Path(__file__).resolve().parents[2]


def create_app(project_root: Path | str | None = None) -> FastAPI:
    root = Path(project_root) if project_root is not None else _default_root()
    app = FastAPI(title="Novel-Data Workbench (G4)")
    app.state.WORKBENCH_ROOT = root
    # GG6 远程鉴权：读 config/web_api.yaml（host/port 由 web.api.server 用；auth.enabled 可开密码登录）
    web_settings = security.load_web_settings(root)
    app.state.WEB_SETTINGS = web_settings
    security.install_auth(app, web_settings)
    # G4c 作者在环会话：注册表（data_root 一地对一）+ 可注入 run_fn（测试用假回环）
    app.state.SESSION_REGISTRY = SessionRegistry()
    app.state.SESSION_RUN_FN = None

    prefix = "/api"
    app.include_router(novels.router, prefix=prefix)
    app.include_router(graph.router, prefix=prefix)
    app.include_router(characters.router, prefix=prefix)
    app.include_router(outline.router, prefix=prefix)
    app.include_router(console.router, prefix=prefix)
    app.include_router(session.router, prefix=prefix)
    app.include_router(system.router, prefix=prefix)

    static_dir = Path(__file__).resolve().parents[1] / "static"
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="dashboard")
    return app


app = create_app()