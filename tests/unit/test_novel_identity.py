from pathlib import Path

import yaml
import pytest

from src.author_loop import novel_identity as ni
from src.author_loop.novel_identity import (
    generate_title_candidates,
    persist_novel_identity,
    slugify_title,
)


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def test_slugify_title():
    assert slugify_title("  末法 村志  ") == "末法-村志"
    assert slugify_title("!!!") == "novel"


def test_synopsis_round_trip_and_truncate(tmp_path: Path):
    """read_synopsis/write_synopsis 读写 meta.yaml，非空截断 500 字。"""
    novel_root = tmp_path / "novel"
    novel_root.mkdir(parents=True)
    _write_yaml(novel_root / "meta.yaml", {"slug": "alpha", "title": "火星", "status": "draft"})
    assert ni.read_synopsis(novel_root) == ""  # 缺省空
    long = "字" * 600
    ni.write_synopsis(novel_root, long)
    assert len(ni.read_synopsis(novel_root)) == 500
    ni.write_synopsis(novel_root, "  近未来火星殖民  ")
    assert ni.read_synopsis(novel_root) == "近未来火星殖民"
    # write 空串 → 存空
    ni.write_synopsis(novel_root, "   ")
    assert ni.read_synopsis(novel_root) == ""


def test_finalize_draft_preserves_synopsis(tmp_path: Path):
    """初稿确认书名（_finalize_draft_novel_identity）整表重建 meta 时保留既有 synopsis。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    data = tmp_path / "data"
    novels_root = data / "novels"
    novels_root.mkdir(parents=True)
    slug = "draft-preserve"
    novel_root = novels_root / slug
    novel_root.mkdir(parents=True)
    (novel_root / "config").mkdir(parents=True)
    _write_yaml(
        novel_root / "meta.yaml",
        {"title": "（初稿）待命名", "slug": slug, "status": "draft",
         "created_at": "2026-01-01T00:00:00Z", "synopsis": "近未来火星殖民官场"},
    )
    _write_yaml(
        config_dir / "current_novel.yaml",
        {"slug": slug, "title": "（初稿）待命名", "root": str(novel_root), "provisional": True},
    )
    runtime = {"runtime": {"storage": {"data_root": str(data)}}}
    out = persist_novel_identity(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config=runtime,
        title="火星官场",
        world_config={"world": {"name": "火星殖民"}},
        characters_config={"characters": [{"id": "方舟"}]},
    )
    root = Path(out["root"])
    meta = yaml.safe_load((root / "meta.yaml").read_text(encoding="utf-8")) or {}
    assert meta.get("status") == "design_done"
    assert meta.get("synopsis") == "近未来火星殖民官场"


def test_persist_novel_identity_finalizes_draft(tmp_path: Path):
    """初稿目录（draft）上确认书名时更新 meta / 可能重命名目录。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    data = tmp_path / "data"
    novels_root = data / "novels"
    novels_root.mkdir(parents=True)
    slug = "draft-testonly"
    novel_root = novels_root / slug
    novel_root.mkdir(parents=True)
    (novel_root / "config").mkdir(parents=True)
    _write_yaml(
        novel_root / "meta.yaml",
        {"title": "（初稿）待命名", "slug": slug, "status": "draft", "created_at": "2026-01-01T00:00:00Z"},
    )
    _write_yaml(
        config_dir / "current_novel.yaml",
        {
            "slug": slug,
            "title": "（初稿）待命名",
            "root": str(novel_root),
            "provisional": True,
        },
    )
    runtime = {"runtime": {"storage": {"data_root": str(data)}}}
    out = persist_novel_identity(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config=runtime,
        title="末法村志",
        world_config={"world": {"name": "青石世界"}},
        characters_config={"characters": [{"id": "张凡"}]},
    )
    assert out["title"] == "末法村志"
    root = Path(out["root"])
    meta = yaml.safe_load((root / "meta.yaml").read_text(encoding="utf-8")) or {}
    assert meta.get("status") == "design_done"
    assert meta.get("title") == "末法村志"
    cur = yaml.safe_load((config_dir / "current_novel.yaml").read_text(encoding="utf-8")) or {}
    assert cur.get("provisional") is False


def test_persist_novel_identity_writes_meta_and_index(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    runtime = {"runtime": {"storage": {"data_root": str(tmp_path / "data")}}}
    world = {"world": {"name": "青石世界"}}

    out = persist_novel_identity(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config=runtime,
        title="末法村志",
        world_config=world,
        characters_config={"characters": [{"id": "张凡"}]},
    )

    novel_root = Path(out["root"])
    assert (novel_root / "meta.yaml").is_file()
    meta = yaml.safe_load((novel_root / "meta.yaml").read_text(encoding="utf-8")) or {}
    assert meta.get("title") == "末法村志"
    assert meta.get("slug") == out["slug"]
    assert (config_dir / "current_novel.yaml").is_file()
    idx = yaml.safe_load((tmp_path / "data" / "novels" / "index.yaml").read_text(encoding="utf-8")) or {}
    assert any((n.get("slug") == out["slug"]) for n in (idx.get("novels") or []))
    assert (novel_root / "config" / "runtime.yaml").is_file()
    rt_cfg = yaml.safe_load((novel_root / "config" / "runtime.yaml").read_text(encoding="utf-8")) or {}
    data_root = (((rt_cfg.get("runtime") or {}).get("storage") or {}).get("data_root") or "")
    assert str(novel_root) == data_root


def test_generate_title_candidates_raise_when_dummy_llm():
    runtime = {"framework": {"llm": "dummy"}}
    world = {"world": {"name": "青石世界", "era": "末法时代"}, "scopes": []}
    with pytest.raises(RuntimeError, match="生成书名需要可用 LLM"):
        generate_title_candidates(runtime, world, None, count=5)


class _Log:
    def warning(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None


def test_confirm_title_retry_three_then_ask_continue(monkeypatch, tmp_path: Path):
    calls = {"n": 0}

    def _always_fail(*args, **kwargs):
        calls["n"] += 1
        raise RuntimeError("llm error")

    monkeypatch.setattr(ni, "generate_title_candidates", _always_fail)
    # 连续失败 3 次后询问，输入 n 终止
    answers = iter(["n"])
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    runtime = {"runtime": {"storage": {"data_root": str(tmp_path / "data")}}, "framework": {"llm": "openai"}}
    world = {"world": {"name": "青石世界"}}
    with pytest.raises(RuntimeError, match="连续重试后仍失败"):
        ni.confirm_title_and_persist(
            config_dir=config_dir,
            project_root=tmp_path,
            runtime_config=runtime,
            world_config=world,
            characters_config={"characters": [{"id": "a"}]},
            special_settings=None,
            input_fn=lambda _: next(answers),
            log=_Log(),
        )
    assert calls["n"] == 3

