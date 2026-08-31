"""
G3 运行时镜头：可变、会话内持有的「导出镜头」上下文。

运行时镜头是**最终成文选择器**：决定「此刻哪条正篇变最终小说内容」，**不**约束演进层多角色独立演进——
成长/记忆/视野/关系边照常各自累积。切换是**前向**的（只影响后续回合成文），演进数据不动。
- `ProtagonistContext`：持当前 `protagonist_id`/`display_name`，可判 override。
- `effective_protagonist`：运行时 override > 配置期（委派 `resolve_protagonist_id`）。
- `switch_protagonist`：校验 target 存在于 characters 后再翻转（不在→WARN 原样）。
- 持久化 `state/protagonist_runtime.yaml`，跨回合/续读生效。

确定性、无 LLM。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.runtime.protagonist import resolve_protagonist_id

logger = logging.getLogger(__name__)


@dataclass
class ProtagonistContext:
    """会话内当前导出镜头。默认 None = 未 override（用配置期解析值）。"""

    protagonist_id: str | None = None
    display_name: str | None = None

    def is_override(self) -> bool:
        return bool(self.protagonist_id)


def effective_protagonist(
    runtime_config: dict[str, Any] | None,
    characters_config: dict[str, Any] | None,
    ctx: ProtagonistContext | None = None,
) -> tuple[str | None, str | None]:
    """统一镜头判定：ctx override 时取 ctx，否则委派配置期 `resolve_protagonist_id`。"""
    if ctx is not None and ctx.is_override():
        return ctx.protagonist_id, ctx.display_name
    return resolve_protagonist_id(runtime_config or {}, characters_config)


def switch_protagonist(
    ctx: ProtagonistContext,
    runtime_config: dict[str, Any] | None,
    characters_config: dict[str, Any] | None,
    target_id: str,
) -> tuple[str | None, str | None]:
    """
    把导出镜头切到 `target_id`。校验其存在于 `characters_config.characters[].id`：
    不存在→WARN 返回原镜头不变；存在→沿用 `protagonist.py` 显示名解析、更新 ctx，返回 `(id, name)`。
    """
    target = (target_id or "").strip()
    chars = (characters_config or {}).get("characters") or []
    ids = {str(c.get("id")) for c in chars if isinstance(c, dict) and c.get("id")}
    if target not in ids:
        logger.warning("[G3] 切换导出镜头失败：target_id=%s 不在 characters 配置中，镜头保持 %s", target, ctx.protagonist_id)
        return ctx.protagonist_id, ctx.display_name
    display = target
    for c in chars:
        if isinstance(c, dict) and c.get("id") == target:
            display = ((c.get("name") or "").strip() or target)
            break
    ctx.protagonist_id = target
    ctx.display_name = display
    logger.info("[G3] 运行时镜头切换 → 导出镜头=%s（%s）", target, display)
    return target, display


def format_lens_snippet(
    protagonist_id: str | None,
    display_name: str | None,
    characters_config: dict[str, Any] | None,
) -> str:
    """按**当前镜头**（显式 id/name）生成「主角与主要角色」提示块；无镜头→空串。

    与 `protagonist.format_main_characters_snippet` 同形、同约束（以叙事主角为镜头主轴、不得虚构/替换主角姓名），
    但可给**运行时** id/name —— 换镜头后重建同一路径。未改 `protagonist.py`。
    """
    pid, pname = protagonist_id or None, display_name or None
    if not pid or not pname:
        return ""
    chars = (characters_config or {}).get("characters") or []
    role = ""
    other_names: list[str] = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        name = (c.get("name") or "").strip()
        if not name:
            continue
        r = (c.get("role") or "").strip()
        if c.get("id") == pid:
            role = r
        elif name != pname:
            other_names.append(f"{name}（{r}）" if r else name)
    lines = ["【主角与主要角色】"]
    lines.append(f"- 叙事主角：{pname}（{role}）" if role else f"- 叙事主角：{pname}")
    if other_names:
        lines.append("- 主要角色：" + "、".join(other_names))
    lines.append(
        f"本回合叙述以叙事主角「{pname}」为镜头主轴：其姓名与身份须与上述一致，"
        "不得虚构或替换主角姓名；其他在场角色按上述名单称呼，未列出的次要角色可由剧情动态引入并写入次要角色列表。"
    )
    return "\n".join(lines)


def protagonist_runtime_yaml_path(data_root: Path | str) -> Path:
    """与 §4 一致：`<novel_root>/state/protagonist_runtime.yaml`。"""
    return Path(data_root) / "state" / "protagonist_runtime.yaml"


def load_protagonist_context(data_root: Path | str) -> ProtagonistContext:
    """读持久化镜头上下文；缺失/异常→空上下文（未 override）。"""
    path = protagonist_runtime_yaml_path(data_root)
    try:
        if not path.is_file():
            return ProtagonistContext()
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return ProtagonistContext()
        pid = (str(raw.get("protagonist_id") or "")).strip() or None
        if not pid:
            return ProtagonistContext()
        return ProtagonistContext(
            protagonist_id=pid,
            display_name=(str(raw.get("display_name") or "")).strip() or pid,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[G3] 读取 protagonist_runtime.yaml 失败，按未 override 处理：%s", exc)
        return ProtagonistContext()


def save_protagonist_context(data_root: Path | str, ctx: ProtagonistContext) -> Path | None:
    """写持久化镜头上下文（override 状态才写；非 override 不落盘）。"""
    if ctx is None or not ctx.is_override():
        return None
    root = Path(data_root)
    path = protagonist_runtime_yaml_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "protagonist_id": ctx.protagonist_id,
            "display_name": ctx.display_name,
            "override": True,
        }
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=True), encoding="utf-8")
        return path
    except Exception as exc:  # noqa: BLE001
        logger.warning("[G3] 写出 protagonist_runtime.yaml 失败：%s（%s）", path, exc)
        return None