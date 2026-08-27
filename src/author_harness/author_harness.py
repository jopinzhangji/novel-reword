"""
R6：作者在环 Harness 薄层（设定主菜单 ingress）。

将「分类 → 检索 → Assembler → session.extra」收拢到此，run_design_phase 只做 UI 与分支。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.author_harness.prompt_assembler import assemble_retrieval_prompt_block
from src.author_loop.author_session import AuthorSession
from src.author_loop.author_interaction_state import AuthorPhaseState, LastRoundDigest
from src.author_loop.classify_intent import (
    INTENT_REVIEW_REVISE,
    IntentClassification,
    classify_intent,
    design_main_menu_key,
    main_review_intent_to_cli_action,
)
from src.author_loop.retrieve_for_intent import RetrievalSnippet, retrieve_for_intent


@dataclass(frozen=True)
class DesignMainMenuHarnessResult:
    """主菜单单行经 Harness 后的结构化结果（供 run_design_phase 分支）。"""

    raw_normalized: str
    classification: IntentClassification
    menu_key: str
    retrieval_snippets: list[RetrievalSnippet]
    retrieval_block: str


def apply_design_main_menu_ingress(
    user_line: str,
    *,
    session: AuthorSession,
    config_dir: Path,
    runtime_config: dict[str, Any],
) -> DesignMainMenuHarnessResult:
    """
    设定阶段主菜单：在 ``phase_state`` 为 DESIGN_MAIN 的前提下，对**已规范化**的一行输入
    做 classify → retrieve → assemble，并写入 ``session.extra``。
    """
    text = (user_line or "").strip()
    _cl = classify_intent(
        text,
        session.phase_state,
        session.last_round_digest,
        runtime_config,
        config_dir=config_dir,
    )
    menu_key = design_main_menu_key(_cl, text)
    _snippets = retrieve_for_intent(
        _cl.intent_id,
        _cl.retrieval_query or text,
        config_dir=config_dir,
        project_root=session.project_root,
        runtime_config=runtime_config,
        internet_search_needed=_cl.internet_search_needed,
        internet_query=_cl.internet_query or None,
    )
    block = assemble_retrieval_prompt_block(_snippets)
    session.extra["intent_retrieval"] = block
    session.extra["intent_retrieval_snippets"] = _snippets
    return DesignMainMenuHarnessResult(
        raw_normalized=text,
        classification=_cl,
        menu_key=menu_key,
        retrieval_snippets=_snippets,
        retrieval_block=block,
    )


@dataclass(frozen=True)
class MainWritingReviewIngressResult:
    """正篇阶段一审阅单行：分类 →（revise 时）检索 → 组装块（R7d）。"""

    raw_input: str
    classification: IntentClassification
    intent_cli: str
    retrieval_snippets: list[RetrievalSnippet]
    retrieval_block: str


def apply_main_writing_review_ingress(
    user_line: str,
    *,
    config_dir: Path,
    project_root: Path,
    runtime_config: dict[str, Any],
    storage: Any,
    scope_id: str,
    last_round_digest: LastRoundDigest | None = None,
) -> MainWritingReviewIngressResult:
    """
    MAIN_WRITING 阶段一：对作者输入做 ``MAIN_WRITING_REVIEW`` 分类；若为 ``review_revise`` 则拉取
    ``retrieve_for_intent`` 审阅链并组装为 ``retrieval_block``，供 ``revise_body_by_feedback`` 注入。
    """
    text = (user_line or "").strip()
    dg = last_round_digest if last_round_digest is not None else LastRoundDigest()
    cl = classify_intent(
        text or "y",
        AuthorPhaseState(phase="MAIN_WRITING_REVIEW"),
        dg,
        runtime_config,
    )
    intent_cli = main_review_intent_to_cli_action(cl.intent_id)
    snippets: list[RetrievalSnippet] = []
    if cl.intent_id == INTENT_REVIEW_REVISE:
        snippets = retrieve_for_intent(
            INTENT_REVIEW_REVISE,
            cl.retrieval_query or text or "y",
            config_dir=config_dir,
            project_root=project_root,
            runtime_config=runtime_config,
            storage=storage,
            scope_id=scope_id,
        )
    block = assemble_retrieval_prompt_block(snippets)
    return MainWritingReviewIngressResult(
        raw_input=text,
        classification=cl,
        intent_cli=intent_cli,
        retrieval_snippets=snippets,
        retrieval_block=block,
    )


class AuthorHarness:
    """
    可挂载会话与路径的 Harness（R6）；当前提供主菜单 ingress，后续可扩展 MAIN_WRITING 等。
    """

    def __init__(
        self,
        *,
        session: AuthorSession,
        config_dir: Path,
        runtime_config: dict[str, Any],
    ) -> None:
        self._session = session
        self._config_dir = Path(config_dir)
        self._runtime_config = runtime_config

    def apply_design_main_menu_ingress(self, user_line: str) -> DesignMainMenuHarnessResult:
        return apply_design_main_menu_ingress(
            user_line,
            session=self._session,
            config_dir=self._config_dir,
            runtime_config=self._runtime_config,
        )
