"""G4 作者控制台 · 定制调整写口（SDD D13 §5 console + §6.2）。

复用 G3 三件套：capabilities（能力开关）、protagonist_switch（运行时镜头）、alt_draft（候选备选稿）。
- 读：console_status（当前镜头 / 能力面 / 备选稿清单）——只读、确定性。
- 写：patch_features → save_features；switch_lens → switch+save_protagonist_context；
      write_draft / promote_draft → alt_draft。
所有写口仍走 G3 白名单；作者在环（Session）驱动不在本层，仍由 D9 WebInputAdapter 承接。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from src.runtime.alt_draft import (
    drafts_dir,
    list_alt_drafts,
    promote_alt_draft,
    write_alt_draft,
)
from src.runtime.capabilities import load_features, resolve_features, save_features
from src.runtime.protagonist_switch import (
    ProtagonistContext,
    effective_protagonist,
    load_protagonist_context,
    save_protagonist_context,
    switch_protagonist,
)
from src.workbench.common import characters_config, characters_roster


def _runtime_config(runtime_config: dict | None) -> dict:
    return runtime_config if isinstance(runtime_config, dict) else {}


def _all_drafts(novel_root: Path) -> list[dict]:
    """跨章列出所有备选稿（本地头解析；复用 alt_draft 盘符约束）。"""
    folder = drafts_dir(novel_root)
    out: list[dict] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        if end < 0:
            continue
        try:
            raw = yaml.safe_load(text[4:end]) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(raw, dict):
            continue
        body = text[end + len("\n---\n"):].lstrip("\n")
        out.append(
            {
                "chapter_id": str(raw.get("chapter_id") or ""),
                "lens_id": str(raw.get("lens_id") or ""),
                "status": str(raw.get("status") or "draft"),
                "body": body,
                "path": str(path),
            }
        )
    return out


def console_status(novel_root: Path, runtime_config: dict | None = None) -> dict:
    """作者控制台读面：镜头 + 能力面 + 备选稿清单（只读确定性）。"""
    rc = _runtime_config(runtime_config)
    cc = characters_config(novel_root)
    ctx = load_protagonist_context(novel_root)
    pid, pname = effective_protagonist(rc, cc, ctx)
    flags = resolve_features(rc, data_root=novel_root)
    roster = characters_roster(novel_root)
    return {
        "lens": {
            "protagonist_id": pid,
            "display_name": pname,
            "is_override": bool(ctx.protagonist_id),
            "selectable": [
                {
                    "id": c.get("id"),
                    "name": c.get("name") or c.get("id"),
                    "role": c.get("role") or "",
                }
                for c in roster
                if c.get("id")
            ],
        },
        "features": {
            "flags": flags.to_dict(),
            "persisted_override": load_features(novel_root) or {},
        },
        "drafts": _all_drafts(novel_root),
        "draft_count": len(_all_drafts(novel_root)),
    }


def patch_features(novel_root: Path, override: dict) -> dict:
    """PATCH /features：写 per-novel config/features.yaml 并重算标志。"""
    save_features(novel_root, override)
    flags = resolve_features({}, data_root=novel_root)
    return {"flags": flags.to_dict(), "persisted_override": load_features(novel_root) or {}}


def switch_lens(novel_root: Path, target_id: str, runtime_config: dict | None = None) -> dict:
    """PUT /protagonist：切换导出镜头并落盘。"""
    rc = _runtime_config(runtime_config)
    cc = characters_config(novel_root)
    ctx = load_protagonist_context(novel_root)
    pid, pname = switch_protagonist(ctx, rc, cc, target_id)
    save_protagonist_context(novel_root, ctx)
    return {"protagonist_id": pid, "display_name": pname}


def write_draft(novel_root: Path, chapter_id: str, lens_id: str, body: str) -> dict:
    """POST /drafts：建一条候选备选稿（dry-run，不触发演进/立库）。"""
    path = write_alt_draft(novel_root, chapter_id, lens_id, body)
    return {"path": str(path), "lens_id": lens_id, "chapter_id": chapter_id, "status": "draft"}


def list_drafts(novel_root: Path, chapter_id: str | None = None) -> list[dict]:
    """GET /drafts：按章或跨章列备选稿。"""
    if chapter_id:
        return [
            {
                "chapter_id": d.chapter_id,
                "lens_id": d.lens_id,
                "status": d.status,
                "body": d.body,
                "path": d.path,
            }
            for d in list_alt_drafts(novel_root, chapter_id)
        ]
    return _all_drafts(novel_root)


def promote_draft(novel_root: Path, chapter_id: str, lens_id: str) -> dict:
    """POST /drafts/:lens/promote：提升备选稿为成文并返回镜头（供调用方切导出镜头）。"""
    res = promote_alt_draft(novel_root, chapter_id, lens_id)
    if res is None:
        return {"promoted": False, "reason": "无该 (章, 镜头) 备选稿，或已提升"}
    cp, lens = res
    return {"promoted": True, "canonical_path": str(cp), "lens_id": lens}