"""
小说主流程（作者在环）：每回合先不写回 → 阶段一审阅同意后写回事件簿/状态 → 阶段二确认后写回角色记忆。
在项目根执行：python run_novel_with_author.py（Linux：python3；或 .venv/bin/python）
可选环境变量：MIN_AUTOBOOK_TURNS=2 指定回合数；MIN_AUTOBOOK_LOG_LEVEL=DEBUG 指定日志级别；
MIN_AUTOBOOK_RECENT_TURNS=3 启动时展示最近若干回合的正文进展（默认 3，约等于「最近一章」粒度）。
main() 支持可选参数 input_fn（与 AuthorSession 一致），供测试或外挂 UI 注入读入逻辑。
"""
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.log_config import setup_logging, apply_design_phase_debug
from src.orchestrator import Orchestrator
from src.author_loop import review_turn_result, review_memory_plan, run_design_phase
from src.author_loop.author_session import AuthorSession
from src.author_loop.author_classified_memory import (
    append_classified_entries,
    classify_author_input,
    get_author_memory_root,
    print_startup_resume,
)
from src.author_loop.novel_bootstrap import (
    ensure_current_novel_for_design_phase,
    interactive_resolve_novel_for_design_phase,
    prepare_new_novel_if_needed,
)
from src.author_loop.novel_identity import confirm_title_and_persist
from src.author_loop.design_phase import run_supplement_setting_during_turn
from src.author_loop.turn_planning import (
    generate_turn_plan_for_turn,
    generate_turn_body,
    revise_turn_plan_with_author_requirements,
    DEFAULT_MAX_BODY_CHARS,
)
from src.context import build_turn_context_from_storage
from src.config import current_novel_root, get_initial_scene, load_runtime_config
from src.llm import get_llm_provider
from src.runtime import file_sync as runtime_file_sync
from src.runtime.outline_store import (
    build_outline_prompt_snippet,
    load_outline_snapshot,
    outline_injection_options,
    resolve_current_beat,
)
from src.runtime.protagonist import resolve_protagonist_id


def main(input_fn: Callable[[str], str] | None = None) -> None:
    log = setup_logging(PROJECT_ROOT)
    log.info("小说主流程启动（作者在环模式）")
    sys.stdout.flush()
    sys.stderr.flush()

    config_dir = PROJECT_ROOT / "config"
    log.debug("[启动] 配置目录: %s", config_dir)

    # 先单独加载 runtime 以读取 debug 开关，再应用 DEBUG 日志，这样后续 load_all_config 的 DEBUG 才会输出
    runtime_pre = load_runtime_config(config_dir)
    apply_design_phase_debug(runtime_pre)
    # 新小说引导：若无设定且无正文，自动准备最小配置并强制进入完整设定交互
    bootstrap_triggered = prepare_new_novel_if_needed(
        config_dir=config_dir,
        project_root=PROJECT_ROOT,
        runtime_config=runtime_pre,
        log=log,
    )
    if bootstrap_triggered:
        # 若引导过程更新了配置（如强制 setting_research=design_only），重新加载一次 runtime
        runtime_pre = load_runtime_config(config_dir)
        apply_design_phase_debug(runtime_pre)

    log.debug("[启动] 加载配置并创建编排器...")
    orch = Orchestrator.from_config(config_dir)
    runtime = orch.runtime_config
    log.debug("[启动] 编排器已创建")
    framework = runtime.get("framework") or {}
    llm_key = (framework.get("llm") or "dummy").strip().lower()
    try:
        provider = get_llm_provider(runtime)
        log.info("LLM 配置: framework.llm=%s, Provider=%s", llm_key, type(provider).__name__)
    except Exception as e:
        log.warning("获取 LLM Provider 失败: %s", e)

    enabled_char = list(runtime.get("agents", {}).get("characters", {}).get("enabled_ids", []))
    present = [c for c in enabled_char if c in orch.character_agents]
    scene = get_initial_scene(orch.runtime_config, orch.world_config)
    scope_id = scene["scope_id"]
    time_str = scene["time"]
    place = scene["place"]

    log.info("开局场景: scope_id=%s, time=%s, place=%s", scope_id, time_str, place)
    log.info("在场角色: %s", present)
    _prot_id, _prot_name = resolve_protagonist_id(runtime, orch.characters_config)
    if _prot_id:
        log.info("[叙事主角] %s（id=%s）", _prot_name, _prot_id)

    _setting = (runtime.get("runtime") or runtime).get("setting_research") or {}
    print_startup_resume(
        config_dir=config_dir,
        project_root=PROJECT_ROOT,
        runtime_config=runtime,
        storage=orch.storage,
        scope_id=scope_id,
        show_design_hint=bool(
            _setting.get("enabled") and _setting.get("trigger") == "design_only"
        ),
        recent_turns_k=max(1, min(20, int(os.environ.get("MIN_AUTOBOOK_RECENT_TURNS", "3")))),
    )

    n = int(os.environ.get("MIN_AUTOBOOK_TURNS", "2"))
    n = max(1, min(n, 100))
    log.info("计划执行 %s 回合（每回合需作者审阅）", n)

    # 开书前设定阶段：若启用且 trigger=design_only，先与设定研究 Agent 沟通完善世界模型与设定
    inner_runtime = runtime.get("runtime") or runtime
    setting_research = inner_runtime.get("setting_research") or {}
    log.debug("[启动] setting_research enabled=%s, trigger=%s", setting_research.get("enabled"), setting_research.get("trigger"))
    author_session: AuthorSession | None = None
    if setting_research.get("enabled") and setting_research.get("trigger") == "design_only":
        log.debug("[启动] 进入设定阶段 run_design_phase")
        novel_root_before = current_novel_root(config_dir)
        gate_ok = ensure_current_novel_for_design_phase(
            config_dir=config_dir,
            project_root=PROJECT_ROOT,
            runtime_config=runtime,
            log=log,
            world_config=orch.world_config,
            characters_config=orch.characters_config,
        )
        if not gate_ok:
            log.info("进入交互引导：请新建初稿或绑定已有作品目录。")
            gate_ok = interactive_resolve_novel_for_design_phase(
                config_dir=config_dir,
                project_root=PROJECT_ROOT,
                runtime_config=runtime,
                world_config=orch.world_config,
                characters_config=orch.characters_config,
                log=log,
                input_fn=input_fn or input,
            )
        if not gate_ok:
            log.error("无法进入设定阶段：缺少有效作品目录。请按上述提示操作后重新启动。")
            sys.exit(1)
        if current_novel_root(config_dir) != novel_root_before:
            runtime = load_runtime_config(config_dir)
            apply_design_phase_debug(runtime)
            orch = Orchestrator.from_config(config_dir)
            runtime = orch.runtime_config
            enabled_char = list(runtime.get("agents", {}).get("characters", {}).get("enabled_ids", []))
            present = [c for c in enabled_char if c in orch.character_agents]
            scene = get_initial_scene(runtime, orch.world_config)
            scope_id = scene["scope_id"]
            time_str = scene["time"]
            place = scene["place"]
        config_edited = run_design_phase(
            config_dir,
            runtime,
            orch.world_config,
            orch.characters_config,
        )
        if config_edited:
            log.info("设定已编辑，重新加载配置与编排器。")
            orch = Orchestrator.from_config(config_dir)
            runtime = orch.runtime_config
            scene = get_initial_scene(runtime, orch.world_config)
            scope_id = scene["scope_id"]
            time_str = scene["time"]
            place = scene["place"]
            enabled_char = list(runtime.get("agents", {}).get("characters", {}).get("enabled_ids", []))
            present = [c for c in enabled_char if c in orch.character_agents]
            log.info("开局场景: scope_id=%s, time=%s, place=%s", scope_id, time_str, place)
            log.info("在场角色: %s", present)
            print_startup_resume(
                config_dir=config_dir,
                project_root=PROJECT_ROOT,
                runtime_config=runtime,
                storage=orch.storage,
                scope_id=scope_id,
                show_design_hint=False,
                recent_turns_k=max(1, min(20, int(os.environ.get("MIN_AUTOBOOK_RECENT_TURNS", "3")))),
            )
        # 设定完成后（新小说首次）进入书名确认并持久化 meta/index/current_novel
        special_after_design = None
        try:
            from src.config import load_special_settings_config

            special_after_design = load_special_settings_config(config_dir)
        except Exception:
            pass
        author_session = AuthorSession.for_main_loop(
            config_dir=config_dir,
            project_root=PROJECT_ROOT,
            runtime_config=runtime,
            input_fn=input_fn,
        )
        confirm_title_and_persist(
            config_dir=config_dir,
            project_root=PROJECT_ROOT,
            runtime_config=runtime,
            world_config=orch.world_config,
            characters_config=orch.characters_config,
            special_settings=special_after_design,
            input_fn=author_session.read_line,
            log=log,
        )
        # 若首次确认了小说身份（current_novel），重建编排器以切换到小说级配置与数据目录
        try:
            from src.author_loop.novel_identity import has_current_novel_pointer

            if has_current_novel_pointer(config_dir):
                orch = Orchestrator.from_config(config_dir)
                nr = current_novel_root(config_dir)
                if nr:
                    log.info("已切换到当前小说目录：%s", nr)
                runtime = orch.runtime_config
                scene = get_initial_scene(runtime, orch.world_config)
                scope_id = scene["scope_id"]
                time_str = scene["time"]
                place = scene["place"]
                enabled_char = list(runtime.get("agents", {}).get("characters", {}).get("enabled_ids", []))
                present = [c for c in enabled_char if c in orch.character_agents]
                author_session.runtime_config = runtime
        except Exception:
            pass

    # 大纲 MVP-0/1：若 data_root 下存在 book/outline/outline.yaml 则加载并打日志（无文件则跳过）
    try:
        _outline_dr = runtime_file_sync.get_data_root(PROJECT_ROOT, runtime)
        _outline_snap_boot = load_outline_snapshot(_outline_dr)
        if _outline_snap_boot:
            log.info("[大纲] %s", _outline_snap_boot.log_line())
            for _ow in _outline_snap_boot.warnings:
                log.debug("[大纲] 校验: %s", _ow)
    except Exception as _ox:
        log.debug("加载大纲快照失败（忽略）: %s", _ox)

    edit_output_dir = PROJECT_ROOT / "dev_agent" / "output" / "author_edits"
    log.debug("作者编辑输出目录: %s", edit_output_dir)

    if author_session is None:
        author_session = AuthorSession.for_main_loop(
            config_dir=config_dir,
            project_root=PROJECT_ROOT,
            runtime_config=runtime,
            input_fn=input_fn,
        )
    else:
        author_session.runtime_config = runtime

    def make_supplement_callback(sid: str, t: str, p: str, summary: str) -> None:
        run_supplement_setting_during_turn(
            config_dir,
            runtime,
            orch.world_config,
            sid,
            t,
            p,
            summary,
            input_fn=author_session.read_line,
        )

    last_summary = ""
    for turn in range(n):
        log.info("===== 回合 %s/%s =====", turn + 1, n)
        outline_snippet = ""
        try:
            _dr_turn = runtime_file_sync.get_data_root(PROJECT_ROOT, runtime)
            _snap_turn = load_outline_snapshot(_dr_turn)
            outline_snippet = build_outline_prompt_snippet(
                runtime, _snap_turn, orch.characters_config
            )
            if _snap_turn and outline_snippet:
                _opts_turn = outline_injection_options(runtime)
                if _opts_turn["enabled"]:
                    _bc = resolve_current_beat(
                        _snap_turn, soft_max_turns=_opts_turn["soft_max_turns"]
                    )
                    if _bc:
                        log.info(
                            "[大纲进度] chapter=%s beat=%s turns_in_beat=%s/%s",
                            _bc.chapter_id,
                            _bc.beat_id,
                            _bc.turns_in_beat,
                            _opts_turn["soft_max_turns"],
                        )
        except Exception as _oe:
            log.debug("本回合大纲片段构建失败（忽略）: %s", _oe)
        # 先呈现本回合写作前分析及预计字数，作者同意后再生成本回合正文（≤2000 字）
        plan = generate_turn_plan_for_turn(
            orch.storage,
            orch.world_config,
            runtime,
            scope_id=scope_id,
            time=time_str,
            place=place,
            present_character_ids=present,
            last_turn_summary=last_summary,
            project_root=PROJECT_ROOT,
            outline_snippet=outline_snippet,
        )
        log.info("--- 本回合写作前分析 ---")
        log.info("%s", plan.analysis)
        default_max = (
            runtime.get("turn_body_max_chars")
            or runtime.get("runtime", {}).get("turn_body_max_chars")
            or DEFAULT_MAX_BODY_CHARS
        )
        log.info("本回合预计字数：%s（正文上限默认 %s 字，可临时修改）", plan.estimated_chars, default_max)
        max_chars_input = author_session.read_line(
            "\n本回合正文上限（字，直接回车使用 {}）：".format(default_max)
        )
        if max_chars_input:
            try:
                max_chars_this_turn = max(100, min(10000, int(max_chars_input)))
            except ValueError:
                max_chars_this_turn = default_max
        else:
            max_chars_this_turn = default_max
        author_requirements_parts: list[str] = []
        while True:
            req_input = author_session.read_line(
                "可在此补充对本回合正文的要求（如视角、语气、禁止出现的内容等，直接回车跳过）："
            )
            if not req_input:
                break
            author_requirements_parts.append(req_input)
            br = get_author_memory_root(PROJECT_ROOT, runtime)
            if br:
                classified = classify_author_input(req_input, runtime)
                append_classified_entries(
                    br, scope_id, req_input, classified, runtime_config=runtime
                )
                log.info(
                    "作者输入已归类持久化: %s → %s",
                    classified.get("one_line", "")[:60],
                    classified.get("categories"),
                )
            log.info("作者已补充要求，正在由大模型修订本回合写作前分析…")
            plan = revise_turn_plan_with_author_requirements(plan, req_input, runtime)
            log.info("--- 修订后本回合写作前分析 ---")
            log.info("%s", plan.analysis)
            log.info("本回合预计字数：%s", plan.estimated_chars)
        author_requirements = "\n".join(author_requirements_parts)
        confirm = (
            author_session.read_line(
                "\n同意按此分析生成本回合正文？(y=生成正文, n=跳过本回合, 默认 y): "
            ).lower()
            or "y"
        )
        if confirm in ("n", "no", "否"):
            log.info("作者未同意，本回合跳过。")
            continue
        result = orch.run_one_turn(
            scope_id=scope_id,
            time=time_str,
            place=place,
            present_character_ids=present,
            last_turn_summary=last_summary,
            auto_write=False,
        )
        ctx = build_turn_context_from_storage(
            scope_id=scope_id,
            time=time_str,
            place=place,
            present_character_ids=present,
            storage=orch.storage,
            world_config=orch.world_config,
            last_turn_summary=last_summary,
        )
        body = generate_turn_body(
            plan, result, ctx, runtime,
            max_chars=max_chars_this_turn,
            author_requirements=author_requirements,
            outline_snippet=outline_snippet,
        )
        result.body_narrative = body
        approved, result_phase1 = review_turn_result(
            result, scope_id, time_str, place,
            edit_output_dir=edit_output_dir,
            supplement_callback=make_supplement_callback,
            runtime_config=runtime,
            input_fn=author_session.read_line,
            config_dir=config_dir,
            project_root=PROJECT_ROOT,
            storage=orch.storage,
        )
        if not approved or result_phase1 is None:
            log.info("作者驳回，本回合不写回事件簿/状态，跳过阶段二。")
            # 允许作者在“驳回后”直接修改写作前分析再试一次（而不是直接跳过本回合）。
            retry_ans = author_session.read_line(
                "\n作者不满意已选择驳回：是否要在本回合内修改写作前分析并重新生成正文？"
                "(y=修改重试，n=跳过本回合，默认 n): "
            ).lower()
            can_retry = retry_ans in ("y", "yes", "是")
            if can_retry:
                # 复用前面已有的 author_requirements_parts：把“分析修改意图”也纳入正文生成的要求，
                # 以保证分析与正文的约束一致。
                while True:
                    req_input = author_session.read_line(
                        "可在此补充对本回合写作前分析的要求（直接回车结束）："
                    )
                    if not req_input:
                        break
                    author_requirements_parts.append(req_input)
                    br = get_author_memory_root(PROJECT_ROOT, runtime)
                    if br:
                        classified = classify_author_input(req_input, runtime)
                        append_classified_entries(
                            br, scope_id, req_input, classified, runtime_config=runtime
                        )
                        log.info(
                            "作者输入已归类持久化: %s → %s",
                            classified.get("one_line", "")[:60],
                            classified.get("categories"),
                        )
                    log.info("作者已补充分析要求，正在由大模型修订本回合写作前分析…")
                    plan = revise_turn_plan_with_author_requirements(plan, req_input, runtime)
                    log.info("--- 修订后本回合写作前分析 ---")
                    log.info("%s", plan.analysis)
                    log.info("本回合预计字数：%s", plan.estimated_chars)

                author_requirements = "\n".join(author_requirements_parts)
                gen_confirm = (
                    author_session.read_line(
                        "\n同意按修订后的分析生成本回合正文？(y=生成正文, n=跳过本回合, 默认 y): "
                    ).lower()
                    or "y"
                )
                if gen_confirm not in ("n", "no", "否"):
                    body = generate_turn_body(
                        plan, result, ctx, runtime,
                        max_chars=max_chars_this_turn,
                        author_requirements=author_requirements,
                        outline_snippet=outline_snippet,
                    )
                    result.body_narrative = body
                    approved, result_phase1 = review_turn_result(
                        result, scope_id, time_str, place,
                        edit_output_dir=edit_output_dir,
                        supplement_callback=make_supplement_callback,
                        runtime_config=runtime,
                        input_fn=author_session.read_line,
                        config_dir=config_dir,
                        project_root=PROJECT_ROOT,
                        storage=orch.storage,
                    )
                else:
                    log.info("作者选择跳过：本回合不再重新生成正文。")

            last_summary = result.scope_output.event_summary
            # 若重试后仍驳回，则直接跳过本回合进入下一回合。
            if not approved or result_phase1 is None:
                continue
        orch.apply_event_and_state_write(result_phase1, scope_id, time_str, place)
        confirmed, result_phase2 = review_memory_plan(
            result_phase1, scope_id, time_str, place,
            edit_output_dir=edit_output_dir,
            supplement_callback=make_supplement_callback,
            input_fn=author_session.read_line,
        )
        if confirmed and result_phase2 is not None:
            orch.apply_memory_write(result_phase2, scope_id, time_str, place)
            log.info("已写回角色记忆。")
        elif confirmed:
            orch.apply_memory_write(result_phase1, scope_id, time_str, place)
            log.info("已写回角色记忆。")
        else:
            log.info("未写回角色记忆。")
        last_summary = result_phase1.scope_output.event_summary

    events = orch.storage.get_recent_events(scope_id, k=n)
    log.info("已执行 %s 回合写回，scope=%s，事件簿最近 %s 条。", len(events), scope_id, len(events))


if __name__ == "__main__":
    print("小说主流程（作者在环）启动中...", flush=True)
    try:
        main()
    except (EOFError, KeyboardInterrupt) as e:
        # 交互被中断（如 Ctrl+C / stdin 关闭）：优雅退出，不打印崩溃栈
        print(f"\n交互已中断（{type(e).__name__}），程序退出。未确认的回合内容不会写回。", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"运行异常: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
