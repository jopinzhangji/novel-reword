"""G4b outline router：大纲 + 进度指针（节拍情志条）。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from src.workbench import outline
from web.api.routers.common import resolve_novel_root

router = APIRouter(tags=["outline"])


@router.get("/novels/{slug}/outline")
def novel_outline(request: Request, slug: str) -> dict:
    return outline.outline(resolve_novel_root(request, slug))


@router.get("/novels/{slug}/progress")
def progress(request: Request, slug: str) -> dict:
    return outline.progress(resolve_novel_root(request, slug))