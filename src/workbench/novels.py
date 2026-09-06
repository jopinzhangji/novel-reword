"""G4 作品索引 / 进度总览（SDD D13 §4 多小说进度卡片）。

只读、确定性：委托 outline_store / relationship_graph / character_growth，
对 data/novels/<slug>/ 逐书聚合「章节/节拍/回合 + 成长爆发 + 关系边数 + 最近回合」。
在线书名编辑（D13 §6.8，确定性写口）：rename_novel 改 meta/index/current_novel，
slug 变化时目录重命名——只动身份元数据、不碰 book/ 与 config/*.yaml 写作产物。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from src.author_loop.novel_identity import slugify_title
from src.workbench.common import (
    characters_config,
    characters_roster,
    novel_meta,
    novel_roots,
    novels_dir,
    scope_event_dirs,
)
from src.runtime.character_growth import load_growth_state
from src.runtime.file_sync import load_scope_events_from_disk
from src.runtime.outline_store import load_outline_snapshot, resolve_current_beat
from src.runtime.relationship_graph import load_graph, relationship_graph_yaml_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _growth_totals(novel_root: Path) -> dict:
    """全书成长聚合：有 growth 状态的角色数 + transition_log 总条数。"""
    roster = characters_roster(novel_root)
    with_state = 0
    transitions = 0
    for c in roster:
        cid = c.get("id")
        if not cid:
            continue
        state = load_growth_state(cid, novel_root)
        if state.transition_log:
            with_state += 1
            transitions += len(state.transition_log)
    return {"characters_with_growth": with_state, "transition_entries": transitions}


def _outline_pointer(novel_root: Path) -> dict:
    """当前章/拍/回合指针；无大纲 → 空。"""
    snap = load_outline_snapshot(novel_root)
    if snap is None:
        return {}
    beat = resolve_current_beat(snap, soft_max_turns=3)
    if beat is None:
        return {"has_outline": True, "had_any_beat": False}
    return {
        "has_outline": True,
        "had_any_beat": True,
        "chapter_id": beat.chapter_id,
        "chapter_title": beat.chapter_title,
        "beat_id": beat.beat_id,
        "beat_intent": beat.beat_intent,
        "turns_in_beat": beat.turns_in_beat,
        "missing_ref": beat.missing_ref,
    }


def _graph_edge_count(novel_root: Path) -> int:
    path = relationship_graph_yaml_path(novel_root)
    graph = load_graph(path)
    return len(graph.get("edges") or [])


def _recent_event_count(novel_root: Path) -> int:
    total = 0
    for scope_dir in scope_event_dirs(novel_root):
        total += len(list((scope_dir / "events").glob("turn_*.md")))
    return total


def novel_summary(novel_root: Path) -> dict:
    """单书进度摘要卡（多小说总览 / dashboard 摘要卡共用）。"""
    growth = _growth_totals(novel_root)
    pointer = _outline_pointer(novel_root)
    return {
        **novel_meta(novel_root),
        "growth": growth,
        "outline_pointer": pointer,
        "edge_count": _graph_edge_count(novel_root),
        "scope_event_count": _recent_event_count(novel_root),
        "character_count": len(characters_roster(novel_root)),
    }


def index_novels(project_root: Path) -> list[dict]:
    """全部小说进度卡片（?center 排序：索引序）。"""
    out = []
    for root in novel_roots(project_root):
        out.append(novel_summary(root))
    return out


def story_events(novel_root: Path, scope_id: str = "main", limit: int = 20) -> dict:
    """GG-W #6 小说正文情况：按 turn 倒序取 scope 事件 summary+body（确定性 read port）。

    复用 `file_sync.load_scope_events_from_disk`（`## 正文` 段作 body）：真小说有正文，
    测试/样例小说多只有摘要（body 空）。配 outline_pointer 作「当前位置」。不触碰正文磁盘。
    """
    events = load_scope_events_from_disk(novel_root, scope_id)
    turn_dir = novel_root / "book" / "events" / scope_id / "events"
    turns = sorted(
        int(p.stem.replace("turn_", ""))
        for p in turn_dir.glob("turn_*.md")
    ) if turn_dir.is_dir() else []
    rows = []
    for i, ev in enumerate(events):
        rows.append({
            "turn": turns[i] if i < len(turns) else i + 1,
            "summary": ev.get("summary", ""),
            "body": ev.get("body", ""),
            "time": ev.get("time", ""),
            "place": ev.get("place", ""),
            "present_characters": ev.get("present_characters", []),
        })
    rows.reverse()  # 最新在前
    return {
        "scope_id": scope_id,
        "count": len(rows),
        "events": rows[:limit],
        "outline_pointer": _outline_pointer(novel_root),
    }


def _resolved_root(project_root: Path, slug: str) -> Path:
    """slug → data/novels/<slug>/；找不到抛 ValueError（不沿 index 顺序，避免歧义）。"""
    root = novels_dir(project_root) / slug
    if not root.is_dir():
        raise ValueError(f"未找到小说 slug={slug}")
    return root


def rename_novel(project_root: Path, slug: str, title: str) -> dict:
    """在线书名编辑（D13 §6.8，确定性写口）。

    仅改身份元数据：meta.yaml（title+slug，status 不变）+ data/novels/index.yaml
    （按旧 slug 移除旧行、按新 slug 追加）+ config/current_novel.yaml（指针指向本
    小说时更新 slug/title/root，provisional=False）。slug 变化时对目录 rename
    （`slugify_title` 冲突递增后缀）。不触碰 book/ 与 config/world|characters|outline
    等写作产物。返回新 `{slug, title, root}`。
    """
    project_root = Path(project_root)
    title = (title or "").strip()
    if not title:
        raise ValueError("书名不能为空")
    old_root = _resolved_root(project_root, slug)

    meta = _read_yaml(old_root / "meta.yaml")
    old_slug = str(meta.get("slug") or old_root.name)
    old_status = str(meta.get("status") or "unknown")

    new_slug = slugify_title(title)
    if not new_slug:
        new_slug = old_slug
    target = novels_dir(project_root) / new_slug
    if target.resolve() != old_root.resolve():
        if target.exists():
            i = 2
            base = new_slug
            while (novels_dir(project_root) / f"{base}-{i}").exists():
                i += 1
            new_slug = f"{base}-{i}"
            target = novels_dir(project_root) / new_slug
        old_root.rename(target)
        novel_root = target
    else:
        novel_root = old_root

    # meta.yaml：title + slug（status 不变：draft 仍是 draft）
    _write_yaml(
        novel_root / "meta.yaml",
        {
            **meta,
            "title": title,
            "slug": new_slug,
        },
    )

    # index.yaml：按旧 slug 移除旧行、按新 slug 追加
    idx_path = novels_dir(project_root) / "index.yaml"
    idx = _read_yaml(idx_path)
    novels = [n for n in idx.get("novels") or [] if not (isinstance(n, dict) and n.get("slug") == old_slug)]
    novels.append(
        {
            "slug": new_slug,
            "title": title,
            "status": old_status,
            "updated_at": _now_iso(),
        }
    )
    _write_yaml(idx_path, {"novels": novels})

    # config/current_novel.yaml：指针指向本小说时更新
    cur_path = project_root / "config" / "current_novel.yaml"
    cur = _read_yaml(cur_path)
    cur_slug = str(cur.get("slug") or "")
    cur_root = str(cur.get("root") or "")
    if cur_slug == old_slug or cur_root == str(old_root):
        _write_yaml(
            cur_path,
            {
                **cur,
                "slug": new_slug,
                "title": title,
                "root": str(novel_root),
                "provisional": False,
            },
        )

    return {"slug": new_slug, "title": title, "root": str(novel_root)}