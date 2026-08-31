"""
I2：PolicyAssembler（最小实现）

将 I1 PolicyStore 解析为可注入 prompt 的策略块，先接入节奏约束（Pacing Contract）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.author_harness.policy_store import PolicyStoreConfig, load_policy_store_from_runtime


@dataclass(frozen=True)
class PacingContract:
    pace_mode: str
    goal_window: str
    plot_exposure_budget: str
    subplot_reveal_budget: str
    character_action_caps: dict[str, int]
    forbidden_moves: list[str]


def resolve_pacing_contract(
    runtime_config: dict[str, Any],
    *,
    chapter_goal: str = "",
    requested_mode: str | None = None,
    growth_standings: Any = None,
) -> PacingContract:
    cfg = load_policy_store_from_runtime(runtime_config)
    pace_mode = cfg.resolve_pace_mode(requested_mode)
    goal_window = _infer_goal_window(chapter_goal, pace_mode)
    if goal_window == "铺垫":
        contract = PacingContract(
            pace_mode=pace_mode,
            goal_window=goal_window,
            plot_exposure_budget="low",
            subplot_reveal_budget="signal",
            character_action_caps={"protagonist_high_impact_max": 1, "supporting_high_impact_max": 0},
            forbidden_moves=["避免同回合揭示核心暗线真相", "避免并发推进多个主冲突"],
        )
    elif goal_window == "兑现":
        contract = PacingContract(
            pace_mode=pace_mode,
            goal_window=goal_window,
            plot_exposure_budget="high",
            subplot_reveal_budget="reveal",
            character_action_caps={"protagonist_high_impact_max": 2, "supporting_high_impact_max": 1},
            forbidden_moves=["避免无铺垫强行反转", "避免一次性回收全部暗线"],
        )
    else:
        contract = PacingContract(
            pace_mode=pace_mode,
            goal_window="推进",
            plot_exposure_budget="medium",
            subplot_reveal_budget="partial",
            character_action_caps={"protagonist_high_impact_max": 1, "supporting_high_impact_max": 1},
            forbidden_moves=["避免跳过关键因果桥接"],
        )
    # G2 前馈：若提供成长站姿，按「兑现边缘」对契约做偏置（默认 None → 行为与旧版完全一致）。
    if growth_standings is not None:
        contract = override_contract_for_growth(contract, growth_standings)
    return contract


def infer_growth_window(standings: Any) -> str | None:
    """
    G2：从成长站姿推出节拍倾向。仅当存在**兑现边缘**角色时偏置为 `"兑现"`；否则返回 None（不偏置）。
    """
    if standings is None:
        return None
    edges = getattr(standings, "payoff_edge", None)
    if edges:
        return "兑现"
    return None


def override_contract_for_growth(contract: PacingContract, standings: Any) -> PacingContract:
    """
    G2：站在既有契约之上，按成长站姿偏置。仅当成长站姿推出 `"兑现"` **且** 契约尚未处于兑现窗时才改写：
    更新窗口为兑现口径，并追加一条「勿悬置兑现边缘角色回响」禁止项；其余字段保留。其余情况原样返回。
    """
    window = infer_growth_window(standings)
    if window is None or contract.goal_window == window:
        return contract
    forbidden = list(contract.forbidden_moves) + ["勿悬置已到兑现边缘角色的回响（正文需承接其成长回响）"]
    return PacingContract(
        pace_mode=contract.pace_mode,
        goal_window=window,
        plot_exposure_budget="high",
        subplot_reveal_budget="reveal",
        character_action_caps={"protagonist_high_impact_max": 2, "supporting_high_impact_max": 1},
        forbidden_moves=forbidden,
    )


def assemble_policy_prompt_block(
    policy_store: PolicyStoreConfig,
    *,
    novel_profile: str | None = None,
    phase: str | None = None,
    intent_id: str | None = None,
    pacing: PacingContract | None = None,
) -> str:
    rules = policy_store.resolve_rules(
        novel_profile=novel_profile,
        phase=phase,
        intent_id=intent_id,
    )
    lines: list[str] = []
    if rules:
        lines.append("【动态策略规则】")
        lines.extend(f"- {r}" for r in rules)
        lines.append("")
    if pacing is not None:
        lines.append(assemble_pacing_prompt_block(pacing))
    return "\n".join(lines).strip()


def assemble_pacing_prompt_block(contract: PacingContract) -> str:
    return "\n".join(
        [
            "【节奏约束（Pacing Contract）】",
            f"- pace_mode: {contract.pace_mode}",
            f"- goal_window: {contract.goal_window}",
            f"- 主线推进预算: {contract.plot_exposure_budget}",
            f"- 暗线显露上限: {contract.subplot_reveal_budget}",
            (
                "- 角色高影响动作上限: "
                f"主角={contract.character_action_caps.get('protagonist_high_impact_max', 1)}，"
                f"配角={contract.character_action_caps.get('supporting_high_impact_max', 1)}"
            ),
            *[f"- 禁止项: {x}" for x in contract.forbidden_moves],
            "",
        ]
    )


def _infer_goal_window(chapter_goal: str, pace_mode: str) -> str:
    goal = (chapter_goal or "").strip()
    if any(k in goal for k in ("铺垫", "埋伏笔", "引入", "渲染")):
        return "铺垫"
    if any(k in goal for k in ("兑现", "回收", "揭示", "收束", "落地")):
        return "兑现"
    if pace_mode == "slow_burn":
        return "铺垫"
    if pace_mode == "push":
        return "兑现"
    return "推进"

