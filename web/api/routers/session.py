"""G4c session router：作者在环会话（D9 §8.3 + D13 §6.3 写回通道）。

- POST   /session                    建会话（绑定 data_root；其已活跃 → 409 互斥）
- GET    /session/{key}              状态 + 当前 pending_prompt（前端可轮询）
- POST   /session/{key}/reply        body {text} → 喂作者回复（唤醒阻塞的 read）
- POST   /session/{key}/abort        放弃会话（令被阻塞 read 立即返回空串）
- DELETE /session/{key}              移除并中止会话，释放 data_root 锁

`run_fn` 默认 = run_novel_with_author.main（真实作者在环主流程）；测试经
`app.state.SESSION_RUN_FN` 注入假回环以隔离 LLM。注册表在 `app.state.SESSION_REGISTRY`。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from web.api.session_runner import SessionRegistry, pin_current_novel

router = APIRouter(tags=["session"])


class SessionCreateBody(BaseModel):
    slug: str
    data_root: str | None = None


class ReplyBody(BaseModel):
    text: str


def _registry(request: Request) -> SessionRegistry:
    reg = getattr(request.app.state, "SESSION_REGISTRY", None)
    if not isinstance(reg, SessionRegistry):
        raise HTTPException(status_code=501, detail="会话注册表未启用")
    return reg


def _run_fn(request: Request):
    return getattr(request.app.state, "SESSION_RUN_FN", None)


@router.post("/session")
def create_session(request: Request, body: SessionCreateBody) -> dict:
    reg = _registry(request)
    key = body.data_root or body.slug
    # 启动引擎线程前，把全局 current_novel 钉到本会话小说根（引擎按它决定操作哪本小说）。
    pin_current_novel(getattr(request.app.state, "WORKBENCH_ROOT", None), key)
    session, fresh = reg.create(key, data_root=key, run_fn=_run_fn(request))
    if not fresh:
        raise HTTPException(status_code=409, detail=f"data_root 已有活跃作者在环会话（{key}）")
    session.start()
    return {"key": key, **session.state()}


@router.get("/session/{key}")
def session_state(request: Request, key: str) -> dict:
    reg = _registry(request)
    session = reg.get(key)
    if session is None:
        raise HTTPException(status_code=404, detail=f"无此会话（{key}）")
    return {"key": key, **session.state()}


@router.post("/session/{key}/reply")
def session_reply(request: Request, key: str, body: ReplyBody) -> dict:
    reg = _registry(request)
    session = reg.get(key)
    if session is None:
        raise HTTPException(status_code=404, detail=f"无此会话（{key}）")
    session.submit(body.text)
    return {"key": key, **session.state()}


@router.post("/session/{key}/abort")
def session_abort(request: Request, key: str) -> dict:
    reg = _registry(request)
    session = reg.get(key)
    if session is None:
        raise HTTPException(status_code=404, detail=f"无此会话（{key}）")
    session.abort()
    return {"key": key, **session.state()}


@router.delete("/session/{key}")
def session_delete(request: Request, key: str) -> dict:
    reg = _registry(request)
    session = reg.remove(key)
    if session is None:
        raise HTTPException(status_code=404, detail=f"无此会话（{key}）")
    return {"key": key, "deleted": True}