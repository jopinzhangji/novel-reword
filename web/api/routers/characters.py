"""G4b characters router：人物索引 / 详情 / 信息视野。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from src.workbench import characters
from web.api.routers.common import resolve_novel_root

router = APIRouter(tags=["characters"])


@router.get("/novels/{slug}/characters")
def characters_index(request: Request, slug: str) -> list[dict]:
    return characters.characters_index(resolve_novel_root(request, slug))


@router.get("/novels/{slug}/characters/{character_id}")
def character_detail(request: Request, slug: str, character_id: str) -> dict:
    return characters.character_detail(resolve_novel_root(request, slug), character_id)


@router.get("/novels/{slug}/characters/{character_id}/view")
def character_view(request: Request, slug: str, character_id: str) -> dict:
    return characters.character_view(resolve_novel_root(request, slug), character_id)