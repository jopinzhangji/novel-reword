"""G4b novels router：作品索引 / 单书摘要 / 在线书名编辑。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.workbench import novels
from web.api.routers.common import project_root, resolve_novel_root

router = APIRouter(tags=["novels"])


class RenameBody(BaseModel):
    title: str


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


@router.patch("/novels/{slug}/rename")
def rename_novel(request: Request, slug: str, body: RenameBody) -> dict:
    """D13 §6.8 在线书名编辑：校验后落 meta/index/current_novel，slug 变化时目录改名。"""
    try:
        return novels.rename_novel(project_root(request), slug, body.title)
    except ValueError as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e