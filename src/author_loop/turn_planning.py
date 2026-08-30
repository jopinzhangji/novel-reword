"""
回合写作前分析与正文生成：先呈现本回合写作前分析及预计字数，作者同意后再生成本回合小说正文（≤2000 字）。
与 DESIGN 画卷徐徐展开、写作前分析一致；供 run_novel_with_author 两阶段审阅使用。
"""
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

from src.context import TurnContext
from src.llm.base import LLMQuotaExhaustedError

logger = logging.getLogger(__name__)

# 每回合正文建议上限（字）
DEFAULT_MAX_BODY_CHARS = 2000


@dataclass
class TurnPlan:
    """本回合写作前分析及预计字数，用于先呈报作者同意再生成正文。"""
    analysis: str
    estimated_chars: int


def _get_scope_info(world_config: dict | None, scope_id: str) -> dict:
    """从 world_config 取指定范围的设定。"""
    if not world_config:
        return {}
    for s in world_config.get("scopes") or []:
        if s.get("id") == scope_id:
            return dict(s)
    return {}


def build_turn_plan_prompt(
    ctx: TurnContext,
    scope_info: dict,
    events_snippet: str,
    author_memory_snippet: str = "",
    outline_snippet: str = "",
    pacing_prompt_block: str = "",
    main_characters_snippet: str = "",
) -> str:
    """拼写作前分析 + 预计字数的 prompt，仅要求 LLM 输出分析与本回合预计字数。"""
    name = scope_info.get("name") or ctx.scope_id
    # 设定“概要”原则：写作前分析阶段只允许注入基础设定概览；
    # 是否需要把设定细节进一步展开，由【最近事件/前文】【最近剧情】【次要角色】等结果触发。
    raw_desc = (scope_info.get("description") or "").strip()
    # 只取前段，避免把完整设定细节提前塞进“分析”阶段导致膨胀。
    if len(raw_desc) > 260:
        desc = raw_desc[:260].rsplit("。", 1)[0].strip() or raw_desc[:260].strip()
    else:
        desc = raw_desc
    lines = [
        "你是本回合的叙事策划。请仅输出「本回合写作前分析」与「本回合预计字数」，不写正文。",
        "",
        f"范围：{name}（{ctx.scope_id}），时间：{ctx.time}，地点：{ctx.place}。",
        f"设定概览：{desc}" if desc else "",
    ]
    if (main_characters_snippet or "").strip():
        lines.extend(["", main_characters_snippet.strip()])
    lines.extend([
        "",
        "关键规则：本阶段“设定概览”只用于提供基础背景。",
        "只有当你从【最近事件/前文】或【最近剧情】或【本段涉及的其他角色（次要角色列表）】中判断：当前场景确实需要某类设定细节来解释行动/因果/规则时，才在你的分析中简要点出需要深挖的设定维度。",
        "如果没有触发需求，请只沿用概览，不要提前展开完整设定内容（尤其不要把完整战力/境界/体系逐条抄出来）。",
        "",
        "【最近事件/前文】",
        events_snippet if events_snippet else "（暂无）",
        "",
        "【作者持久记忆（按目录归类，渐进检索注入；如有硬约束须严格遵守）】",
        (author_memory_snippet.strip() or "（暂无）"),
        "",
        f"最近剧情：{ctx.shared_story_snippet or '（无）'}",
        (ctx.secondary_characters_snippet or ""),
        "",
    ])
    if (outline_snippet or "").strip():
        lines.extend([outline_snippet.strip(), ""])
    if (pacing_prompt_block or "").strip():
        lines.extend([pacing_prompt_block.strip(), ""])
    lines.extend([
        "请按以下结构输出（不要写小说正文）：",
        "1）场景分析（时间、地点、环境、氛围）",
        "2）相关角色分析（本段涉及的主要角色及其状态）",
        "3）受害者/冲突方分析（若有）",
        "4）相关其他人员与生物",
        "5）本段目标分析（情节或情绪目标）",
        "6）基调与风格",
        "7）分场景构思（本段内各小场景写什么）",
        "8）本回合预计字数：一个数字（建议不超过2000）。",
        "",
        "严格在最后一行写：本回合预计字数：<数字>",
    ])
    return "\n".join(l for l in lines if l is not None)


def _parse_turn_plan_response(raw: str) -> TurnPlan:
    """从 LLM 回复中解析写作前分析文本与预计字数。"""
    raw = (raw or "").strip()
    estimated = DEFAULT_MAX_BODY_CHARS
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if "本回合预计字数" in line or "预计字数" in line:
            import re
            m = re.search(r"[:：]\s*(\d+)", line)
            if m:
                try:
                    estimated = min(DEFAULT_MAX_BODY_CHARS, max(100, int(m.group(1))))
                except ValueError:
                    pass
            break
    # 若最后一行是「本回合预计字数：1234」，分析文本去掉该行
    analysis_lines = []
    for line in raw.splitlines():
        s = line.strip()
        if s and "本回合预计字数" not in s and "预计字数" not in s:
            analysis_lines.append(s)
        elif "本回合预计字数" in s or "预计字数" in s:
            break
    analysis = "\n".join(analysis_lines).strip() or "（无分析）"
    return TurnPlan(analysis=analysis, estimated_chars=estimated)


def generate_turn_plan_for_turn(
    storage: Any,
    world_config: dict,
    runtime_config: dict,
    scope_id: str,
    time: str,
    place: str,
    present_character_ids: list[str],
    last_turn_summary: str = "",
    recent_events_k: int = 5,
    project_root: Path | None = None,
    outline_snippet: str = "",
    chapter_goal: str = "",
    requested_pace_mode: str | None = None,
    main_characters_snippet: str = "",
) -> TurnPlan:
    """
    根据当前回合上下文生成本回合写作前分析及预计字数（供主流程先呈现、作者同意后再生成正文）。
    """
    from src.context import build_turn_context_from_storage
    from src.retrieval import format_scope_events_snippet
    ctx = build_turn_context_from_storage(
        scope_id=scope_id,
        time=time,
        place=place,
        present_character_ids=present_character_ids,
        storage=storage,
        world_config=world_config,
        last_turn_summary=last_turn_summary,
        recent_events_k=recent_events_k,
    )
    scope_info = _get_scope_info(world_config, scope_id)
    events_snippet = format_scope_events_snippet(storage, scope_id, k=recent_events_k)
    author_memory_snippet = ""
    if project_root is not None:
        try:
            from src.author_loop.author_classified_memory import (
                progressive_author_memory_for_plan,
            )

            author_memory_snippet = progressive_author_memory_for_plan(
                project_root,
                runtime_config,
                scope_id,
                last_turn_summary,
            )
        except Exception as e:
            logger.debug("加载作者归类记忆失败（忽略）: %s", e)
    return generate_turn_plan(
        ctx,
        scope_info,
        events_snippet,
        runtime_config,
        author_memory_snippet=author_memory_snippet,
        outline_snippet=outline_snippet,
        chapter_goal=chapter_goal,
        requested_pace_mode=requested_pace_mode,
        main_characters_snippet=main_characters_snippet,
    )


def generate_turn_plan(
    ctx: TurnContext,
    scope_info: dict,
    events_snippet: str,
    runtime_config: dict,
    author_memory_snippet: str = "",
    outline_snippet: str = "",
    chapter_goal: str = "",
    requested_pace_mode: str | None = None,
    main_characters_snippet: str = "",
) -> TurnPlan:
    """
    生成本回合写作前分析及预计字数。若 LLM 不可用则返回占位。
    """
    from src.author_harness.policy_assembler import assemble_pacing_prompt_block, resolve_pacing_contract

    pacing_contract = resolve_pacing_contract(
        runtime_config,
        chapter_goal=chapter_goal,
        requested_mode=requested_pace_mode,
    )
    pacing_prompt_block = assemble_pacing_prompt_block(pacing_contract)
    prompt = build_turn_plan_prompt(
        ctx,
        scope_info,
        events_snippet,
        author_memory_snippet=author_memory_snippet,
        outline_snippet=outline_snippet,
        pacing_prompt_block=pacing_prompt_block,
        main_characters_snippet=main_characters_snippet,
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return TurnPlan(
                analysis="（未配置 LLM，使用占位分析）\n本段推进氛围与角色反应，预计 800～1200 字。",
                estimated_chars=1200,
            )
        raw = provider.generate(prompt)
        return _parse_turn_plan_response(raw)
    except LLMQuotaExhaustedError as e:
        logger.error("生成写作前分析失败（模型额度已用尽）：%s", e)
        return TurnPlan(
            analysis="（模型额度已用尽，使用占位）\n本段按前文推进，建议 800～1500 字。",
            estimated_chars=1200,
        )
    except Exception as e:
        logger.warning("生成写作前分析失败: %s", e)
        return TurnPlan(
            analysis="（生成失败，使用占位）\n本段按前文推进，建议 800～1500 字。",
            estimated_chars=1200,
        )


def revise_turn_plan_with_author_requirements(
    plan: TurnPlan,
    author_requirements: str,
    runtime_config: dict,
) -> TurnPlan:
    """
    根据作者补充要求，由大模型对当前写作前分析进行修订并重新生成一次。
    作者输入非空时调用；若 LLM 不可用或失败则保留原分析并在文末追加作者要求说明。
    """
    if not (author_requirements and author_requirements.strip()):
        return plan
    prompt = (
        "你是本回合的叙事策划。当前已有「本回合写作前分析」如下。\n\n"
        "【当前写作前分析】\n"
        f"{plan.analysis}\n\n"
        "【作者补充要求】\n"
        f"{author_requirements.strip()}\n\n"
        "请根据作者补充要求，对写作前分析进行修订或补充（如更新相关角色分析、本段目标、分场景构思等），"
        "使修订后的分析充分体现作者要求。不要写小说正文，只输出修订后的完整写作前分析。\n"
        "严格在最后一行写：本回合预计字数：<数字>"
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            revised_analysis = (plan.analysis or "").strip() + "\n\n【作者补充要求】\n" + author_requirements.strip()
            return TurnPlan(analysis=revised_analysis, estimated_chars=plan.estimated_chars)
        raw = provider.generate(prompt)
        revised = _parse_turn_plan_response(raw)
        logger.debug("已根据作者要求修订写作前分析")
        return revised
    except LLMQuotaExhaustedError as e:
        logger.error("根据作者要求修订写作前分析失败（模型额度已用尽）：%s", e)
        revised_analysis = (plan.analysis or "").strip() + "\n\n【作者补充要求】\n" + author_requirements.strip()
        return TurnPlan(analysis=revised_analysis, estimated_chars=plan.estimated_chars)
    except Exception as e:
        logger.warning("根据作者要求修订写作前分析失败: %s", e)
        revised_analysis = (plan.analysis or "").strip() + "\n\n【作者补充要求】\n" + author_requirements.strip()
        return TurnPlan(analysis=revised_analysis, estimated_chars=plan.estimated_chars)


def build_turn_body_prompt(
    plan: TurnPlan,
    result: Any,
    ctx: TurnContext,
    max_chars: int = DEFAULT_MAX_BODY_CHARS,
    author_requirements: str = "",
    outline_snippet: str = "",
    pacing_prompt_block: str = "",
    main_characters_snippet: str = "",
    bridging_snippet: str = "",
) -> str:
    """拼本回合小说正文的 prompt：基于写作前分析、Scope 约束与事件摘要、角色言行及作者补充要求，输出一段连贯正文。"""
    scope = result.scope_output
    event_summary = scope.event_summary or "（无）"
    constraints = scope.constraints or []
    parts = [
        "请根据以下「写作前分析」与「本回合事件与角色言行」，写出一段连贯的小说正文。",
        "要求：一段成文，不要列条、不要重复分析；正文不超过 {} 字。".format(max_chars),
        "本回合仅服务当前节拍意图，勿提前写尽下一节拍或下一章核心转折（除非写作前分析已说明跨度）。",
        "",
        "【写作前分析】",
        plan.analysis,
        "",
    ]
    if (bridging_snippet or "").strip():
        parts.extend([bridging_snippet.strip(), ""])
    if (main_characters_snippet or "").strip():
        parts.extend([main_characters_snippet.strip(), ""])
    if (outline_snippet or "").strip():
        parts.extend([outline_snippet.strip(), ""])
    if (pacing_prompt_block or "").strip():
        parts.extend([pacing_prompt_block.strip(), ""])
    if author_requirements and author_requirements.strip():
        parts.extend([
            "【作者补充要求】（必须满足）",
            author_requirements.strip(),
            "",
        ])
    parts.extend([
        "【本回合事件摘要】",
        event_summary,
        "",
        "【约束】",
        "\n".join("- " + c for c in constraints) if constraints else "（无）",
        "",
        "【角色言行】",
    ])
    for cid in sorted(result.character_outputs.keys()):
        out = result.character_outputs[cid]
        inner = (out.inner_monologue or "").strip()
        action = (out.dialogue_action or "").strip()
        if inner or action:
            parts.append(f"- {cid}：{inner}; {action}".replace("; ", " ") if not action else f"- {cid}：{action}")
    parts.extend([
        "",
        "请直接输出小说正文，不要加「正文：」等前缀，不要超出 {} 字。".format(max_chars),
    ])
    return "\n".join(parts)


def generate_turn_body(
    plan: TurnPlan,
    result: Any,
    ctx: TurnContext,
    runtime_config: dict,
    max_chars: int = DEFAULT_MAX_BODY_CHARS,
    author_requirements: str = "",
    outline_snippet: str = "",
    chapter_goal: str = "",
    requested_pace_mode: str | None = None,
    main_characters_snippet: str = "",
    bridging_snippet: str = "",
) -> str:
    """
    基于写作前分析与本回合 TurnResult，生成本回合小说正文，不超过 max_chars 字。
    author_requirements：作者在呈现分析时补充的本回合正文要求（视角、语气、禁止内容等），会注入 prompt。
    若 LLM 不可用则用 resolve_turn_conflict 的摘要作为正文并截断。
    """
    try:
        from src.llm import get_llm_provider
        from src.orchestrator import resolve_turn_conflict
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            resolved = resolve_turn_conflict(result.scope_output, result.character_outputs)
            return (resolved or "（本回合无正文）")[:max_chars]
        from src.author_harness.policy_assembler import (
            assemble_pacing_prompt_block,
            resolve_pacing_contract,
        )
        from src.author_harness.critic import evaluate_body_against_pacing

        pacing_contract = resolve_pacing_contract(
            runtime_config,
            chapter_goal=chapter_goal,
            requested_mode=requested_pace_mode,
        )
        pacing_prompt_block = assemble_pacing_prompt_block(pacing_contract)
        prompt = build_turn_body_prompt(
            plan,
            result,
            ctx,
            max_chars,
            author_requirements=author_requirements or "",
            outline_snippet=outline_snippet or "",
            pacing_prompt_block=pacing_prompt_block,
            main_characters_snippet=main_characters_snippet,
            bridging_snippet=bridging_snippet or "",
        )
        raw = provider.generate(prompt)
        body = (raw or "").strip()
        # 去掉可能的前缀
        for prefix in ("正文：", "正文:", "【正文】", "小说正文："):
            if body.startswith(prefix):
                body = body[len(prefix):].strip()
        if len(body) > max_chars:
            body = body[:max_chars]
        critic = evaluate_body_against_pacing(pacing_contract, body)
        logger.info(
            "[作者在环] critic pace_deviation=%.2f subplot_reveal_deviation=%.2f reason=%s goal_window=%s pace_mode=%s",
            critic.pace_deviation,
            critic.subplot_reveal_deviation,
            critic.reason,
            pacing_contract.goal_window,
            pacing_contract.pace_mode,
        )
        return body or "（本回合无正文）"
    except LLMQuotaExhaustedError as e:
        logger.error("生成本回合正文失败（模型额度已用尽）：%s", e)
        from src.orchestrator import resolve_turn_conflict
        resolved = resolve_turn_conflict(result.scope_output, result.character_outputs)
        return (resolved or "（本回合无正文）")[:max_chars]
    except Exception as e:
        logger.warning("生成本回合正文失败: %s", e)
        from src.orchestrator import resolve_turn_conflict
        resolved = resolve_turn_conflict(result.scope_output, result.character_outputs)
        return (resolved or "（本回合无正文）")[:max_chars]


# 正文展示后作者自由交流：意图理解、按反馈修订正文、生成本回合摘要

CONFIRM_KEYWORDS = ("y", "yes", "是", "没问题", "满意", "通过", "可以", "好", "确认", "行", "ok")

# 审阅时给作者的提示：直接回复这些词表示满意，会触发本回合摘要写入主线记忆并进入下一回合
CONFIRM_HINT = "直接回复「y」或「没问题」表示满意，将写入本回合摘要到主线记忆并进入下一回合。"


def understand_author_review_intent(author_input: str, runtime_config: dict | None = None) -> str:
    """
    判断作者审阅时的意图：confirm=通过/没问题，reject=驳回，edit=先修改文件，supplement=补充设定，revise=针对本回合的修改意见。

    R7b：委托 classify_intent（phase=MAIN_WRITING_REVIEW），与入口分类单源对拍；rules/Dummy 与历史行为一致。
    """
    from src.author_loop.author_interaction_state import AuthorPhaseState, LastRoundDigest
    from src.author_loop.classify_intent import classify_intent, main_review_intent_to_cli_action

    cl = classify_intent(
        author_input or "",
        AuthorPhaseState(phase="MAIN_WRITING_REVIEW"),
        LastRoundDigest(),
        runtime_config if runtime_config is not None else {},
    )
    logger.debug(
        "MAIN_WRITING_REVIEW intent_id=%s retrieval_query_chars=%s",
        cl.intent_id,
        len(cl.retrieval_query or ""),
    )
    return main_review_intent_to_cli_action(cl.intent_id)


def revise_body_by_feedback(
    body: str,
    author_feedback: str,
    constraints: list[str],
    runtime_config: dict,
    max_chars: int = DEFAULT_MAX_BODY_CHARS,
    *,
    assembled_context: str = "",
) -> str:
    """
    根据作者对本回合正文的反馈，由大模型修订正文并返回。
    无 LLM 或失败时返回原 body。

    **R7d**：``assembled_context`` 为 PromptAssembler 组装的检索块（最近事件摘要、digest 等），
    与作者反馈一并注入；不得替代「作者反馈」为唯一指令来源。
    """
    if not (author_feedback and author_feedback.strip()):
        return body
    ctx_block = ""
    if (assembled_context or "").strip():
        ctx_block = (
            "\n【与修订相关的已落盘检索（供参照，修改以作者反馈为准）】\n"
            f"{assembled_context.strip()}\n"
        )
    prompt = (
        "以下是本回合的小说正文。作者审阅后给出如下反馈，请根据反馈修订正文，除非作者明确要求修改风格，否则保持风格一致，不要偏离前文。\n\n"
        "【当前正文】\n"
        f"{body}\n\n"
        "【作者反馈】\n"
        f"{author_feedback.strip()}\n"
        f"{ctx_block}\n"
        "【约束（须遵守）】\n"
        + "\n".join(f"- {c}" for c in (constraints or ["无"]))
        + "\n\n请直接输出修订后的完整正文，不要加「正文：」等前缀，不要超出 "
        + str(max_chars)
        + " 字。"
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return body
        raw = provider.generate(prompt)
        revised = (raw or "").strip()
        for prefix in ("正文：", "正文:", "【正文】", "修订后正文："):
            if revised.startswith(prefix):
                revised = revised[len(prefix) :].strip()
        if len(revised) > max_chars:
            revised = revised[:max_chars]
        return revised if revised else body
    except LLMQuotaExhaustedError as e:
        logger.error("根据作者反馈修订正文失败（模型额度已用尽）：%s", e)
        return body
    except Exception as e:
        logger.warning("根据作者反馈修订正文失败: %s", e)
        return body


def generate_turn_summary_from_body(body: str, runtime_config: dict) -> str:
    """
    从本回合正文生成简短摘要（一到三句话），便于写入主线记忆并后续检索；
    摘要与正文对应，方便查到摘要时能定位到完整正文。
    无 LLM 或失败时用正文前 200 字作为摘要。
    """
    if not (body and body.strip()):
        return "（本回合无正文）"
    prompt = (
        "请将以下本回合小说正文压缩为一到三句话的摘要，便于后续检索时对应到本段正文。只输出摘要，不要其他。\n\n"
        f"正文：\n{body[:3000]}\n\n"
        "摘要："
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return (body.strip()[:200] + ("…" if len(body) > 200 else "")) or "（本回合无正文）"
        raw = provider.generate(prompt)
        summary = (raw or "").strip()
        if len(summary) > 500:
            summary = summary[:500] + "…"
        return summary if summary else body.strip()[:200] + "…"
    except LLMQuotaExhaustedError as e:
        logger.error("从正文生成本回合摘要失败（模型额度已用尽）：%s", e)
        return body.strip()[:200] + ("…" if len(body) > 200 else "") or "（本回合无正文）"
    except Exception as e:
        logger.warning("从正文生成本回合摘要失败: %s", e)
        return body.strip()[:200] + ("…" if len(body) > 200 else "") or "（本回合无正文）"
