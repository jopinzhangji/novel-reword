"""
设定完成后的小说命名与身份持久化。

当前职责（任务 B）：
- 基于设定生成书名候选（LLM 优先，失败时回退规则）；
- 作者确认书名；
- 写入 data_root/novels/<slug>/meta.yaml、index.yaml；
- 在 config/current_novel.yaml 记录当前小说指针。
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.config import current_novel_root

# 新小说首次落盘时的初稿书名（设定完成后可改为正式书名）
PROVISIONAL_NOVEL_TITLE = "（初稿）待命名"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify_title(title: str) -> str:
    """标题转安全目录名。"""
    t = (title or "").strip().lower()
    t = re.sub(r"\s+", "-", t)
    # 保留中文、英文、数字、下划线、短横线
    t = re.sub(r"[^0-9a-zA-Z_\-\u4e00-\u9fff]+", "-", t)
    t = re.sub(r"-{2,}", "-", t).strip("-_")
    return t or "novel"


def _novels_root(project_root: Path, runtime_config: dict) -> Path:
    try:
        from src.runtime.file_sync import get_data_root
    except Exception:
        return project_root / "data" / "novels"
    data_root = get_data_root(project_root, runtime_config)
    if not data_root:
        data_root = project_root / "data"
    return data_root / "novels"


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def has_current_novel_pointer(config_dir: Path) -> bool:
    p = config_dir / "current_novel.yaml"
    data = _read_yaml(p)
    return bool((data.get("slug") or "").strip())


def is_provisional_novel(config_dir: Path) -> bool:
    """当前小说是否为初稿目录（meta.status=draft），设定完成后可确认正式书名。"""
    nr = current_novel_root(config_dir)
    if not nr:
        return False
    meta = _read_yaml(nr / "meta.yaml")
    return (meta.get("status") or "").strip().lower() == "draft"


def _draft_slug_unique(novels_root: Path) -> str:
    """时间戳 + 冲突时递增，避免与已有目录重名。"""
    base = "draft-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = base
    n = 2
    while (novels_root / slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def ensure_provisional_novel_directory(
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
    world_config: dict,
    characters_config: dict,
    log: Any,
) -> dict[str, str]:
    """
    新小说且无 current_novel 时：在 data/.../novels/<draft-*>/ 下创建初稿目录与小说级配置，
    并写入 config/current_novel.yaml。不在全局 config 下写 example_world / example_characters。
    返回 {slug, title, root}。
    """
    if has_current_novel_pointer(config_dir):
        raise RuntimeError("ensure_provisional_novel_directory：已有 current_novel 指针")
    novels_root = _novels_root(project_root, runtime_config)
    novels_root.mkdir(parents=True, exist_ok=True)
    slug = _draft_slug_unique(novels_root)
    novel_root = novels_root / slug
    novel_root.mkdir(parents=True, exist_ok=True)
    title = PROVISIONAL_NOVEL_TITLE
    meta = {
        "title": title,
        "slug": slug,
        "status": "draft",
        "created_at": _now_iso(),
        "world_name": (world_config.get("world") or {}).get("name") or "",
    }
    _write_yaml(novel_root / "meta.yaml", meta)
    _write_yaml(novel_root / "config" / "runtime.yaml", _build_novel_runtime_snapshot(runtime_config, novel_root))
    _write_yaml(novel_root / "config" / "world.yaml", world_config or {})
    _write_yaml(novel_root / "config" / "characters.yaml", characters_config or {"characters": []})

    idx_path = novels_root / "index.yaml"
    idx = _read_yaml(idx_path)
    novels = list(idx.get("novels") or [])
    novels = [n for n in novels if not (isinstance(n, dict) and n.get("slug") == slug)]
    novels.append(
        {
            "slug": slug,
            "title": title,
            "status": "draft",
            "updated_at": _now_iso(),
        }
    )
    _write_yaml(idx_path, {"novels": novels})

    _write_yaml(
        config_dir / "current_novel.yaml",
        {"slug": slug, "title": title, "root": str(novel_root), "provisional": True},
    )
    if log:
        log.info(
            "已创建初稿小说目录（可稍后在设定完成后改为正式书名）：slug=%s，root=%s",
            slug,
            novel_root,
        )
    return {"slug": slug, "title": title, "root": str(novel_root)}


def _setting_brief_for_title(world_config: dict, special: dict | None) -> str:
    world = world_config.get("world") or {}
    world_name = world.get("name") or "未命名世界"
    era = world.get("era") or ""
    scope_names = [s.get("name") or s.get("id") for s in (world_config.get("scopes") or [])[:5] if isinstance(s, dict)]
    parts = [f"世界：{world_name}", f"时代：{era}" if era else "", f"范围：{'、'.join([x for x in scope_names if x])}" if scope_names else ""]
    if special:
        base_skip = {"world_id", "version", "genre", "theme", "reference"}
        keys = [k for k in special.keys() if k not in base_skip]
        if keys:
            parts.append("设定维度：" + "、".join(keys[:6]))
    return "\n".join([p for p in parts if p]).strip()


def generate_title_candidates(
    runtime_config: dict,
    world_config: dict,
    special: dict | None,
    count: int = 5,
) -> list[dict[str, str]]:
    """生成书名候选：[{title, reason}]。"""
    count = max(3, min(8, int(count)))
    brief = _setting_brief_for_title(world_config, special)
    prompt = (
        "你是资深网络小说编辑。请根据以下设定，生成小说书名候选。\n"
        f"{brief}\n\n"
        f"请输出 {count} 个候选，每个含：标题（4~14字）+ 20字内理由。\n"
        "严格输出 YAML，格式：\n"
        "candidates:\n"
        "  - title: 书名\n"
        "    reason: 理由\n"
    )
    from src.llm import get_llm_provider
    provider = get_llm_provider(runtime_config)
    if provider.__class__.__name__ == "DummyLLM":
        raise RuntimeError("生成书名需要可用 LLM，当前为 DummyLLM（未配置真实模型）")

    try:
        raw = provider.generate(prompt)
        data = yaml.safe_load(raw) or {}
        out = []
        for c in data.get("candidates") or []:
            if not isinstance(c, dict):
                continue
            title = str(c.get("title") or "").strip()
            reason = str(c.get("reason") or "").strip()
            if title:
                out.append({"title": title[:28], "reason": reason[:60]})
        if len(out) >= 3:
            return out[:count]
    except Exception:
        raise RuntimeError("生成书名失败：LLM不可用或返回结果不可解析")


def _build_novel_runtime_snapshot(runtime_config: dict, novel_root: Path) -> dict:
    """将当前运行时转为小说级 runtime 配置快照，并强制 data_root 指向小说目录。"""
    out = dict(runtime_config)
    inner = out.get("runtime") or {}
    if not isinstance(inner, dict):
        inner = {}
    storage = inner.get("storage") or {}
    if not isinstance(storage, dict):
        storage = {}
    storage["data_root"] = str(novel_root)
    inner["storage"] = storage
    out["runtime"] = inner
    return out


def _finalize_draft_novel_identity(
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
    title: str,
    world_config: dict,
    characters_config: dict | None,
    novel_root: Path,
    old_slug: str,
) -> dict[str, str]:
    """将初稿目录重命名（若 slug 变化）、更新 meta 为 design_done，并写回配置。"""
    novels_root = _novels_root(project_root, runtime_config)
    novels_root.mkdir(parents=True, exist_ok=True)
    new_slug = slugify_title(title)
    if not new_slug:
        new_slug = old_slug
    target = novels_root / new_slug
    if target.resolve() != novel_root.resolve():
        if target.exists():
            i = 2
            base = new_slug
            while (novels_root / f"{base}-{i}").exists():
                i += 1
            new_slug = f"{base}-{i}"
            target = novels_root / new_slug
        novel_root.rename(target)
        novel_root = target

    meta = {
        "title": title.strip(),
        "slug": new_slug,
        "status": "design_done",
        "created_at": _now_iso(),
        "world_name": (world_config.get("world") or {}).get("name") or "",
    }
    prev = _read_yaml(novel_root / "meta.yaml")
    if isinstance(prev, dict) and prev.get("created_at"):
        meta["created_at"] = prev["created_at"]
    _write_yaml(novel_root / "meta.yaml", meta)
    _write_yaml(novel_root / "config" / "runtime.yaml", _build_novel_runtime_snapshot(runtime_config, novel_root))
    _write_yaml(novel_root / "config" / "world.yaml", world_config or {})
    _write_yaml(novel_root / "config" / "characters.yaml", characters_config or {"characters": []})

    idx_path = novels_root / "index.yaml"
    idx = _read_yaml(idx_path)
    novels = list(idx.get("novels") or [])
    novels = [n for n in novels if not (isinstance(n, dict) and n.get("slug") == old_slug)]
    novels.append(
        {
            "slug": new_slug,
            "title": title.strip(),
            "status": "design_done",
            "updated_at": _now_iso(),
        }
    )
    _write_yaml(idx_path, {"novels": novels})

    _write_yaml(
        config_dir / "current_novel.yaml",
        {"slug": new_slug, "title": title.strip(), "root": str(novel_root), "provisional": False},
    )
    return {"slug": new_slug, "title": title.strip(), "root": str(novel_root)}


def persist_novel_identity(
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
    title: str,
    world_config: dict,
    characters_config: dict | None = None,
) -> dict[str, str]:
    """落盘 meta/index/current_novel。返回 {slug, title, root}。"""
    novels_root = _novels_root(project_root, runtime_config)
    novels_root.mkdir(parents=True, exist_ok=True)

    existing = current_novel_root(config_dir)
    old_meta = _read_yaml(existing / "meta.yaml") if existing else {}
    if existing and (old_meta.get("status") or "").strip().lower() == "draft":
        old_slug = (old_meta.get("slug") or existing.name).strip()
        return _finalize_draft_novel_identity(
            config_dir=config_dir,
            project_root=project_root,
            runtime_config=runtime_config,
            title=title,
            world_config=world_config,
            characters_config=characters_config,
            novel_root=existing,
            old_slug=old_slug,
        )

    base_slug = slugify_title(title)
    slug = base_slug
    i = 2
    while (novels_root / slug).exists() and not (novels_root / slug / "meta.yaml").is_file():
        slug = f"{base_slug}-{i}"
        i += 1
    novel_root = novels_root / slug
    novel_root.mkdir(parents=True, exist_ok=True)

    meta = {
        "title": title.strip(),
        "slug": slug,
        "status": "design_done",
        "created_at": _now_iso(),
        "world_name": (world_config.get("world") or {}).get("name") or "",
    }
    _write_yaml(novel_root / "meta.yaml", meta)
    _write_yaml(novel_root / "config" / "runtime.yaml", _build_novel_runtime_snapshot(runtime_config, novel_root))
    _write_yaml(novel_root / "config" / "world.yaml", world_config or {})
    _write_yaml(novel_root / "config" / "characters.yaml", characters_config or {"characters": []})

    idx_path = novels_root / "index.yaml"
    idx = _read_yaml(idx_path)
    novels = list(idx.get("novels") or [])
    novels = [n for n in novels if not (isinstance(n, dict) and n.get("slug") == slug)]
    novels.append(
        {
            "slug": slug,
            "title": title.strip(),
            "status": "design_done",
            "updated_at": _now_iso(),
        }
    )
    _write_yaml(idx_path, {"novels": novels})

    _write_yaml(
        config_dir / "current_novel.yaml",
        {"slug": slug, "title": title.strip(), "root": str(novel_root), "provisional": False},
    )
    return {"slug": slug, "title": title.strip(), "root": str(novel_root)}


def confirm_title_and_persist(
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
    world_config: dict,
    characters_config: dict | None,
    special_settings: dict | None,
    input_fn: Any = None,
    log: Any = None,
) -> dict[str, str] | None:
    """
    交互确认书名并落盘。
    若已有 current_novel 且非初稿（draft），则直接返回 None（本轮不重复确认）。
    初稿（draft）时仍会进入命名，以正式书名替换初稿标题并可重命名目录。
    input_fn 宜传入 AuthorSession.read_line，与主流程作者在环统一读入一致。
    """
    if has_current_novel_pointer(config_dir) and not is_provisional_novel(config_dir):
        return None

    fn = input_fn or input
    from src.llm import call_with_user_retry

    def _generate_with_retry() -> list[dict[str, str]]:
        return call_with_user_retry(
            lambda: generate_title_candidates(runtime_config, world_config, special_settings, count=5),
            input_fn=fn,
            log=log,
            action_name="书名生成",
            attempts_per_round=3,
        )

    candidates = _generate_with_retry()
    while True:
        if log:
            log.info("======== 小说命名（设定完成后） ========")
            for i, c in enumerate(candidates, start=1):
                log.info("  %s) %s  —— %s", i, c["title"], c.get("reason", ""))
            log.info("========================================")
            log.info("请选择书名：输入序号(1~%s)；r=重新生成；m=手动输入", len(candidates))

        ans = (fn("书名选择（默认 1）：").strip() or "1").lower()
        if ans == "r":
            candidates = _generate_with_retry()
            continue
        if ans == "m":
            manual = fn("请输入书名：").strip()
            if not manual:
                if log:
                    log.info("书名为空，请重试。")
                continue
            out = persist_novel_identity(
                config_dir=config_dir,
                project_root=project_root,
                runtime_config=runtime_config,
                title=manual,
                world_config=world_config,
                characters_config=characters_config,
            )
            if log:
                log.info("已确认书名：%s（slug=%s）", out["title"], out["slug"])
            return out
        try:
            idx = int(ans)
        except ValueError:
            if log:
                log.info("输入无效，请重试。")
            continue
        if 1 <= idx <= len(candidates):
            chosen = candidates[idx - 1]["title"]
            out = persist_novel_identity(
                config_dir=config_dir,
                project_root=project_root,
                runtime_config=runtime_config,
                title=chosen,
                world_config=world_config,
                characters_config=characters_config,
            )
            if log:
                log.info("已确认书名：%s（slug=%s）", out["title"], out["slug"])
            return out
        if log:
            log.info("超出范围，请重试。")

