"""G4b console router：作者控制台读/写口（复用 G3 三件套白名单）。

- GET    /novels/{slug}/console          读：镜头 / 能力面 / 备选稿
- PATCH  /novels/{slug}/features         写：能力开关（save_features）
- PUT    /novels/{slug}/protagonist      写：切换导出镜头
- GET/POST /novels/{slug}/drafts         写：列 / 建备选稿
- POST   /novels/{slug}/drafts/promote   写：提升备选稿
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.workbench import console
from web.api.routers.common import resolve_novel_root

router = APIRouter(tags=["console"])


class FeaturesBody(BaseModel):
    features: dict


class TargetBody(BaseModel):
    target_id: str


class DraftBody(BaseModel):
    chapter_id: str
    lens_id: str
    body: str = ""


class PromoteBody(BaseModel):
    chapter_id: str
    lens_id: str


@router.get("/novels/{slug}/console")
def console_status(request: Request, slug: str) -> dict:
    return console.console_status(resolve_novel_root(request, slug))


@router.patch("/novels/{slug}/features")
def patch_features(request: Request, slug: str, body: FeaturesBody) -> dict:
    return console.patch_features(resolve_novel_root(request, slug), body.features)


@router.put("/novels/{slug}/protagonist")
def switch_lens(request: Request, slug: str, body: TargetBody) -> dict:
    return console.switch_lens(resolve_novel_root(request, slug), body.target_id)


@router.get("/novels/{slug}/drafts")
def list_drafts(request: Request, slug: str, chapter_id: str | None = None) -> list[dict]:
    return console.list_drafts(resolve_novel_root(request, slug), chapter_id)


@router.post("/novels/{slug}/drafts")
def write_draft(request: Request, slug: str, body: DraftBody) -> dict:
    return console.write_draft(resolve_novel_root(request, slug), body.chapter_id, body.lens_id, body.body)


@router.post("/novels/{slug}/drafts/promote")
def promote_draft(request: Request, slug: str, body: PromoteBody) -> dict:
    return console.promote_draft(resolve_novel_root(request, slug), body.chapter_id, body.lens_id)