"""G4b novels router：作品索引 / 单书摘要 / 在线书名编辑 / 设定讨论读口。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.workbench import discussion, novels
from src.workbench.common import novel_meta
from web.api.routers.common import project_root, resolve_novel_root

router = APIRouter(tags=["novels"])


class RenameBody(BaseModel):
    title: str


class SynopsisBody(BaseModel):
    text: str


@router.get("/novels")
def list_novels(request: Request) -> list[dict]:
    return novels.index_novels(project_root(request))


@router.get("/novels/{slug}/discussion")
def novel_discussion(request: Request, slug: str) -> dict:
    """D13 §6.9 设定讨论/设定情况快照（确定性读口，无 LLM）。"""
    return discussion.discussion_snapshot(resolve_novel_root(request, slug))


@router.get("/novels/{slug}/discussion/archive")
def novel_discussion_archive(request: Request, slug: str) -> dict:
    """D13 §6.9 最近归档设定讨论的完整内容（确定性读口；摘要 + 完整对话轮次/审阅摘要）。"""
    return discussion.archived_discussion_detail(resolve_novel_root(request, slug))


@router.patch("/novels/{slug}/synopsis")
def update_synopsis(request: Request, slug: str, body: SynopsisBody) -> dict:
    """D13 §6.9 写小说简介到 meta.yaml（作设定讨论种子）。"""
    from src.author_loop.novel_identity import write_synopsis

    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="简介不能为空")
    root = resolve_novel_root(request, slug)
    write_synopsis(root, body.text)
    return {"synopsis": novel_meta(root).get("synopsis") or ""}


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