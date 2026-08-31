"""G4b novels router：作品索引 / 单书摘要。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from src.workbench import novels
from web.api.routers.common import project_root, resolve_novel_root

router = APIRouter(tags=["novels"])


@router.get("/novels")
def list_novels(request: Request) -> list[dict]:
    return novels.index_novels(project_root(request))


@router.get("/novels/{slug}/summary")
def novel_summary(request: Request, slug: str) -> dict:
    return novels.novel_summary(resolve_novel_root(request, slug))