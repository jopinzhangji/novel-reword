"""
G3 候选镜头 · 备选稿：作者在某章下手动以另一镜头生成的**试探稿**生命周期。

备选稿**不进演进、不进主书事件簿立库**（dry-run：生成时不触发成长迁移/事件/记忆；提升也不重放演进，
演进只认最终成文所在回合）。每时刻仍只有一条成文；备选稿是「试探镜头」，作者对比后**显式提升**才成为该章正篇。
- `write_alt_draft`：建 `state/drafts/{chapter_id}_{lens_id}.md` 写带头创建（幂等覆盖同名）。
- `list_alt_drafts`：读回某章所有 `status=draft` 的备选稿（供作者对比/选择）。
- `promote_alt_draft`：置 `status=promoted`，把正文**提升**为该章正篇（写入提供方 `canonical_path`，缺省仅落 state），
  返回 `(canonical_path, lens_id)` —— 调用方据此 `switch_protagonist` 切导出镜头。

确定性、无 LLM。不自动消费；提升不代表真实事件重演。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

logger = logging.getLogger(__name__)

_DRAFTS_DIR = "drafts"
_STATUS = ("draft", "promoted")


@dataclass(frozen=True)
class AltDraft:
    chapter_id: str
    lens_id: str
    status: str = "draft"
    body: str = ""
    path: str = ""
    raw: dict | None = None


def drafts_dir(data_root: Path | str) -> Path:
    return Path(data_root) / "state" / _DRAFTS_DIR


def draft_path(data_root: Path | str, chapter_id: str, lens_id: str) -> Path:
    safe_ch = re.sub(r"[^A-Za-z0-9_.\-]+", "_", (chapter_id or "ch"))
    safe_lens = re.sub(r"[^A-Za-z0-9_.\-]+", "_", (lens_id or "lens"))
    return drafts_dir(data_root) / f"{safe_ch}_{safe_lens}.md"


def _header(raw: dict) -> str:
    return "---\n" + yaml.safe_dump(raw, allow_unicode=True, sort_keys=True) + "---\n"


def _parse(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    try:
        raw = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None
    if not isinstance(raw, dict):
        return None
    body = text[end + len("\n---\n"):].lstrip("\n") if text.startswith("---\n") else ""
    raw["_body"] = body
    return raw


def write_alt_draft(
    data_root: Path | str,
    chapter_id: str,
    lens_id: str,
    body: str,
) -> Path:
    """创建/覆盖一条备选稿（`status=draft`）。不触发任何演进/立库。"""
    folder = drafts_dir(data_root)
    folder.mkdir(parents=True, exist_ok=True)
    path = draft_path(data_root, chapter_id, lens_id)
    raw = {"type": "alt_draft", "chapter_id": chapter_id, "lens_id": lens_id, "status": "draft"}
    path.write_text(_header(raw) + (body or ""), encoding="utf-8")
    return path


def list_alt_drafts(data_root: Path | str, chapter_id: str) -> list[AltDraft]:
    """读回某章所有备选稿（按文件名排序）。"""
    results: list[AltDraft] = []
    folder = drafts_dir(data_root)
    if not folder.is_dir():
        return results
    prefix = f"{re.sub(r'[^A-Za-z0-9_.\\-]+', '_', chapter_id or 'ch')}_"
    for path in sorted(folder.glob("*.md")):
        if not path.name.startswith(prefix):
            continue
        raw = _parse(path)
        if not raw:
            continue
        status = str(raw.get("status") or "draft")
        if status not in _STATUS:
            status = "draft"
        results.append(
            AltDraft(
                chapter_id=str(raw.get("chapter_id") or chapter_id),
                lens_id=str(raw.get("lens_id") or ""),
                status=status,
                body=str(raw.get("_body") or ""),
                path=str(path),
                raw=raw,
            )
        )
    return results


def promote_alt_draft(
    data_root: Path | str,
    chapter_id: str,
    lens_id: str,
    *,
    canonical_writer: Callable[[str], Path] | None = None,
) -> tuple[Path, str] | None:
    """
    把 `{chapter_id, lens_id}` 备选稿提升为该章最终成文：
    - 置 `status=promoted` 写回；若给 `canonical_writer`（把正文写入正篇常显路径的委托），先由其写 canonical。
    - 返回 `(canonical_path|draft_path, lens_id)`；找不到备选稿→None。
    提升**不重放演进**；调用方随后以 `lens_id` 调 `switch_protagonist` 切导出镜头。
    """
    path = draft_path(data_root, chapter_id, lens_id)
    raw = _parse(path)
    if raw is None or str(raw.get("status") or "draft") != "draft":
        logger.warning("[G3] 无可提升的备选稿 %s (status=%s)", path, None if raw is None else raw.get("status"))
        return None
    body = str(raw.get("_body") or "")
    raw["status"] = "promoted"
    # 落 promoted 态（保留 status 头、正文原样）
    path.write_text(_header(raw) + body, encoding="utf-8")
    canonical_path: Path = path
    if canonical_writer is not None:
        try:
            canonical_path = canonical_writer(body)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[G3] 提升备选稿时写 canonical 失败，草案仍置 promoted：%s", exc)
    logger.info("[G3] 备选稿提升为该章最终成文：chapter=%s lens=%s → %s", chapter_id, lens_id, canonical_path)
    return canonical_path, lens_id