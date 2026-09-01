"""
小说主流程（作者在环）：每回合先不写回 → 阶段一审阅同意后写回事件簿/状态 → 阶段二确认后写回角色记忆。
在项目根执行：python run_novel_with_author.py（Linux：python3；或 .venv/bin/python）
可选环境变量：MIN_AUTOBOOK_TURNS=2 指定回合数；MIN_AUTOBOOK_LOG_LEVEL=DEBUG 指定日志级别；
MIN_AUTOBOOK_RECENT_TURNS=3 启动时展示最近若干回合的正文进展（默认 3，约等于「最近一章」粒度）。
main() 支持可选参数 input_fn（与 AuthorSession 一致），供测试或外挂 UI 注入读入逻辑。
"""
import logging
import os
import re
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
    advance_to_next_beat,
    bump_turns_in_beat,
    load_outline_snapshot,
    resolve_outline_context,
    save_progress,
)
from src.runtime.protagonist import format_main_characters_snippet, resolve_protagonist_id
from src.runtime.protagonist_switch import format_lens_snippet


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
    # G4c 互斥门：author_workbench.enabled=true 且未注入输入源（如前端 adapter）时，
    # 终端不读 stdin、仅日志，作者交互转前端（D9 §6.1/§10 + D13 §6.1）。
    _awb_enabled = bool(
        ((runtime_pre.get("runtime") or {}).get("author_workbench") or {}).get("enabled", False)
    )
    if input_fn is None and _awb_enabled:
        from src.author_harness.workbench_ingress import LogOnlyAuthorIngress

        input_fn = LogOnlyAuthorIngress()
        log.info(
            "[作者在环] author_workbench.enabled=true：作者交互转前端；终端仅日志（不读 stdin）。"
        )
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
    # G3 运行时镜头：会话内 override（state/protagonist_runtime.yaml）> 配置期主角；默认无 override → 等价旧版。
    try:
        from src.runtime.capabilities import resolve_features, save_features
        from src.runtime.protagonist_switch import (
            ProtagonistContext,
            effective_protagonist,
            load_protagonist_context,
            save_protagonist_context,
        )
        _g3_dr0 = runtime_file_sync.get_data_root(PROJECT_ROOT, runtime)
        _prot_ctx = load_protagonist_context(_g3_dr0) if _g3_dr0 else ProtagonistContext()
        _prot_id, _prot_name = effective_protagonist(runtime, orch.characters_config, _prot_ctx)
        _features_flags = resolve_features(runtime, data_root=_g3_dr0)
    except Exception as _g3e:
        _prot_ctx = ProtagonistContext()
        _prot_id, _prot_name = resolve_protagonist_id(runtime, orch.characters_config)
        _features_flags = None
        log.warning("运行时镜头/能力外观面初始化失败（按配置期与默认回退）: %s", _g3e)
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
            # 必须透传：input_fn 缺失时 AuthorSession.read_line 回退 builtin input()，
            # Web 会话（nohup 无 stdin）会 EOFError。透传后设计阶段的交互（含危险覆盖确认）
            # 全部桥接前端 adapter。
            input_fn=input_fn,
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
    # G3：主角与主要角色提示块按**当前镜头**重建（默认 = 配置期，等价旧版）；换镜头后同一函数跟 _prot_id/_prot_name。
    def _rebuild_prot_snippet() -> str:
        return format_lens_snippet(_prot_id, _prot_name, orch.characters_config)

    def _write_g3_canonical(dr: Path, chapter_id: str, body: str) -> Path:
        """把已提升的备选稿正文落为 canonical 成文副本（不覆盖实时 turn 文件）。"""
        _safe = re.sub(r"[^A-Za-z0-9_.\-]+", "_", chapter_id or "ch")
        _cp = Path(dr) / "book" / "content" / "drafts" / f"{_safe}.md"
        _cp.parent.mkdir(parents=True, exist_ok=True)
        _cp.write_text(f"# {chapter_id}\n\n{body or ''}", encoding="utf-8")
        return _cp

    main_characters_snippet = _rebuild_prot_snippet()
    if main_characters_snippet:
        log.debug("[主角注入] 已生成主角与主要角色提示块（镜头=%s）", _prot_name)
    _outline_warned = False  # Opt-6：首损 WARN 一次、连续失败才降级 debug
    # G3 能力外观面：统一开关。默认无 features → 逐字段回退旧深层位置（与旧行为逐字节等价）。
    _flags = _features_flags if _features_flags is not None else resolve_features(runtime, data_root=None)
    # G1 屏外线：保留 parallel_threads 配置块读参（trigger/batch_turns/bridge_ids），enable 统一走 _flags。
    pt_cfg = runtime.get("parallel_threads") or {}
    if not pt_cfg:
        pt_cfg = (runtime.get("runtime") or {}).get("parallel_threads") or {}
    # G2 演进层↔叙事策略层：保留 evolution_pacing 配置块读参，enable 统一走 _flags。
    _evo_cfg = runtime.get("evolution_pacing") or {}
    if not _evo_cfg:
        _evo_cfg = (runtime.get("runtime") or {}).get("evolution_pacing") or {}
    _evo_enabled = bool(_flags.evolution_pacing)
    for turn in range(n):
        log.info("===== 回合 %s/%s =====", turn + 1, n)
        outline_snippet = ""
        outline_beat = None
        _dr_turn = None
        _snap_turn = None
        try:
            _dr_turn = runtime_file_sync.get_data_root(PROJECT_ROOT, runtime)
            _snap_turn = load_outline_snapshot(_dr_turn)
            if _snap_turn is not None:
                # 单次解析（Opt 3/4）：prompt 注入与进度日志、推进写回复用同一 beat
                outline_snippet, outline_beat = resolve_outline_context(
                    runtime,
                    _snap_turn,
                    orch.characters_config,
                    protagonist_id=_prot_id,
                    protagonist_display_name=_prot_name,
                )
            if outline_beat and outline_beat.missing_ref:
                _p = (_snap_turn.progress if _snap_turn and _snap_turn.progress else {})
                log.warning(
                    "[大纲] 进度引用到不存在的%s（chapter=%s beat=%s），已回退到 %s/%s",
                    outline_beat.missing_ref,
                    _p.get("chapter_id", "?"),
                    _p.get("beat_id", "?"),
                    outline_beat.chapter_id,
                    outline_beat.beat_id,
                )
            if outline_beat:
                log.info(
                    "[大纲进度] chapter=%s beat=%s turns_in_beat=%s/%s",
                    outline_beat.chapter_id,
                    outline_beat.beat_id,
                    outline_beat.turns_in_beat,
                    outline_beat.soft_max_turns,
                )
            _outline_warned = False
        except Exception as _oe:
            if not _outline_warned:
                log.warning("大纲片段构建失败（后续同因降级 debug）: %s", _oe)
                _outline_warned = True
            else:
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
            main_characters_snippet=main_characters_snippet,
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
        # G1c 批处理触发：仅当能力开关 off_screen_batch && trigger=="batch" 时，每 batch_turns 回合
        # 扫一次各关键角色已累积未消费的屏外条目（无新戏自动空转，幂等）。默认关 → 不触发。
        if pt_cfg and bool(_flags.off_screen_batch) and pt_cfg.get("trigger") == "batch":
            _batch_turns = int(pt_cfg.get("batch_turns", 5) or 5)
            if _batch_turns > 0 and (turn + 1) % _batch_turns == 0:
                try:
                    from src.runtime.character_growth import (
                        GrowthGuard,
                        scan_off_screen_batch_for_all,
                    )
                    from src.runtime.file_sync import get_data_root as _batch_get_data_root
                    _batch_dr = _batch_get_data_root(PROJECT_ROOT, runtime)
                    _batch_cids = list(orch.character_agents.keys())
                    _fired_by_char, _b_audit = scan_off_screen_batch_for_all(
                        orch.storage,
                        _batch_dr,
                        character_ids=_batch_cids,
                        guard=GrowthGuard(),
                        max_entries=int(pt_cfg.get("batch_budget_entries", 0) or 0) or None,
                    )
                    if _fired_by_char:
                        log.info(
                            "[屏外批处理] 第 %s 回合扫描：%s",
                            turn + 1,
                            {c: f for c, f in _fired_by_char.items()},
                        )
                    if _b_audit:
                        log.debug("[屏外批处理] guard_audit=%s", _b_audit[:3])
                except Exception as _be:
                    log.warning("屏外批处理失败（忽略，不影响主书）: %s", _be)
        # G2 前馈：开启 evolution_pacing 时加载在场角色成长站姿，前馈给节奏契约与 Critic；否则传 None（行为不变）。
        growth_standings = None
        if _evo_enabled:
            try:
                from src.author_harness.evolution_pacing import (
                    format_standings_hint,
                    load_growth_standings,
                )
                growth_standings = load_growth_standings(
                    _dr_turn, orch.characters_config, present_character_ids=present
                )
                if format_standings_hint(growth_standings):
                    log.debug("[G2] 前馈成长站姿: %s", format_standings_hint(growth_standings))
            except Exception as _ge:
                growth_standings = None
                log.warning("加载成长站姿失败（忽略）: %s", _ge)
        # G1b 桥接：仅当能力开关 bridging 开启 且配置了 bridge_ids 时才注入屏外结果摘要。
        # 默认关闭（false/无配置）→ 空串，不改变主书正文行为。
        bridging_snippet = ""
        if pt_cfg and bool(_flags.bridging):
            try:
                from src.retrieval.bridging import build_bridging_snippet_from_storage
                bridging_snippet = build_bridging_snippet_from_storage(
                    storage=orch.storage,
                    present_character_ids=present,
                    parallel_threads_cfg=pt_cfg,
                    characters_config=orch.characters_config,
                )
            except Exception:
                bridging_snippet = ""
        body = generate_turn_body(
            plan, result, ctx, runtime,
            max_chars=max_chars_this_turn,
            author_requirements=author_requirements,
            outline_snippet=outline_snippet,
            main_characters_snippet=main_characters_snippet,
            bridging_snippet=bridging_snippet,
            growth_standings=growth_standings,
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
                        main_characters_snippet=main_characters_snippet,
                        bridging_snippet=bridging_snippet,
                        growth_standings=growth_standings,
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
        _beat_tags_to_growth = bool(_flags.beat_tags_to_growth)
        orch.apply_event_and_state_write(
            result_phase1,
            scope_id,
            time_str,
            place,
            # G2 反馈：仅当 evolution_pacing.beat_tags_to_growth 开启才把节拍标签透传进成长写回
            # 实影响当回合演进；默认关 → 空元组，行为不变。
            beat_tags=(
                list((outline_beat.tags if outline_beat and outline_beat.tags else ()))
                if _beat_tags_to_growth
                else ()
            ),
        )
        # 大纲 MVP-2：作者在环推进（仅当大纲启用且能定位当前节拍时；无静默跳章）
        if _dr_turn and _snap_turn is not None and outline_beat is not None:
            _cp = _snap_turn.progress or {}
            _base = {
                "version": _cp.get("version", 1),
                "chapter_id": outline_beat.chapter_id,
                "beat_id": outline_beat.beat_id,
                "turns_in_beat": outline_beat.turns_in_beat,
            }
            # 无条件 +1：本回合已被确认并写回（事实记录）
            _p = bump_turns_in_beat(_base)
            save_progress(_dr_turn, _p)
            _adv = author_session.read_line(
                "\n[大纲推进] 本回合已计入本节拍回合数。是否推进节拍？"
                "（+ 仅计入回合/回车, b 进入本草下一节拍, c 进入下一章首拍, s 跳过手改 YAML）: "
            ).strip().lower()
            if _adv in ("b", "next"):
                _ap = advance_to_next_beat(_snap_turn, _p)
                # b=本草下一拍：仅接受同章内的推进；若已跳到下一章则视为本草无下一拍
                if _ap is not None and _ap.get("chapter_id") == _p.get("chapter_id"):
                    save_progress(_dr_turn, _ap)
                    log.info("[大纲推进] 同章 %s→%s", _ap.get("beat_id"), _ap.get("beat_id"))
                elif _ap is not None:
                    log.info("[大纲] 本草无更多节拍，可用 c 进入下一章。")
                else:
                    log.info("[大纲] 已在末章末拍，无可推进节拍。")
            elif _adv in ("c", "chapter"):
                _ap = _p
                for _ in range(64):  # 防御性上限
                    _nxt = advance_to_next_beat(_snap_turn, _ap)
                    if _nxt is None or _nxt.get("chapter_id") != _ap.get("chapter_id"):
                        break
                    _ap = _nxt
                if _nxt is not None and _nxt.get("chapter_id") != _p.get("chapter_id"):
                    save_progress(_dr_turn, _nxt)
                    log.info("[大纲推进] 下一章 %s/%s → %s/%s", _p.get("chapter_id"), _p.get("beat_id"),
                             _nxt.get("chapter_id"), _nxt.get("beat_id"))
                else:
                    log.info("[大纲] 已在末章，无可进入的下一章。")
            elif _adv in ("s", "skip"):
                log.info("[大纲] 作者选择跳过，改由手改 YAML。")
            else:
                log.info("[大纲] 仅计入本回合数（仍停留 %s/%s）。", _p.get("chapter_id"), _p.get("beat_id"))
        # G3 镜头/开关：仅当备选稿能力或工作台开启时展示（默认关 → 零打扰）。显式操作，无静默跳章。
        _g3_show = bool(_flags.alt_draft) or bool(
            ((runtime.get("runtime") or {}).get("author_workbench") or {}).get("enabled", False)
        )
        if _g3_show:
            _g3_ch = (outline_beat.chapter_id if outline_beat and outline_beat.chapter_id else f"turn{turn}")
            _g3_ans = author_session.read_line(
                f"\n[G3 镜头/开关：当前章 {_g3_ch}，镜头={_prot_name}]"
                "（l 换主导镜头, a 候选备选稿, c 开关能力, 回车 继续）: "
            ).strip().lower()
            if _g3_ans == "l":
                _opts = [
                    str(c.get("id")) for c in (orch.characters_config or {}).get("characters", [])
                    if isinstance(c, dict) and c.get("id")
                ]
                if not _opts:
                    log.info("[G3] 无可用角色可切换镜头。")
                else:
                    log.info("[G3] 可选镜头角色: %s（输入 id）", "、".join(_opts))
                    _target = author_session.read_line("切换导出镜头到（角色 id）: ").strip()
                    if _target:
                        from src.runtime.protagonist_switch import switch_protagonist
                        _changed = switch_protagonist(_prot_ctx, runtime, orch.characters_config, _target)
                        if _changed and _changed[0] == _target:
                            _prot_id, _prot_name = _changed
                            main_characters_snippet = _rebuild_prot_snippet()
                            save_protagonist_context(_g3_dr0, _prot_ctx) if _g3_dr0 else None
                            log.info("[G3] 导出镜头已切换：%s（%s）。后续回合按新镜头成文。", _prot_name, _prot_id)
                        else:
                            log.info("[G3] 镜头未切换（目标不在可用列表）。")
                    else:
                        log.info("[G3] 未输入镜头目标，保持 %s。", _prot_name)
            elif _g3_ans == "c":
                _cap = author_session.read_line(
                    "开关能力（输入 能力名;on|off，如 evolution_pacing;on，回车 返回）: "
                ).strip()
                if _cap and ";" in _cap:
                    _n, _v = _cap.split(";", 1)
                    _n = _n.strip()
                    _v = _v.strip().lower() in ("on", "true", "1", "yes", "开")
                    _ov = _flags.to_dict()
                    _ov[_n] = _v
                    _flags = resolve_features(runtime, features_override=_ov, data_root=_g3_dr0)
                    save_features(_g3_dr0, {_n: _v}) if _g3_dr0 else None
                    log.info("[G3] 能力开关 %s → %s（会话内已生效；已写入 features.yaml）", _n, _v)
                else:
                    log.info("[G3] 未改动能力开关。")
            elif _g3_ans == "a":
                from src.runtime.alt_draft import list_alt_drafts, promote_alt_draft
                _drafts = list_alt_drafts(_g3_dr0, _g3_ch) if _g3_dr0 else []
                _draftable = [d for d in _drafts if d.status == "draft"]
                if not _draftable:
                    log.info("[G3] 本章无待提升的候选备选稿（本章已有 %s 条）。", len(_drafts))
                else:
                    _nm = "、".join(d.lens_id for d in _draftable)
                    _pick = author_session.read_line(f"可提升备选稿 lens: {_nm}（输入 lens 提升，回车 返回）: ").strip()
                    if _pick:
                        _hit = next((d for d in _draftable if d.lens_id == _pick), None)
                        if _hit is None:
                            log.info("[G3] 无 lens=%s 的备选稿。", _pick)
                        else:
                            _res = promote_alt_draft(
                                _g3_dr0, _g3_ch, _pick,
                                canonical_writer=(
                                    (lambda b: _write_g3_canonical(_g3_dr0, _g3_ch, b)) if _g3_dr0 else None
                                ),
                            )
                            if _res:
                                from src.runtime.protagonist_switch import switch_protagonist
                                _cp, _lens = _res
                                _changed = switch_protagonist(_prot_ctx, runtime, orch.characters_config, _lens)
                                if _changed and _changed[0] == _lens:
                                    _prot_id, _prot_name = _changed
                                    main_characters_snippet = _rebuild_prot_snippet()
                                    save_protagonist_context(_g3_dr0, _prot_ctx) if _g3_dr0 else None
                                log.info("[G3] 备选稿已提升为本章最终成文并切镜头 → %s（%s）", _prot_name, _prot_id)
                            else:
                                log.info("[G3] 备选稿提升失败或无此稿。")
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
