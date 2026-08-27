"""
新小说启动引导：
- 检测“无设定 + 无正文”时判定为新小说；
- 自动准备最小 world/characters 配置骨架，避免首次启动因缺配置报错；
- 强制 setting_research 进入 design_only，引导作者先完成完整设定交互。
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from src.config import current_novel_root
from src.author_loop.novel_identity import (
    ensure_provisional_novel_directory,
    has_current_novel_pointer,
)


def _has_setting(config_dir: Path) -> bool:
    """是否已有设定产物或可恢复设定会话（仅认小说目录下的 setting_research_output，不认全局 config 下旧路径）。"""
    novel_root = current_novel_root(config_dir)
    sr = (novel_root / "config" / "setting_research_output.yaml") if novel_root else None
    if sr is not None and sr.is_file():
        try:
            data = yaml.safe_load(sr.read_text(encoding="utf-8")) or {}
            # 除基础字段外有任意设定方向即视为已有设定
            skip = {"world_id", "version", "genre", "theme", "reference"}
            for k, v in data.items():
                if k in skip:
                    continue
                if isinstance(v, dict) and (v.get("name") or v.get("description") or v.get("levels")):
                    return True
                if isinstance(v, (list, str)) and v:
                    return True
        except Exception:
            pass
    ds = config_dir / "design_session.yaml"
    if ds.is_file():
        try:
            data = yaml.safe_load(ds.read_text(encoding="utf-8")) or {}
            if data.get("session_file") or data.get("summary") or data.get("events"):
                return True
        except Exception:
            pass
    return False


def _has_body_events(project_root: Path, runtime_config: dict) -> bool:
    """是否已有正文事件（turn_*.md）。"""
    try:
        from src.runtime.file_sync import get_data_root
    except Exception:
        return False
    data_root = get_data_root(project_root, runtime_config)
    if not data_root:
        return False
    events_root = data_root / "book" / "events"
    if not events_root.is_dir():
        return False
    for _ in events_root.glob("*/events/turn_*.md"):
        return True
    return False


def _minimal_world(enabled_scope_ids: list[str]) -> dict[str, Any]:
    scopes = []
    for sid in enabled_scope_ids:
        scopes.append(
            {
                "id": sid,
                "name": sid,
                "description": "（待设定阶段完善）",
            }
        )
    return {
        "world": {
            "name": "",
            "era": "",
            "rules": [],
        },
        "time": {"start": ""},
        "scopes": scopes,
    }


def _minimal_characters(enabled_char_ids: list[str]) -> dict[str, Any]:
    chars = []
    for cid in enabled_char_ids:
        chars.append(
            {
                "id": cid,
                "name": cid,
                "role": "（待设定）",
                "traits": [],
                "goals": [],
                "background": "（待设定阶段完善）",
            }
        )
    return {"characters": chars}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _read_yaml_simple(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _force_design_only(config_dir: Path) -> None:
    """
    强制 setting_research 为 design_only（新小说必须先完成设定交互）。
    优先写 novel_writing.yaml（根层字段），不存在则回写 example_runtime.yaml.runtime。
    """
    nw = config_dir / "novel_writing.yaml"
    if nw.is_file():
        data = yaml.safe_load(nw.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            data = {}
        setting = data.get("setting_research") or {}
        if not isinstance(setting, dict):
            setting = {}
        setting["enabled"] = True
        setting["trigger"] = "design_only"
        data["setting_research"] = setting
        _write_yaml(nw, data)
        return

    rt = config_dir / "example_runtime.yaml"
    if rt.is_file():
        data = yaml.safe_load(rt.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            data = {}
        runtime = data.get("runtime") or {}
        if not isinstance(runtime, dict):
            runtime = {}
        setting = runtime.get("setting_research") or {}
        if not isinstance(setting, dict):
            setting = {}
        setting["enabled"] = True
        setting["trigger"] = "design_only"
        runtime["setting_research"] = setting
        data["runtime"] = runtime
        _write_yaml(rt, data)


def prepare_new_novel_if_needed(
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
    log: Any,
) -> bool:
    """
    若检测为新小说（无设定+无正文），准备最小配置骨架并强制进入设定阶段。
    返回 True 表示触发了新小说引导。
    """
    has_setting = _has_setting(config_dir)
    has_body = _has_body_events(project_root, runtime_config)
    if has_setting or has_body:
        return False

    enabled_char = list(runtime_config.get("agents", {}).get("characters", {}).get("enabled_ids", []))
    enabled_scope = list(runtime_config.get("agents", {}).get("scopes", {}).get("enabled_ids", []))

    _force_design_only(config_dir)
    if has_current_novel_pointer(config_dir):
        log.info(
            "检测到新小说（无设定且无正文），已切换为完整设定交互模式（design_only）；"
            "已绑定当前小说目录，跳过新建初稿（不写入全局 example_world/example_characters）。"
        )
        return True

    world_data = _minimal_world(enabled_scope)
    chars_data = _minimal_characters(enabled_char)
    ensure_provisional_novel_directory(
        config_dir=config_dir,
        project_root=project_root,
        runtime_config=runtime_config,
        world_config=world_data,
        characters_config=chars_data,
        log=log,
    )
    log.info(
        "检测到新小说（无设定且无正文），已切换为完整设定交互模式（design_only），"
        "并已在小说目录下创建初稿（书名可于设定完成后修改）。"
    )
    return True


def ensure_current_novel_for_design_phase(
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
    log: Any,
    world_config: dict,
    characters_config: dict,
) -> bool:
    """
    完整设定阶段（design_only）需要有效作品根目录，以便在 <novel>/config/ 落盘 setting_research_output 等。

    若已有有效 current_novel.root，返回 True。
    否则再次尝试 prepare_new_novel_if_needed；仍无则在不违反「已有正文却无指针」等约束时，
    用当前已加载的 world/characters 调用 ensure_provisional_novel_directory 创建初稿并绑定指针。

    返回 False 时调用方应退出或跳过设定阶段（并记录错误，提示用户修复 current_novel 或数据目录）。
    """
    if current_novel_root(config_dir):
        return True

    prepare_new_novel_if_needed(
        config_dir=config_dir,
        project_root=project_root,
        runtime_config=runtime_config,
        log=log,
    )
    if current_novel_root(config_dir):
        return True

    if has_current_novel_pointer(config_dir):
        log.error(
            "config/current_novel.yaml 已存在但 root 无效或目录不存在，无法进入设定阶段。"
            "请修正其中的 root 为有效作品目录后重试。"
        )
        return False

    if _has_body_events(project_root, runtime_config):
        log.error(
            "已检测到正文事件（turn_*.md），但未绑定有效作品目录；设定产出需写入小说目录。"
            "请恢复 config/current_novel.yaml 指向正确作品根，或调整 data 目录后再试。"
        )
        return False

    ensure_provisional_novel_directory(
        config_dir=config_dir,
        project_root=project_root,
        runtime_config=runtime_config,
        world_config=world_config,
        characters_config=characters_config,
        log=log,
    )
    if current_novel_root(config_dir):
        log.info("已为设定阶段创建初稿作品目录并绑定 current_novel。")
        return True
    log.error("创建初稿作品目录后仍无法解析 current_novel.root，请检查配置与权限。")
    return False


def bind_existing_novel_root(
    *,
    config_dir: Path,
    novel_root: Path,
    log: Any,
) -> bool:
    """
    将已有作品根目录写入 config/current_novel.yaml（读 meta.yaml 若存在）。
    """
    root = novel_root.expanduser().resolve()
    if not root.is_dir():
        if log:
            log.error("路径不存在或不是目录: %s", root)
        return False
    meta = _read_yaml_simple(root / "meta.yaml")
    slug = (str(meta.get("slug") or "").strip() or root.name)
    title = (str(meta.get("title") or "").strip() or root.name)
    st = (str(meta.get("status") or "").strip().lower())
    provisional = True if not st else st == "draft"
    _write_yaml(
        Path(config_dir) / "current_novel.yaml",
        {
            "slug": slug,
            "title": title,
            "root": str(root),
            "provisional": provisional,
        },
    )
    if log:
        log.info("已绑定当前作品目录: %s（slug=%s）", root, slug)
    return True


def interactive_resolve_novel_for_design_phase(
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict,
    world_config: dict,
    characters_config: dict,
    log: Any,
    input_fn: Callable[[str], str],
) -> bool:
    """
    当 ensure_current_novel_for_design_phase 失败时，与作者交互以新建初稿或绑定已有目录。

    典型场景：已有 data/.../book/events 正文，但缺少或未正确配置 current_novel。
    返回 True 表示已存在有效的 current_novel.root。
    """
    config_dir = Path(config_dir)
    fn = input_fn

    while True:
        if current_novel_root(config_dir):
            return True

        has_body = _has_body_events(project_root, runtime_config)
        ptr_bad = has_current_novel_pointer(config_dir) and not current_novel_root(config_dir)

        lines_intro = [
            "",
            "—— 需要先绑定「当前作品」目录 ——",
        ]
        if ptr_bad:
            lines_intro.append(
                "检测到 config/current_novel.yaml 存在，但其中的 root 不是有效目录。"
            )
        elif has_body:
            lines_intro.append(
                "检测到已有正文存档（如 data/.../book/events 下 turn_*.md），"
                "但未绑定有效作品根目录；设定产出必须写入当前作品目录。"
            )
        else:
            lines_intro.append("当前仍无法解析作品根目录，请选择下列操作之一。")
        lines_intro.extend(
            [
                "",
                "  1) 新建初稿：在 data/novels/ 下创建 draft-*，并写入 current_novel（推荐）",
                "  2) 绑定已有目录：输入作品根路径（该目录下通常应有 config/ 与 meta.yaml）",
                "  q) 退出",
                "",
                "请选择 [1 / 2 / q]：",
            ]
        )
        choice = fn("\n".join(lines_intro)).strip().lower()

        if choice in ("q", "quit", "退出"):
            if log:
                log.info("作者选择退出，未绑定作品目录。")
            return False

        if choice == "1":
            cn = config_dir / "current_novel.yaml"
            if cn.is_file():
                warn = (
                    "将删除现有 config/current_novel.yaml 并新建初稿（若选错请先选 q 退出）。"
                    "\n确认请输入 y："
                )
                if fn(warn).strip().lower() != "y":
                    continue
                cn.unlink(missing_ok=True)
            try:
                ensure_provisional_novel_directory(
                    config_dir=config_dir,
                    project_root=project_root,
                    runtime_config=runtime_config,
                    world_config=world_config,
                    characters_config=characters_config,
                    log=log,
                )
            except RuntimeError as e:
                if log:
                    log.error("新建初稿失败: %s", e)
                continue
            if current_novel_root(config_dir):
                if log:
                    log.info("已新建初稿并绑定 current_novel，可继续设定阶段。")
                return True
            if log:
                log.error("新建初稿后仍无法解析作品根，请检查权限与磁盘。")
            continue

        if choice == "2":
            path_str = fn(
                "请粘贴作品根目录的绝对路径（须为已存在的目录；回车返回菜单）："
            ).strip()
            if not path_str:
                continue
            candidate = Path(path_str)
            if bind_existing_novel_root(config_dir=config_dir, novel_root=candidate, log=log):
                if current_novel_root(config_dir):
                    return True
            continue

        if log:
            log.info("无效选择，请输入 1、2 或 q。")

