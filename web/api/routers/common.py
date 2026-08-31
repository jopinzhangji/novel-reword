"""G4b router 公共：从请求拿 project_root 并按 slug 解析到小说根（404 守卫）。"""
from __future__ import annotations

from fastapi import HTTPException, Request
from pathlib import Path

from src.workbench.common import novel_roots


def project_root(request: Request) -> Path:
    return Path(request.app.state.WORKBENCH_ROOT)


def resolve_novel_root(request: Request, slug: str) -> Path:
    """slug → data/novels/<slug>/；不存在则 404。"""
    root = project_root(request)
    for p in novel_roots(root):
        if Path(p).name == slug:
            return Path(p)
    raise HTTPException(status_code=404, detail=f"未找到小说 slug={slug}")