"""
设定阶段会话持久化：记录所有输出内容与用户输入，便于后续启动时增量续写与恢复。

book/setting 目录规划：
- setting/setting_config.yaml  设定方向配置，列出允许的设定方向 key（如 power_system, level_system）。
  仅在此列表中的方向会写入独立 .md；新增方向需在讨论归纳时经作者确认后加入。
- setting/<key>.md             各设定方向的独立文件（与 setting_config 中的 key 对应）。
- setting/sessions/            会话子目录，与方向 .md 分离。
  - session_<timestamp>.md      会话可读摘要
  - session_<timestamp>.yaml    会话可恢复数据（events + state_snapshot）

config/design_session.yaml 仅保存路径、摘要、theme/genre；完整会话写入 book/setting/sessions/。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DESIGN_SESSION_FILENAME = "design_session.yaml"
SESSION_MD_PREFIX = "session_"
# 会话文件统一放在 setting 下的子目录，与各方向 .md 分离
SESSION_SUBDIR = "sessions"
SETTING_CONFIG_FILENAME = "setting_config.yaml"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_summary(
    events: list[dict[str, Any]],
    world_lines: list[str],
    scopes_lines: list[str],
    characters_lines: list[str],
    special_lines: list[str],
) -> None:
    """记录一次「设定审阅」的完整输出（世界/范围/角色/特殊设定摘要）。"""
    events.append({
        "type": "summary",
        "timestamp": _now_iso(),
        "world": world_lines,
        "scopes": scopes_lines,
        "characters": characters_lines,
        "special": special_lines,
    })


def append_menu_choice(events: list[dict[str, Any]], choice: str) -> None:
    """记录一次主菜单选择。"""
    events.append({"type": "menu", "choice": choice, "timestamp": _now_iso()})


def append_discussion(
    events: list[dict[str, Any]],
    initial_message: str,
    rounds: list[tuple[str, str]],
    extracted_directions: list[str] | None = None,
) -> None:
    """记录一整段自由讨论：初始想法、每轮作者输入与 Agent 完整回复、归纳到的方向。"""
    events.append({
        "type": "discussion",
        "timestamp": _now_iso(),
        "initial_message": initial_message,
        "rounds": [{"author": a, "agent": b} for a, b in rounds],
        "extracted_directions": extracted_directions or [],
    })


def append_supplement(events: list[dict[str, Any]], ref_line: str) -> None:
    """记录一次补充说明输入。"""
    events.append({"type": "supplement", "reference": ref_line, "timestamp": _now_iso()})


def _session_to_markdown(events: list[dict[str, Any]], state_snapshot: dict[str, Any]) -> str:
    """将 events 与 state_snapshot 转为可读 MD。"""
    lines = ["# 设定会话", ""]
    for i, ev in enumerate(events):
        t = ev.get("type", "")
        ts = ev.get("timestamp", "")
        lines.append(f"## [{i+1}] {t} {ts}")
        if t == "summary":
            for key in ("world", "scopes", "characters", "special"):
                if key in ev and ev[key]:
                    lines.append(f"### {key}")
                    lines.extend(f"- {line}" for line in ev[key][:20])
                    if len(ev.get(key, [])) > 20:
                        lines.append("- ...")
                    lines.append("")
        elif t == "menu":
            lines.append(f"- choice: {ev.get('choice', '')}")
        elif t == "supplement":
            lines.append(f"- reference: {ev.get('reference', '')}")
        elif t == "discussion":
            lines.append(f"- initial: {ev.get('initial_message', '')}")
            for r in ev.get("rounds", []):
                lines.append(f"- **作者**：\n{r.get('author', '')}\n")
                lines.append(f"- **设定 Agent**：\n{r.get('agent', '')}\n")
            lines.append(f"- extracted_directions: {ev.get('extracted_directions', [])}")
        lines.append("")
    if state_snapshot:
        lines.append("## state_snapshot")
        lines.append("")
        for k, v in state_snapshot.items():
            if k == "current_discussion" and isinstance(v, dict):
                lines.append("### current_discussion")
                lines.append(f"- initial_message: {v.get('initial_message', '')}")
                for r in v.get("rounds", []):
                    lines.append(f"- 作者：{r.get('author', '')}")
                    lines.append(f"  Agent：{r.get('agent', '')}")
            elif isinstance(v, list):
                lines.extend(f"- {line}" for line in v[:15])
            else:
                lines.append(f"- {k}: {str(v)[:200]}...")
            lines.append("")
    return "\n".join(lines).strip()


def save_session(
    config_dir: Path,
    *,
    theme: str = "",
    genre: str = "",
    events: list[dict[str, Any]],
    state_snapshot: dict[str, Any] | None = None,
    project_root: Path | None = None,
    runtime_config: dict | None = None,
) -> Path:
    """
    配置文件仅写入最关键信息（路径、摘要、theme/genre）；    完整内容写入 book/setting/sessions/session_<timestamp>.md（及 .yaml）。
    若未配置 data_root 或无法解析 book_root，则仍将完整 payload 写入 config_dir/design_session.yaml（兼容）。
    """
    logger.debug("[设定讨论] save_session: 开始, events 条数=%s", len(events))
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    now = _now_iso()
    state_snapshot = state_snapshot or {}

    session_file_rel: str | None = None
    book_root: Path | None = None
    if project_root is not None:
        if runtime_config is not None:
            try:
                from src.runtime.file_sync import get_book_root
                book_root = get_book_root(Path(project_root), runtime_config)
            except Exception:
                pass
        if not book_root:
            book_root = Path(project_root) / "data" / "book"
    logger.debug("[设定讨论] save_session: book_root=%s", book_root)
    if book_root:
        setting_dir = book_root / "setting"
        session_dir = setting_dir / SESSION_SUBDIR
        session_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        session_md_name = f"{SESSION_MD_PREFIX}{ts}.md"
        session_md_path = session_dir / session_md_name
        session_file_rel = f"book/setting/{SESSION_SUBDIR}/{session_md_name}"
        logger.debug("[设定讨论] save_session: 写入会话 sessions/%s", session_md_name)
        md_content = _session_to_markdown(events, state_snapshot)
        session_md_path.write_text(md_content, encoding="utf-8")
        logger.info("设定会话完整内容已写入: %s", session_md_path)
        session_data_name = f"{SESSION_MD_PREFIX}{ts}.yaml"
        session_data_path = session_dir / session_data_name
        try:
            with open(session_data_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    {"events": events, "state_snapshot": state_snapshot},
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
            logger.debug("设定会话可恢复数据已写入: %s", session_data_path)
        except Exception as e:
            logger.warning("写入 session 数据文件失败 %s: %s", session_data_path, e)

    summary = f"theme={theme!r} genre={genre!r} events={len(events)}"
    if events:
        last = events[-1]
        if last.get("type") == "discussion":
            summary = f"最近为讨论，{len(last.get('rounds', []))} 轮"
        elif last.get("type") == "summary":
            summary = "最近为设定审阅摘要"

    payload_minimal = {
        "version": 2,
        "session_start": events[0]["timestamp"] if events else now,
        "last_updated": now,
        "theme": theme,
        "genre": genre,
        "summary": summary,
    }
    if session_file_rel:
        payload_minimal["session_file"] = session_file_rel
    else:
        payload_minimal["events"] = events
        payload_minimal["state_snapshot"] = state_snapshot

    path = config_dir / DESIGN_SESSION_FILENAME
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(payload_minimal, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    logger.info("设定会话已持久化到: %s", path)
    return path


def _parse_session_md_for_state_snapshot(md_path: Path) -> dict[str, Any]:
    """
    从 session 的 .md 文件中解析出 state_snapshot（主要含 current_discussion），
    用于仅有 .md、无 .yaml 的已迁移会话仍可恢复讨论。
    """
    if not md_path.is_file():
        return {}
    text = md_path.read_text(encoding="utf-8")
    out: dict[str, Any] = {}
    if "## state_snapshot" not in text or "### current_discussion" not in text:
        return out
    try:
        in_snapshot = False
        in_discussion = False
        initial_message = ""
        rounds: list[dict[str, str]] = []
        current_author = ""
        current_agent: list[str] = []
        in_agent_block = False
        lines = text.split("\n")
        for line in lines:
            if line.strip() == "## state_snapshot":
                in_snapshot = True
                continue
            if not in_snapshot:
                continue
            if line.strip() == "### current_discussion":
                in_discussion = True
                continue
            if not in_discussion:
                continue
            if line.startswith("- initial_message:"):
                initial_message = line.split(":", 1)[-1].strip()
                in_agent_block = False
                continue
            if line.startswith("- 作者："):
                in_agent_block = False
                if current_author and current_agent:
                    rounds.append({"author": current_author, "agent": "\n".join(current_agent).strip()})
                current_author = line.split("：", 1)[-1].strip()
                current_agent = []
                continue
            if line.startswith("  Agent："):
                in_agent_block = True
                current_agent.append(line.split("：", 1)[-1].strip())
                continue
            if in_agent_block and current_agent:
                current_agent.append(line)
        if current_author and current_agent:
            rounds.append({"author": current_author, "agent": "\n".join(current_agent).strip()})
        if initial_message or rounds:
            out["current_discussion"] = {"initial_message": initial_message, "rounds": rounds}
    except Exception as e:
        logger.debug("解析 session MD 的 state_snapshot 失败 %s: %s", md_path, e)
    return out


def load_session(config_dir: Path) -> dict[str, Any] | None:
    """加载已有设定会话索引（若存在）；含 session_file 时可据此再读完整 MD。"""
    path = Path(config_dir) / DESIGN_SESSION_FILENAME
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or None
    except Exception as e:
        logger.warning("加载设定会话失败 %s: %s", path, e)
        return None


def _backfill_current_discussion(events: list, state_snapshot: dict) -> None:
    """若 state_snapshot 未包含 current_discussion 键，则从 events 中最后一条 type=discussion 的事件回填。
    若键已存在（含归档后显式置为 null），则不再回填，避免满意→保存/校准→归档后重启仍提示未完成讨论。"""
    if not events:
        return
    if "current_discussion" in state_snapshot:
        return
    last_discussion = None
    for ev in reversed(events):
        if ev.get("type") == "discussion":
            last_discussion = ev
            break
    if not last_discussion:
        return
    state_snapshot["current_discussion"] = {
        "initial_message": last_discussion.get("initial_message", ""),
        "rounds": last_discussion.get("rounds", []),
    }


def load_session_full(
    config_dir: Path,
    project_root: Path | None = None,
    runtime_config: dict | None = None,
) -> dict[str, Any] | None:
    """
    加载完整会话用于恢复：返回 { "events": list, "state_snapshot": dict }，便于续写与恢复讨论。
    - version 2：根据 session_file 推导同名的 .yaml 数据文件（book/setting/session_<ts>.yaml）并加载。
    - version 1 或配置中仍含 events：直接从 config 返回 events 与 state_snapshot。
    - 若 state_snapshot 无 current_discussion 但 events 最后一条为 discussion，则自动回填以便「继续上次对话」。
    """
    config_dir = Path(config_dir)
    index = load_session(config_dir)
    logger.debug("[设定讨论] load_session_full: index=%s", "有" if index else "无")
    if not index:
        return None
    if index.get("version") == 2 and index.get("session_file"):
        session_file = index["session_file"]
        base = Path(session_file).stem
        logger.debug("[设定讨论] load_session_full: version=2, session_file=%s, base=%s", session_file, base)
        book_root = None
        if project_root is not None and runtime_config is not None:
            try:
                from src.runtime.file_sync import get_book_root
                book_root = get_book_root(Path(project_root), runtime_config)
            except Exception:
                pass
        if not book_root:
            book_root = Path(project_root) if project_root else config_dir.parent
            book_root = book_root / "data" / "book"
        # 先尝试 sessions 子目录（新布局），再尝试 setting 根下（旧布局）
        data_path = book_root / "setting" / SESSION_SUBDIR / f"{base}.yaml"
        if not data_path.is_file():
            data_path = book_root / "setting" / f"{base}.yaml"
        md_path = book_root / "setting" / SESSION_SUBDIR / f"{base}.md"
        if not md_path.is_file():
            md_path = book_root / "setting" / f"{base}.md"
        logger.debug("[设定讨论] load_session_full: data_path=%s 存在=%s, md_path=%s 存在=%s",
                     data_path, data_path.is_file(), md_path, md_path.is_file())
        if data_path.is_file():
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                events = data.get("events") or []
                state_snapshot = data.get("state_snapshot") or {}
                logger.debug("[设定讨论] load_session_full: 从 yaml 加载 events=%s 条, state_snapshot keys=%s", len(events), list(state_snapshot.keys()))
                _backfill_current_discussion(events, state_snapshot)
                if state_snapshot.get("current_discussion"):
                    logger.debug("[设定讨论] load_session_full: 回填或已有 current_discussion")
                return {"events": events, "state_snapshot": state_snapshot}
            except Exception as e:
                logger.warning("读取 session 数据文件失败 %s: %s", data_path, e)
        if md_path.is_file():
            logger.debug("[设定讨论] load_session_full: 从 .md 解析 state_snapshot")
            state_snapshot = _parse_session_md_for_state_snapshot(md_path)
            if state_snapshot:
                return {"events": [], "state_snapshot": state_snapshot}
        logger.debug("[设定讨论] load_session_full: 未找到会话数据文件，返回 None")
        return None
    if "events" in index:
        events = index.get("events") or []
        state_snapshot = index.get("state_snapshot") or {}
        logger.debug("[设定讨论] load_session_full: 从 config 直接加载 events=%s 条", len(events))
        _backfill_current_discussion(events, state_snapshot)
        return {"events": events, "state_snapshot": state_snapshot}
    return None


def migrate_session_to_new_storage(
    config_dir: Path,
    project_root: Path | None = None,
) -> Path | None:
    """
    将旧版 design_session.yaml（version 1，含完整 events/state_snapshot）迁移到新方案：
    完整内容写入 book/setting/session_<timestamp>.md，配置文件仅保留路径与摘要。
    若未配置 data_root，则使用 project_root/data/book/setting 作为落盘目录。
    返回写入的 session MD 路径；无需迁移时返回 None。
    """
    config_dir = Path(config_dir)
    path = config_dir / DESIGN_SESSION_FILENAME
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("读取设定会话失败 %s: %s", path, e)
        return None
    if data.get("version") != 1 or "events" not in data:
        return None
    events = data.get("events") or []
    state_snapshot = data.get("state_snapshot") or {}
    theme = data.get("theme", "")
    genre = data.get("genre", "")
    last_updated = data.get("last_updated", _now_iso())
    session_start = data.get("session_start", last_updated)

    project_root = Path(project_root) if project_root else config_dir.parent
    book_root: Path | None = None
    try:
        from src.config import load_runtime_config
        runtime_config = load_runtime_config(config_dir)
        from src.runtime.file_sync import get_book_root
        book_root = get_book_root(project_root, runtime_config)
    except Exception:
        pass
    if not book_root:
        book_root = project_root / "data" / "book"
    session_dir = book_root / "setting" / SESSION_SUBDIR
    session_dir.mkdir(parents=True, exist_ok=True)
    try:
        dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        ts = dt.strftime("%Y%m%d_%H%M%S")
    except Exception:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    session_md_name = f"{SESSION_MD_PREFIX}{ts}.md"
    session_md_path = session_dir / session_md_name
    md_content = _session_to_markdown(events, state_snapshot)
    session_md_path.write_text(md_content, encoding="utf-8")
    session_file_rel = f"book/setting/{SESSION_SUBDIR}/{session_md_name}"

    summary = f"theme={theme!r} genre={genre!r}，已迁移 {len(events)} 条事件至 {session_file_rel}"
    payload_minimal = {
        "version": 2,
        "session_start": session_start,
        "last_updated": last_updated,
        "theme": theme,
        "genre": genre,
        "summary": summary,
        "session_file": session_file_rel,
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(payload_minimal, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    logger.info("已迁移设定会话：完整内容 -> %s，配置 -> 仅路径与摘要", session_md_path)
    return session_md_path


# ---------- 设定方向配置（book/setting/setting_config.yaml）----------
# 各方向 .md 由配置驱动：仅配置中列出的方向会写入独立 .md；新增方向需作者确认后加入配置。


def _setting_config_path(book_root: Path) -> Path:
    """book/setting/setting_config.yaml 的完整路径。"""
    return Path(book_root) / "setting" / SETTING_CONFIG_FILENAME


def load_setting_directions_config(book_root: Path | None) -> list[str]:
    """
    读取设定方向配置，返回已启用的方向 key 列表。
    若文件不存在或为空，返回空列表（调用方可用默认或现有 special 的 key 做引导）。
    """
    if not book_root:
        logger.debug("[设定讨论] load_setting_directions_config: 无 book_root")
        return []
    path = _setting_config_path(book_root)
    if not path.is_file():
        logger.debug("[设定讨论] load_setting_directions_config: 配置文件不存在 path=%s", path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        directions = data.get("directions")
        if isinstance(directions, list):
            out = [str(k) for k in directions if k]
            logger.debug("[设定讨论] load_setting_directions_config: 已加载 directions=%s", out)
            return out
        return []
    except Exception as e:
        logger.warning("读取设定方向配置失败 %s: %s", path, e)
        return []


def ensure_setting_directions_config(
    book_root: Path | None,
    default_directions: list[str],
) -> list[str]:
    """
    若 setting_config.yaml 不存在，则创建并写入 default_directions，返回当前方向列表；
    若已存在则直接返回文件中的方向列表。
    """
    if not book_root:
        return list(default_directions) if default_directions else []
    path = _setting_config_path(book_root)
    if path.is_file():
        logger.debug("[设定讨论] ensure_setting_directions_config: 配置已存在，直接加载")
        return load_setting_directions_config(book_root)
    logger.debug("[设定讨论] ensure_setting_directions_config: 创建新配置 default_directions=%s", default_directions)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"directions": list(default_directions) if default_directions else []}
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info("已创建设定方向配置: %s", path)
    except Exception as e:
        logger.warning("写入设定方向配置失败 %s: %s", path, e)
    return data.get("directions", [])


def add_setting_direction(book_root: Path | None, key: str) -> bool:
    """将方向 key 追加到设定配置并写回；若已在列表中则不变。返回是否实际修改。"""
    if not book_root or not key:
        return False
    path = _setting_config_path(book_root)
    current = load_setting_directions_config(book_root)
    logger.debug("[设定讨论] add_setting_direction: key=%s, current=%s", key, current)
    if key in current:
        return False
    current.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump({"directions": current}, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info("已增加设定方向: %s -> %s", key, path)
        return True
    except Exception as e:
        logger.warning("追加设定方向失败 %s: %s", path, e)
        return False
