"""叙事主角 id 解析：供大纲注入、正文主轴等 MVP-1 使用。"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def resolve_protagonist_id(
    runtime_config: dict[str, Any],
    characters_config: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    """
    返回 (protagonist_id, display_name)。
    优先级：runtime.novel_run.protagonist_id；否则唯一 is_protagonist 的角色 id。
    多个 is_protagonist 时：**当前仅支持单叙事主角**，会告警并暂用列表中第一个；**多主角尚未支持**，后续版本再考虑。
    id 不在 enabled_ids 时 WARN 仍返回。
    """
    inner = runtime_config.get("runtime") or runtime_config
    nr = inner.get("novel_run") or {}
    pid = (nr.get("protagonist_id") or "").strip() or None
    chars = (characters_config or {}).get("characters") or []
    flagged: list[str] = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        if c.get("is_protagonist"):
            cid = c.get("id")
            if cid:
                flagged.append(str(cid))
    if len(flagged) > 1:
        logger.warning(
            "characters 中多处 is_protagonist=%s：当前实现仅支持**单叙事主角**，多主角**未支持**、后续版本再议；"
            "本次暂用第一个 id=%s，请改为只保留一条 is_protagonist 或改用 novel_run.protagonist_id 显式指定。",
            flagged,
            flagged[0],
        )
    if not pid and flagged:
        pid = flagged[0]
    display: str | None = None
    if pid:
        for c in chars:
            if isinstance(c, dict) and c.get("id") == pid:
                display = ((c.get("name") or "").strip() or pid)
                break
        if not display:
            display = pid
        enabled = set(
            (runtime_config.get("agents") or {}).get("characters", {}).get("enabled_ids") or []
        )
        if enabled and pid not in enabled:
            logger.warning(
                "protagonist_id=%s 不在 agents.characters.enabled_ids 中，仍将注入叙事主角提示",
                pid,
            )
    return pid, display


def format_main_characters_snippet(
    runtime_config: dict[str, Any],
    characters_config: dict[str, Any] | None,
) -> str:
    """
    生成「主角与主要角色」提示块，供 ScopeAgent（主线叙事者）、写作前分析、正文生成注入，
    确保主线叙述使用配置的主角姓名，不虚构或替换。无主角或无角色配置时返回空串。
    与 docs/design/outline-and-beats.md「正文以主角为主线」一致，补齐 MVP-1 主角注入（不依赖大纲文件）。
    """
    pid, pname = resolve_protagonist_id(runtime_config, characters_config)
    if not pid:
        return ""
    chars = (characters_config or {}).get("characters") or []
    protagonist_role = ""
    other_names: list[str] = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        name = (c.get("name") or "").strip()
        if not name:
            continue
        role = (c.get("role") or "").strip()
        if c.get("id") == pid:
            protagonist_role = role
        elif name != pname:
            other_names.append(f"{name}（{role}）" if role else name)
    lines = ["【主角与主要角色】"]
    if protagonist_role:
        lines.append(f"- 叙事主角：{pname}（{protagonist_role}）")
    else:
        lines.append(f"- 叙事主角：{pname}")
    if other_names:
        lines.append("- 主要角色：" + "、".join(other_names))
    lines.append(
        f"本回合叙述以叙事主角「{pname}」为镜头主轴：其姓名与身份须与上述一致，"
        "不得虚构或替换主角姓名；其他在场角色按上述名单称呼，未列出的次要角色可由剧情动态引入并写入次要角色列表。"
    )
    return "\n".join(lines)
