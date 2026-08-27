#!/usr/bin/env python3
"""
一次性迁移：将 config/design_session.yaml 中仍含完整 events/state_snapshot 的内容
迁移到新方案：完整内容写入 data/book/setting/sessions/session_<timestamp>.md 与 .yaml，config 仅保留路径与摘要。
支持 version 1 或 version 2 但 config 里仍带 events 的情况。
用法：在项目根执行 python scripts/migrate_design_session.py
依赖：PyYAML（pip install pyyaml）
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _session_to_markdown(events: list[dict[str, Any]], state_snapshot: dict[str, Any]) -> str:
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


def main() -> None:
    try:
        import yaml
    except ImportError:
        print("请先安装 PyYAML: pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    project_root = Path(__file__).resolve().parent.parent
    config_dir = project_root / "config"
    path = config_dir / "design_session.yaml"
    if not path.is_file():
        print("未找到 config/design_session.yaml，无需迁移。")
        return
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "events" not in data:
        print("config 中无 events，已是新方案，无需迁移。")
        return
    events = data.get("events") or []
    state_snapshot = data.get("state_snapshot") or {}
    theme = data.get("theme", "")
    genre = data.get("genre", "")
    last_updated = data.get("last_updated", "")
    session_start = data.get("session_start", last_updated)
    try:
        dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        ts = dt.strftime("%Y%m%d_%H%M%S")
    except Exception:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    book_root = project_root / "data" / "book"
    session_dir = book_root / "setting" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_md_name = f"session_{ts}.md"
    session_md_path = session_dir / session_md_name
    md_content = _session_to_markdown(events, state_snapshot)
    session_md_path.write_text(md_content, encoding="utf-8")
    session_data_path = session_dir / f"session_{ts}.yaml"
    try:
        with open(session_data_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"events": events, "state_snapshot": state_snapshot},
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        print(f"可恢复数据已写入: {session_data_path}")
    except Exception as e:
        print(f"警告：写入可恢复数据失败 {e}", file=sys.stderr)
    session_file_rel = f"book/setting/sessions/{session_md_name}"
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
    print(f"已迁移：完整内容 -> {session_md_path}")
    print("config/design_session.yaml 已改为仅保留路径与摘要（version 2）。")


if __name__ == "__main__":
    main()
