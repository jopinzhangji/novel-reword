"""G4c+/system router（GG5）：系统设置读 + 白名单写。

- GET   /api/system                读 effective LLM（v2 工作参数可写）/ 工作台互斥 / 联网检索
- PATCH /api/system                白名单写 per-novel config/runtime.yaml（返回更新后状态）

作用于仓库级「当前小说」（config/current_novel.yaml），非按 slug 路由。
framework（LLM）**v2 工作参数可写**：`framework.llm_options.model/base_url/timeout/max_retries/api_key_env`
过白名单；提供方类型与密钥值仍只读。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.workbench import system
from web.api.routers.common import project_root

router = APIRouter(tags=["system"])


class SystemPatchBody(BaseModel):
    author_workbench_enabled: bool | None = None
    internet_search: dict[str, Any] | None = None
    framework: dict[str, Any] | None = None


@router.get("/system")
def get_system(request: Request) -> dict:
    return system.system_status(project_root(request))


@router.patch("/system")
def patch_system(request: Request, body: SystemPatchBody) -> dict:
    payload: dict[str, Any] = {}
    if body.author_workbench_enabled is not None:
        payload["author_workbench_enabled"] = body.author_workbench_enabled
    if body.internet_search is not None:
        payload["internet_search"] = body.internet_search
    if body.framework is not None:
        payload["framework"] = body.framework
    if not payload:
        raise HTTPException(status_code=400, detail="无可写设置（仅 author_workbench/internet_search/framework 白名单键可写）")
    try:
        return system.patch_system(project_root(request), payload)
    except ValueError as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e