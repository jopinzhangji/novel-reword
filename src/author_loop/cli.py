"""
作者在环 CLI：阶段一审阅回合结果、阶段二审阅记忆写回计划。
两阶段均提示「可先修改再确认」；支持输入 e 将内容写入临时文件，编辑后读回并应用。
与 TECH_IMPLEMENTATION §6.2 一致。
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Callable

from src.orchestrator import TurnResult, resolve_turn_conflict
from src.agents.world import ScopeTurnOutput
from src.agents.character import CharacterTurnOutput
from src.author_loop.turn_planning import (
    understand_author_review_intent,
    revise_body_by_feedback,
    DEFAULT_MAX_BODY_CHARS,
    CONFIRM_HINT,
)

logger = logging.getLogger(__name__)

# R7e/R8：作者在环可观测 phase 键（与 docs/design/author-agent-harness.md §6.3 一致）
PHASE_MAIN_WRITING_REVIEW = "MAIN_WRITING_REVIEW"
PHASE_MEMORY_PLAN_REVIEW = "MEMORY_PLAN_REVIEW"


def _prompt(text: str, input_fn: Callable[[str], str] | None = None) -> str:
    """显示提示并读一行；input_fn 用于测试注入。"""
    fn = input_fn or input
    return fn(text).strip()


def _write_turn_result_edit_file(path: Path, result: TurnResult) -> None:
    """将 TurnResult 写成可编辑的文本格式。若含 body_narrative 则优先写正文段。"""
    lines = [
        "# 本回合结果（可编辑后保存，再回到 CLI 按回车继续）",
        "# 格式：## scope / ## character_角色id，下为 key: value；若有 body_narrative 则为本回合正文（≤2000字）",
        "",
    ]
    if result.body_narrative and result.body_narrative.strip():
        lines.append("## body_narrative")
        lines.append("# 本回合小说正文（≤2000字），以下为正文内容")
        lines.append(result.body_narrative.strip())
        lines.append("")
    lines.extend([
        "## scope",
        "event_summary: " + (result.scope_output.event_summary or "").replace("\n", " "),
        "",
    ])
    for cid in sorted(result.character_outputs.keys()):
        out = result.character_outputs[cid]
        lines.append(f"## character_{cid}")
        lines.append("inner_monologue: " + (out.inner_monologue or "").replace("\n", " "))
        lines.append("dialogue_action: " + (out.dialogue_action or "").replace("\n", " "))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _parse_turn_result_edit_file(path: Path, original: TurnResult) -> TurnResult | None:
    """从编辑后的文件解析出 TurnResult（失败返回 None）。支持 body_narrative 段。"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    scope_event_summary = original.scope_output.event_summary
    body_narrative = original.body_narrative or ""
    char_data: dict[str, dict[str, str]] = {}
    current = None
    body_lines: list[str] = []
    for line in text.splitlines():
        line_raw = line
        line = line.rstrip()
        if line.startswith("## body_narrative"):
            current = "body"
            body_lines = []
            continue
        if line.startswith("## scope"):
            current = "scope"
            if body_lines:
                body_narrative = "\n".join(body_lines).strip()
            continue
        if line.startswith("## character_"):
            if current == "body" and body_lines:
                body_narrative = "\n".join(body_lines).strip()
            cid = line[13:].strip()
            current = cid
            char_data[cid] = {"inner_monologue": "", "dialogue_action": ""}
            continue
        if current == "body" and not line.startswith("#"):
            body_lines.append(line_raw)
            continue
        if current == "scope" and line.startswith("event_summary:"):
            scope_event_summary = line[14:].strip()
            continue
        if current and current != "scope" and current != "body" and ":" in line:
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if current in char_data and key in ("inner_monologue", "dialogue_action"):
                char_data[current][key] = value
    if current == "body" and body_lines:
        body_narrative = "\n".join(body_lines).strip()

    new_scope = ScopeTurnOutput(
        constraints=original.scope_output.constraints,
        event_summary=scope_event_summary,
        state_delta=original.scope_output.state_delta,
    )
    new_char_outputs = {}
    for cid in original.character_outputs:
        out = original.character_outputs[cid]
        data = char_data.get(cid, {})
        new_char_outputs[cid] = CharacterTurnOutput(
            inner_monologue=data.get("inner_monologue", out.inner_monologue),
            dialogue_action=data.get("dialogue_action", out.dialogue_action),
            metadata=out.metadata,
        )
    return TurnResult(
        scope_output=new_scope,
        character_outputs=new_char_outputs,
        body_narrative=body_narrative if body_narrative else original.body_narrative,
    )


def _write_memory_plan_edit_file(path: Path, result: TurnResult, scope_id: str, time: str, place: str) -> None:
    """将即将写回的记忆写成可编辑的每行 角色id: 摘要。"""
    lines = [
        "# 即将写回各角色记忆（可编辑后保存，再回到 CLI 按回车继续）",
        "# 每行：角色id: 摘要内容",
        "",
    ]
    for cid in sorted(result.character_outputs.keys()):
        out = result.character_outputs[cid]
        summary = (out.dialogue_action or out.inner_monologue or "").strip() or "（本回合无言行摘要）"
        lines.append(f"{cid}: {summary}")
    path.write_text("\n".join(lines), encoding="utf-8")


def _parse_memory_plan_edit_file(path: Path, original: TurnResult) -> TurnResult | None:
    """从编辑后的记忆文件解析，得到修改后的 TurnResult（仅更新各角色 dialogue_action 为摘要）。"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    summaries: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            cid, _, rest = line.partition(":")
            cid, summary = cid.strip(), rest.strip()
            if cid in original.character_outputs:
                summaries[cid] = summary
    new_char_outputs = {}
    for cid, out in original.character_outputs.items():
        s = summaries.get(cid, (out.dialogue_action or out.inner_monologue or "").strip())
        new_char_outputs[cid] = CharacterTurnOutput(
            inner_monologue=out.inner_monologue,
            dialogue_action=s or out.dialogue_action,
            metadata=out.metadata,
        )
    return TurnResult(scope_output=original.scope_output, character_outputs=new_char_outputs)


def review_turn_result(
    result: TurnResult,
    scope_id: str,
    time: str,
    place: str,
    *,
    input_fn: Callable[[str], str] | None = None,
    edit_output_dir: Path | None = None,
    supplement_callback: Callable[[str, str, str, str], None] | None = None,
    runtime_config: dict | None = None,
    config_dir: Path | None = None,
    project_root: Path | None = None,
    storage: Any | None = None,
) -> tuple[bool, TurnResult | None]:
    """
    阶段一：展示本回合结果。作者可 y 确认 / e 先修改 / s 补充设定 / n 驳回；
    也可直接输入对本回合正文的修改意见，系统将根据反馈修订正文后再次展示，直到作者表示没问题后确认。
    同意后返回 (True, result_to_use)，驳回返回 (False, None)。
    """
    while True:
        logger.info("--- 阶段一：本回合结果审阅 ---")
        logger.info("  ** 可先修改再确认：如需修改请选 e 将内容写入文件，编辑后保存再回到此处确认。**")
        logger.info("  范围 scope_id=%s, time=%s, place=%s", scope_id, time, place)
        if result.body_narrative and result.body_narrative.strip():
            logger.info("  [本回合正文（≤2000字）] %s", result.body_narrative.strip())
        else:
            logger.info("  [Scope] 事件摘要: %s", result.scope_output.event_summary or "（无）")
        if result.scope_output.constraints:
            logger.info("  [Scope] 约束: %s", result.scope_output.constraints)
        for cid in sorted(result.character_outputs.keys()):
            out = result.character_outputs[cid]
            logger.info("  [角色 %s] 内心独白: %s", cid, out.inner_monologue or "（无）")
            logger.info("  [角色 %s] 言行: %s", cid, out.dialogue_action or "（无）")
        resolved = (
            result.body_narrative.strip()
            if result.body_narrative and result.body_narrative.strip()
            else resolve_turn_conflict(result.scope_output, result.character_outputs)
        )
        logger.info("  [裁决后将写入事件簿的摘要] %s", resolved)

        prompt_msg = (
            "\n同意写回？(y 确认 / e 先修改 / s 补充设定 / n 驳回)；"
            "或直接输入对本回合正文的修改意见，将根据意见修订正文后再次展示。\n"
            f"  ** {CONFIRM_HINT} **\n"
            "请输入: "
        )
        ans = _prompt(prompt_msg, input_fn).strip()
        rt = runtime_config or {}
        if config_dir is not None and project_root is not None and storage is not None:
            # 懒加载：避免 author_loop 包初始化 → cli → author_harness → retrieve_for_intent → author_loop 环状 import
            from src.author_harness.author_harness import apply_main_writing_review_ingress

            _ing = apply_main_writing_review_ingress(
                ans or "y",
                config_dir=config_dir,
                project_root=project_root,
                runtime_config=rt,
                storage=storage,
                scope_id=scope_id,
            )
            intent = _ing.intent_cli
            logger.info(
                "  [作者在环] phase=%s scope_id=%s intent_id=%s intent_cli=%s retrieval_sources=%s retrieval_chars=%d",
                PHASE_MAIN_WRITING_REVIEW,
                scope_id,
                _ing.classification.intent_id,
                intent,
                ",".join(s.source for s in _ing.retrieval_snippets),
                len(_ing.retrieval_block),
            )
            _assembled = _ing.retrieval_block
        else:
            intent = understand_author_review_intent(ans or "y", rt)
            _assembled = ""

        if intent == "reject":
            return (False, None)
        if intent == "supplement" and supplement_callback is not None:
            supplement_callback(scope_id, time, place, result.scope_output.event_summary or "")
            continue
        if intent == "edit" and edit_output_dir is not None:
            edit_output_dir.mkdir(parents=True, exist_ok=True)
            name = "turn_" + datetime.now().strftime("%Y-%m-%d_%H-%M") + ".md"
            path = edit_output_dir / name
            _write_turn_result_edit_file(path, result)
            logger.info("  已写入：%s", path)
            _prompt("请编辑上述文件后保存，保存后按回车继续。", input_fn)
            modified = _parse_turn_result_edit_file(path, result)
            if modified is None:
                logger.warning("  解析失败，使用原结果。")
                return (True, result)
            return (True, modified)
        if intent == "confirm":
            return (True, result)
        # intent == "revise"：根据作者反馈修订本回合正文后再次展示
        current_body = (
            (result.body_narrative and result.body_narrative.strip())
            or (result.scope_output.event_summary or "").strip()
        )
        if not current_body:
            logger.info("  当前无正文可修订，请选 y 确认或 e 编辑。")
            continue
        logger.info("  正在根据作者反馈修订正文…")
        revised = revise_body_by_feedback(
            current_body,
            ans,
            result.scope_output.constraints or [],
            rt,
            max_chars=DEFAULT_MAX_BODY_CHARS,
            assembled_context=_assembled if config_dir is not None and project_root is not None and storage is not None else "",
        )
        result.body_narrative = revised
        logger.info("  [修订后本回合正文] %s", revised[:200] + ("…" if len(revised) > 200 else ""))
        continue


def review_memory_plan(
    result: TurnResult,
    scope_id: str,
    time: str,
    place: str,
    *,
    input_fn: Callable[[str], str] | None = None,
    edit_output_dir: Path | None = None,
    supplement_callback: Callable[[str, str, str, str], None] | None = None,
) -> tuple[bool, TurnResult | None]:
    """
    阶段二：展示即将写回各角色记忆，提醒可先修改再确认；确认后返回 (True, result_to_use)，否则 (False, None)。
    可选 s 补充设定：调用 supplement_callback 后继续审阅。
    """
    while True:
        logger.info("--- 阶段二：即将写回各角色记忆 ---")
        logger.info(
            "  [作者在环] phase=%s scope_id=%s time=%s place=%s",
            PHASE_MEMORY_PLAN_REVIEW,
            scope_id,
            time,
            place,
        )
        logger.info("  ** 可先修改再确认：如需修改请选 e 将内容写入文件，编辑后保存再回到此处确认。**")
        for cid in sorted(result.character_outputs.keys()):
            out = result.character_outputs[cid]
            summary = (out.dialogue_action or out.inner_monologue or "").strip() or "（本回合无言行摘要）"
            logger.info("  角色 %s: append_event_refinement(scope_id=%s, time=%s, place=%s, summary=%r)", cid, scope_id, time, place, summary)

        prompt_msg = "\n确认写回以上角色记忆？(y 直接确认 / e 先修改 / s 补充设定 / n 不写回，默认 y): "
        ans = _prompt(prompt_msg, input_fn).lower() or "y"

        if ans in ("n", "no", "否"):
            logger.info(
                "  [作者在环] phase=%s scope_id=%s memory_plan_action=%s",
                PHASE_MEMORY_PLAN_REVIEW,
                scope_id,
                "reject",
            )
            return (False, None)
        if ans in ("s", "补充", "设定") and supplement_callback is not None:
            logger.info(
                "  [作者在环] phase=%s scope_id=%s memory_plan_action=%s",
                PHASE_MEMORY_PLAN_REVIEW,
                scope_id,
                "supplement",
            )
            turn_summary = (result.scope_output.event_summary or "").strip()
            supplement_callback(scope_id, time, place, turn_summary)
            continue
        if ans in ("e", "edit", "修改") and edit_output_dir is not None:
            edit_output_dir.mkdir(parents=True, exist_ok=True)
            name = "memory_" + datetime.now().strftime("%Y-%m-%d_%H-%M") + ".md"
            path = edit_output_dir / name
            _write_memory_plan_edit_file(path, result, scope_id, time, place)
            logger.info("  已写入：%s", path)
            _prompt("请编辑上述文件后保存，保存后按回车继续。", input_fn)
            modified = _parse_memory_plan_edit_file(path, result)
            if modified is None:
                logger.warning("  解析失败，使用原结果。")
                logger.info(
                    "  [作者在环] phase=%s scope_id=%s memory_plan_action=%s",
                    PHASE_MEMORY_PLAN_REVIEW,
                    scope_id,
                    "edit_fallback",
                )
                return (True, result)
            logger.info(
                "  [作者在环] phase=%s scope_id=%s memory_plan_action=%s",
                PHASE_MEMORY_PLAN_REVIEW,
                scope_id,
                "edit",
            )
            return (True, modified)
        logger.info(
            "  [作者在环] phase=%s scope_id=%s memory_plan_action=%s character_count=%d",
            PHASE_MEMORY_PLAN_REVIEW,
            scope_id,
            "confirm",
            len(result.character_outputs),
        )
        return (True, result)
