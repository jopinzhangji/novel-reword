"""
作者在环阶段状态与上一轮摘要持久化（docs/design/author-interaction.md §6–7、§13 M2）。

单文件 author_interaction_state.yaml：绑定小说时落在 <novel_root>/config/，否则在全局 config/。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.config import current_novel_root

STATE_BASENAME = "author_interaction_state.yaml"


def author_interaction_state_path(config_dir: Path) -> Path:
    """状态文件路径：有 current_novel 时用小说 config/，否则全局 config/。"""
    config_dir = Path(config_dir)
    novel_root = current_novel_root(config_dir)
    if novel_root:
        return novel_root / "config" / STATE_BASENAME
    return config_dir / STATE_BASENAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class AuthorPhaseState:
    """作者流程阶段快照（供后续入口分类 LLM）。"""

    phase: str = "DESIGN_MAIN"
    subphase: str | None = None
    flags: dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""


@dataclass
class LastRoundDigest:
    """上一轮交互 + 程序结果的短摘要（非全量日志）。"""

    interaction: str = ""
    system_response: str = ""
    execution: str = ""
    open_issues: list[str] = field(default_factory=list)
    updated_at: str = ""


def _dataclass_from_dict(cls: type, data: dict[str, Any]) -> Any:
    if not isinstance(data, dict):
        data = {}
    kwargs: dict[str, Any] = {}
    for f in fields(cls):
        if f.name not in data:
            continue
        val = data[f.name]
        if f.name == "flags" and not isinstance(val, dict):
            kwargs[f.name] = {}
        elif f.name == "open_issues" and not isinstance(val, list):
            kwargs[f.name] = []
        else:
            kwargs[f.name] = val
    return cls(**kwargs)


def load_interaction_state(config_dir: Path) -> tuple[AuthorPhaseState, LastRoundDigest]:
    path = author_interaction_state_path(config_dir)
    if not path.is_file():
        return AuthorPhaseState(), LastRoundDigest()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return AuthorPhaseState(), LastRoundDigest()
    if not isinstance(raw, dict):
        return AuthorPhaseState(), LastRoundDigest()
    ps = _dataclass_from_dict(AuthorPhaseState, raw.get("phase_state") or {})
    dg = _dataclass_from_dict(LastRoundDigest, raw.get("last_round_digest") or {})
    return ps, dg


def save_interaction_state(
    config_dir: Path,
    phase_state: AuthorPhaseState,
    last_round_digest: LastRoundDigest,
) -> None:
    path = author_interaction_state_path(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "phase_state": asdict(phase_state),
        "last_round_digest": asdict(last_round_digest),
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(payload, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
