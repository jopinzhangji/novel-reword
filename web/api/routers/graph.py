"""G4b graph router：全书谱 / ego 心图 / 单对。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from src.workbench import graph
from web.api.routers.common import resolve_novel_root

router = APIRouter(tags=["graph"])


@router.get("/novels/{slug}/graph")
def full_graph(request: Request, slug: str) -> dict:
    return graph.full_graph(resolve_novel_root(request, slug))


@router.get("/novels/{slug}/graph/ego")
def ego_graph(request: Request, slug: str, center: str, hops: int = 2) -> dict:
    return graph.ego_graph(resolve_novel_root(request, slug), center, hops=hops)


@router.get("/novels/{slug}/graph/pair")
def pair(request: Request, slug: str, a: str, b: str) -> dict:
    return graph.pair(resolve_novel_root(request, slug), a, b)