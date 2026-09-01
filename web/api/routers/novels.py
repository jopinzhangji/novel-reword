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


@router.get("/novels/{slug}/story")
def novel_story(request: Request, slug: str, scope: str = "main", limit: int = 20) -> dict:
    """GG-W #6 小说正文 read port：按 turn 倒序取事件 summary+body（正文以 `## 正文` 段为准）。"""
    return novels.story_events(
        resolve_novel_root(request, slug), scope_id=scope, limit=max(1, min(int(limit), 100))
    )