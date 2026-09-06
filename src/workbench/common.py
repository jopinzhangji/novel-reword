"""G4 工作台公共工具：多小说发现、角色名册、读取/安全工具（确定性、无 LLM）。"""
from __future__ import annotations

import yaml
from pathlib import Path


def read_yaml(path: Path) -> dict | list | None:
    """安全读 YAML；不存在或不可解析返回 None。"""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return None
    try:
        data = yaml.safe_load(text)
    except Exception:  # noqa: BLE001
        return None
    return data if isinstance(data, (dict, list)) else None


def safe_str(value, default: str = "") -> str:
    return str(value or "") if value is not None else default


def novels_dir(project_root: Path) -> Path:
    return Path(project_root) / "data" / "novels"


def novel_roots(project_root: Path) -> list[Path]:
    """列出全部小说根目录 data/novels/<slug>/。

    - 有 index.yaml 时按其中 novels[].slug 顺序给出；
    - 无 index.yaml 时回退 glob data/novels/*/ 下含 meta.yaml 或 book/ 的目录。
    结果去重、保持序。
    """
    idx = read_yaml(novels_dir(project_root) / "index.yaml")
    seen: list[Path] = []
    if isinstance(idx, dict):
        for item in idx.get("novels") or []:
            if isinstance(item, dict):
                slug = safe_str(item.get("slug"))
                if slug:
                    p = novels_dir(project_root) / slug
                    if p.is_dir() and p not in seen:
                        seen.append(p)
    if not seen:
        base = novels_dir(project_root)
        if base.is_dir():
            for p in sorted(base.iterdir()):
                if not p.is_dir():
                    continue
                has_meta = (p / "meta.yaml").is_file()
                has_book = (p / "book").is_dir()
                if (has_meta or has_book) and p not in seen:
                    seen.append(p)
    return seen


def novel_meta(novel_root: Path) -> dict[str, object]:
    """读 data/novels/<slug>/meta.yaml → dict；缺失给默认。"""
    meta = read_yaml(Path(novel_root) / "meta.yaml")
    if not isinstance(meta, dict):
        meta = {}
    slug = safe_str(meta.get("slug")) or Path(novel_root).name
    return {
        "slug": slug,
        "title": safe_str(meta.get("title")) or "（未命名）",
        "status": safe_str(meta.get("status")) or "unknown",
        "created_at": safe_str(meta.get("created_at")),
        "world_name": safe_str(meta.get("world_name")),
        "synopsis": safe_str(meta.get("synopsis")),
    }


def characters_roster(novel_root: Path) -> list[dict]:
    """读 config/characters.yaml 的 characters 列表 → list[dict]；缺省空表。"""
    data = read_yaml(Path(novel_root) / "config" / "characters.yaml")
    if not isinstance(data, dict):
        return []
    chars = data.get("characters") or []
    return [c for c in chars if isinstance(c, dict)]


def characters_config(novel_root: Path) -> dict:
    """供既有模块的 characters_config 入参（`{"characters":[...]}`）。"""
    return {"characters": characters_roster(novel_root)}


def scope_event_dirs(novel_root: Path) -> list[Path]:
    """列出 book/events/* 下含 events/turn_*.md 的 scope 目录（按名排序）。"""
    base = Path(novel_root) / "book" / "events"
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.iterdir()):
        if p.is_dir() and (p / "events").is_dir():
            out.append(p)
    return out