"""
记忆与内容目录双写：按 docs/design/memory-storage-and-retrieval.md 将小说相关输出统一到 data_root/book/ 下。
一级目录 book，二级目录：content（内容）、setting（设定）、characters（人物）、events（事件）。
与 MemoryStorage 并存（方案 B 双写）；data_root 由 runtime.storage.data_root 配置，未配置则不写入。
"""
from pathlib import Path
from typing import Any

# book 下二级目录名（内容、设定、人物、事件）
BOOK_CONTENT = "content"
BOOK_SETTING = "setting"
BOOK_CHARACTERS = "characters"
BOOK_EVENTS = "events"


def _safe_dir_name(name: str) -> str:
    """目录名安全化：替换路径分隔符。"""
    return (name or "unknown").replace("/", "_").replace("\\", "_").strip() or "unknown"


def get_data_root(project_root: Path, runtime_config: dict) -> Path | None:
    """
    从配置读取 data_root。runtime_config 可为整份配置或 runtime 段；
    若 storage.data_root 存在且非空则返回 project_root / 该值，否则返回 None。
    """
    inner = runtime_config.get("runtime") or runtime_config
    storage = inner.get("storage") or {}
    root = storage.get("data_root") or storage.get("novel_data_root")
    if not root:
        return None
    path = Path(root)
    if not path.is_absolute():
        path = Path(project_root) / path
    return path


def get_book_root(project_root: Path, runtime_config: dict) -> Path | None:
    """在 data_root 存在时返回 book 一级目录路径（data_root/book），供内容/设定/人物/事件统一落盘。"""
    data_root = get_data_root(project_root, runtime_config)
    return (data_root / "book") if data_root else None


def next_turn_index(data_root: Path) -> int:
    """读取并递增回合计数器，返回本回合序号（从 1 开始）。计数器放在 data_root 根，与 book/ 布局共用。"""
    counter_file = data_root / ".turn_counter"
    data_root.mkdir(parents=True, exist_ok=True)
    try:
        n = int(counter_file.read_text(encoding="utf-8").strip() or "0")
    except (FileNotFoundError, ValueError):
        n = 0
    n += 1
    counter_file.write_text(str(n), encoding="utf-8")
    return n


def write_turn_content(
    data_root: Path,
    turn_index: int,
    scope_id: str,
    time: str,
    place: str,
    resolved_summary: str,
    character_outputs: dict[str, dict],
) -> None:
    """写入本回合小说主体内容到 book/content/turns/turn_NNNN.md（含 frontmatter 与正文）。"""
    book_root = data_root / "book"
    book_root.mkdir(parents=True, exist_ok=True)
    turns_dir = book_root / BOOK_CONTENT / "turns"
    turns_dir.mkdir(parents=True, exist_ok=True)
    name = f"turn_{turn_index:04d}.md"
    path = turns_dir / name
    lines = [
        "---",
        f"scope_id: {scope_id!r}",
        f"time: {time!r}",
        f"place: {place!r}",
        f"turn_index: {turn_index}",
        "---",
        "",
        resolved_summary or "（本回合无摘要）",
        "",
    ]
    for cid in sorted(character_outputs.keys()):
        out = character_outputs[cid]
        action = (out.get("dialogue_action") or out.get("inner_monologue") or "").strip()
        if action:
            lines.append(f"- **{cid}**：{action}")
    path.write_text("\n".join(lines), encoding="utf-8")
    _append_content_turns_readme(turns_dir, name)


def _append_content_turns_readme(turns_dir: Path, new_name: str) -> None:
    """在 content/turns/README.md 中追加新回合文件名（若不存在则创建）。"""
    readme = turns_dir / "README.md"
    if not readme.is_file():
        readme.write_text("# turns\n\n按回合存储，每文件为一回合叙述。\n\n", encoding="utf-8")
    body = readme.read_text(encoding="utf-8")
    if new_name not in body:
        readme.write_text(body.rstrip() + f"\n- {new_name}\n", encoding="utf-8")


def sync_scope_turn(
    data_root: Path,
    scope_id: str,
    turn_index: int,
    event_entry: dict,
    state: dict,
) -> None:
    """将本回合范围事件与状态写入 book/events/<scope_id>/events/turn_NNNN.md 与 state.md。正文仅此一处持久化，展示时从记忆（storage）读取。"""
    book_root = data_root / "book"
    book_root.mkdir(parents=True, exist_ok=True)
    sid = _safe_dir_name(scope_id)
    scope_dir = book_root / BOOK_EVENTS / sid
    events_dir = scope_dir / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    name = f"turn_{turn_index:04d}.md"
    summary = event_entry.get("summary", str(event_entry))
    body = event_entry.get("body", "")
    time_str = event_entry.get("time", "")
    place_str = event_entry.get("place", "")
    meta = f"scope_id: {scope_id!r}\ntime: {time_str!r}\nplace: {place_str!r}\n"
    if body and body.strip():
        content = f"# 回合 {turn_index}\n\n{meta}\n## 摘要\n\n{summary}\n\n## 正文\n\n{body}\n"
    else:
        content = f"# 回合 {turn_index}\n\n{meta}\n## 摘要\n\n{summary}\n"
    (events_dir / name).write_text(content, encoding="utf-8")
    (scope_dir / "state.md").write_text(
        f"# 范围状态\n\n```yaml\n{_dict_to_yaml_like(state)}\n```\n",
        encoding="utf-8",
    )
    _append_events_readme(events_dir, name)


def sync_character_turn(
    data_root: Path,
    character_id: str,
    turn_index: int,
    refinement_entry: dict,
) -> None:
    """将本回合角色事件提炼写入 book/characters/<id>/events/turn_NNNN.md。"""
    book_root = data_root / "book"
    book_root.mkdir(parents=True, exist_ok=True)
    cid = _safe_dir_name(character_id)
    char_dir = book_root / BOOK_CHARACTERS / cid
    events_dir = char_dir / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    name = f"turn_{turn_index:04d}.md"
    summary = refinement_entry.get("summary", str(refinement_entry))
    (events_dir / name).write_text(f"# 回合 {turn_index}\n\n{summary}\n", encoding="utf-8")
    _append_events_readme(events_dir, name)


def _dict_to_yaml_like(d: dict) -> str:
    """简单 dict 转多行键值文本。"""
    if not d:
        return ""
    return "\n".join(f"{k}: {v!r}" for k, v in d.items())


def _append_events_readme(events_dir: Path, new_name: str) -> None:
    """在 events/README.md 中追加新回合文件名。"""
    readme = events_dir / "README.md"
    if not readme.is_file():
        readme.write_text("# events\n\n按回合列出 turn_*.md。\n\n", encoding="utf-8")
    body = readme.read_text(encoding="utf-8")
    if new_name not in body:
        readme.write_text(body.rstrip() + f"\n- {new_name}\n", encoding="utf-8")


def _parse_turn_md_content(text: str, scope_id: str, turn_index: int) -> dict:
    """从单回合 md 文本解析出 summary、body、time、place，兼容「# 回合 N + 摘要 + ## 正文」与旧版纯摘要格式。"""
    event: dict = {
        "summary": "",
        "body": "",
        "scope_id": scope_id,
        "time": "",
        "place": "",
    }
    lines = text.splitlines()
    i = 0
    after_meta = []
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("scope_id:") or stripped.startswith("scope_id："):
            event["scope_id"] = line.split(":", 1)[-1].split("：", 1)[-1].strip().strip("'\"") or scope_id
        elif stripped.startswith("time:") or stripped.startswith("time："):
            event["time"] = line.split(":", 1)[-1].split("：", 1)[-1].strip().strip("'\"")
        elif stripped.startswith("place:") or stripped.startswith("place："):
            event["place"] = line.split(":", 1)[-1].split("：", 1)[-1].strip().strip("'\"")
        elif stripped == "## 摘要":
            i += 1
            summary_parts = []
            while i < len(lines) and not lines[i].strip().startswith("##"):
                summary_parts.append(lines[i])
                i += 1
            event["summary"] = "\n".join(summary_parts).strip()
            continue
        elif stripped == "## 正文":
            i += 1
            body_parts = []
            while i < len(lines):
                body_parts.append(lines[i])
                i += 1
            event["body"] = "\n".join(body_parts).strip()
            break
        elif stripped and not stripped.startswith("# ") and "## " not in stripped:
            after_meta.append(line)
        i += 1
    if not event["summary"] and after_meta:
        event["summary"] = "\n".join(after_meta).strip() or text.strip()[:500]
    if not event["summary"]:
        event["summary"] = text.strip()[:500] or "（无摘要）"
    return event


def load_scope_events_from_disk(data_root: Path, scope_id: str) -> list[dict]:
    """
    从 data_root/book/events/<scope_id>/events/turn_*.md 加载事件列表，作为记忆的唯一持久化来源。
    返回事件列表，每项含 summary、body、scope_id、time、place，供写入 storage，展示时从 storage 取正文，保证持久化一致、避免多处存正文。
    """
    book_root = data_root / "book"
    sid = _safe_dir_name(scope_id)
    events_dir = book_root / BOOK_EVENTS / sid / "events"
    if not events_dir.is_dir():
        return []
    events: list[dict] = []
    for path in sorted(events_dir.glob("turn_*.md")):
        name = path.stem
        try:
            turn_index = int(name.replace("turn_", ""))
        except ValueError:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        event = _parse_turn_md_content(text, scope_id, turn_index)
        events.append(event)
    return events


def ensure_memory_root_readmes(data_root: Path, scope_ids: list[str], character_ids: list[str]) -> None:
    """确保 book/ 下 README 与 content/setting/characters/events 索引存在。"""
    book_root = data_root / "book"
    book_root.mkdir(parents=True, exist_ok=True)
    (book_root / "README.md").write_text(
        "# book\n\n"
        "- content/ 内容（回合正文）\n"
        "- setting/ 设定\n"
        "- characters/ 人物（角色记忆）\n"
        "- events/ 事件（范围事件与状态）\n"
        "- memory/author_classified/ 作者在环自由输入经 LLM 归类后的持久记忆\n",
        encoding="utf-8",
    )
    for sub in (BOOK_CONTENT, BOOK_SETTING, BOOK_CHARACTERS, BOOK_EVENTS):
        (book_root / sub).mkdir(parents=True, exist_ok=True)
    char_list = "\n".join(f"- {_safe_dir_name(c)}" for c in character_ids) if character_ids else "- （无）"
    (book_root / BOOK_CHARACTERS / "README.md").write_text("# characters 人物\n\n" + char_list + "\n", encoding="utf-8")
    scope_list = "\n".join(f"- {_safe_dir_name(s)}" for s in scope_ids) if scope_ids else "- （无）"
    (book_root / BOOK_EVENTS / "README.md").write_text("# events 事件\n\n" + scope_list + "\n", encoding="utf-8")
    (book_root / BOOK_CONTENT / "README.md").write_text("# content 内容\n\n- turns/ 按回合存储\n", encoding="utf-8")
    (book_root / BOOK_SETTING / "README.md").write_text("# setting 设定\n\n设计会话与各方向设定（MD）。\n", encoding="utf-8")
