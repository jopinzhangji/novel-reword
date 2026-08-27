"""
作者在环 Agent Harness 实现包（迁移 R1+）。

设计说明：docs/design/author-agent-harness.md §6.1（R0–R8）。
"""

from src.author_harness.author_harness import (
    AuthorHarness,
    DesignMainMenuHarnessResult,
    MainWritingReviewIngressResult,
    apply_design_main_menu_ingress,
    apply_main_writing_review_ingress,
)
from src.author_harness.prompt_assembler import assemble_retrieval_prompt_block
from src.author_harness.policy_store import PolicyStoreConfig, load_policy_store_from_runtime
from src.author_harness.policy_assembler import (
    PacingContract,
    assemble_pacing_prompt_block,
    assemble_policy_prompt_block,
    resolve_pacing_contract,
)
from src.author_harness.critic import CriticScore, evaluate_body_against_pacing
from src.author_harness.policy_updater import PolicyCandidatePatch, build_candidate_patch
from src.author_harness.policy_gate import GateResult, validate_candidate_patch
from src.author_harness.retrieval_registry import INTENT_RETRIEVAL_TOOL_CHAINS

__all__ = [
    "AuthorHarness",
    "DesignMainMenuHarnessResult",
    "MainWritingReviewIngressResult",
    "apply_design_main_menu_ingress",
    "apply_main_writing_review_ingress",
    "assemble_retrieval_prompt_block",
    "PolicyStoreConfig",
    "load_policy_store_from_runtime",
    "PacingContract",
    "resolve_pacing_contract",
    "assemble_pacing_prompt_block",
    "assemble_policy_prompt_block",
    "CriticScore",
    "evaluate_body_against_pacing",
    "PolicyCandidatePatch",
    "build_candidate_patch",
    "GateResult",
    "validate_candidate_patch",
    "INTENT_RETRIEVAL_TOOL_CHAINS",
]
