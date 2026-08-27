"""
作者在环统一会话上下文（见 docs/design/author-interaction.md §13 M1–M2）。

M1：统一 read_line。M2：phase_state + last_round_digest 持久化（author_interaction_state.yaml）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from src.author_loop.author_interaction_state import (
    AuthorPhaseState,
    LastRoundDigest,
    load_interaction_state,
    save_interaction_state,
    _now_iso,
)
from src.author_loop.digest_compress_llm import compress_round_digest_fields


@dataclass
class AuthorSession:
    """单作者 CLI 会话：配置路径、读入函数、阶段与上一轮摘要。"""

    config_dir: Path
    project_root: Path
    runtime_config: dict[str, Any]
    input_fn: Callable[[str], str] | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    phase_state: AuthorPhaseState = field(default_factory=AuthorPhaseState)
    last_round_digest: LastRoundDigest = field(default_factory=LastRoundDigest)

    @classmethod
    def for_design_phase(
        cls,
        config_dir: Path,
        project_root: Path,
        runtime_config: dict[str, Any],
        input_fn: Callable[[str], str] | None = None,
    ) -> AuthorSession:
        """加载 author_interaction_state.yaml（若存在），用于设定阶段与开篇补充设定。"""
        ps, dg = load_interaction_state(config_dir)
        return cls(
            config_dir=Path(config_dir),
            project_root=Path(project_root),
            runtime_config=runtime_config,
            input_fn=input_fn,
            phase_state=ps,
            last_round_digest=dg,
        )

    @classmethod
    def for_main_loop(
        cls,
        config_dir: Path,
        project_root: Path,
        runtime_config: dict[str, Any],
        input_fn: Callable[[str], str] | None = None,
    ) -> AuthorSession:
        """正文主流程作者在环（M5）：与设定阶段共用同一 `author_interaction_state` 路径与读入函数。"""
        return cls.for_design_phase(config_dir, project_root, runtime_config, input_fn=input_fn)

    def read_line(self, prompt: str) -> str:
        """显示 prompt 并读一行，strip 首尾空白。"""
        fn = self.input_fn or input
        return fn(prompt).strip()

    def persist_interaction_state(self) -> None:
        """将当前 phase_state 与 last_round_digest 写回磁盘。"""
        save_interaction_state(self.config_dir, self.phase_state, self.last_round_digest)

    def record_round_digest(
        self,
        *,
        interaction: str,
        system_response: str,
        execution: str,
        phase: str | None = None,
        subphase: str | None = None,
        open_issues: list[str] | None = None,
    ) -> None:
        """
        记录上一轮摘要（M2）：默认经 LLM 压缩要点后落盘（见 digest_compress_llm）；
        关闭压缩或 LLM 不可用时保留完整原文，不截断。
        phase / subphase 非 None 时更新 phase_state。
        """
        ci, cs, ce, coi = compress_round_digest_fields(
            self.runtime_config,
            interaction=interaction,
            system_response=system_response,
            execution=execution,
            open_issues=open_issues,
        )
        self.last_round_digest = LastRoundDigest(
            interaction=ci,
            system_response=cs,
            execution=ce,
            open_issues=coi,
            updated_at=_now_iso(),
        )
        if phase is not None:
            self.phase_state.phase = phase
        if subphase is not None:
            self.phase_state.subphase = subphase
        self.phase_state.updated_at = _now_iso()
        self.persist_interaction_state()
