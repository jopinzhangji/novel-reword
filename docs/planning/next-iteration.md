# 迭代清单（与 Cursor / DevAgent 协同使用）

按 [TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md) §10 与 [guides/cursor-and-devagent-workflow.md](../guides/cursor-and-devagent-workflow.md) 使用；文档分层与 SDD 流程见 [README.md](../README.md)、[framework/SPEC_SDD.md](../framework/SPEC_SDD.md)。完成一项可打勾并注明日期；新建议可追加在“待办”中。

### 当前焦点（与 [WORKLOG.md](../../WORKLOG.md) 速览同步）

**方向**：**多视角内部独立演进 ⊕ 单一主角导出** + **用户可调**（一切增强默认关、`config` 可开可关；导出镜头由用户从关键角色中选一）。下列 **G1–G3** 为全仓梳理（2026-08-31）后的方向对齐主轴；已收敛的旧主线（大纲 MVP-2、成长 MVP、三层记忆、U-6、主角名注入）均 ✅，见下「承接主线」。

1. **G1 屏外线 / 并列主线（大纲 Phase 3，最对齐空白）**：当前每角色只在**在场**事件上成长（`apply_growth_transition_for_turn` 仅遍历 `present_character_ids`，orchestrator 写回侧）；**未入场角色的独立生活尚无真实载体**。**SDD（文档闸 ✅）**：[design/parallel-thread-bridging.md](../design/parallel-thread-bridging.md)（SL∈**SPEC_SDD D10**）——屏外记忆类型（`off_screen`/`parallel_thread`）、触发模型（默认按需/按标签，批处理可选）、桥接摘要注入、屏外成长复用 `GrowthGuard`。**编码状态**：**G1a 数据与演进 ✅**（2026-08-31：`storage` 增 `threads` 桶 + `append_off_screen_refinement`/`get_recent_off_screen`；`memory_layers.build_layer_entry` 增 `thread` 字段与 `THREAD_OFF_SCREEN`/`THREAD_PARALLEL` 常量；`file_sync` 增 `off_screen_threads_yaml_path`/`load_off_screen_threads`/`append_off_screen_thread`；`character_growth` 增 `apply_off_screen_transitions`（批回放进成长 + GrowthGuard + mind 写入 emotions，不经过主书事件簿）；9 条单测，全量 **338 通过 + 1 跳过**）。**编码状态**：**G1b 桥接注入 ✅**（同日：新增 `src/retrieval/bridging.py`（`format_bridging_snippet` + `build_bridging_snippet_from_storage`，默认关、`bridge_ids` 明示）；`TurnContext` 增 `bridging_snippet` 字段并贯通两个 build 函数；`build_turn_body_prompt`/`generate_turn_body` 增 `bridging_snippet` 参数并渲染 `【桥接摘要（<name> 屏外结果）】` 块（写作前分析后、主要角色前，§5.2）；`run_novel_with_author` 回环内按 `runtime.parallel_threads.enabled`（默认 false）+ `bridge_ids` 门控从 storage 组装并传入，已在场角色跳过；9 条单测，全量 **347 通过 + 1 跳过**）。**编码状态**：**G1c 批处理 ✅**（同日：`file_sync` 增 `write_off_screen_threads` 整表写回（append 共用）；`character_growth` 增 `apply_off_screen_batch`（取未消费条目一次性回放进成长，跨条目平衡批内保持，随后标 `consumed=true` 写回 → 幂等空转；`max_entries` 批次上限）+ `scan_off_screen_batch_for_all`（按 `trigger=batch` 每 `batch_turns` 扫各角色，无新戏自动空转）；`run_novel_with_author` 按 `parallel_threads.enabled && trigger==batch` 每 `batch_turns` 触发；4 条单测，全量 **351 通过 + 1 跳过**）。**下一步编码**：**G2 演进层 ↔ 叙事策略层耦闸**。验收：**主书仍主角轴**；副线不因缺席而停滞；桥接摘要来源可追溯。蓝图见 [outline-and-beats.md §2.2/§2.3](../design/outline-and-beats.md)（Phase 3）。
2. **G2 演进层 ↔ 叙事策略层耦闸**：演进（成长/关系/信息视野）跑在编排器**写回**内（`apply_event_and_state_write`/`apply_memory_write`），策略/节奏（PacingContract/Critic/Harness）跑在 `turn_planning` 内——共享 `runtime_config` 但**互不调用**。让**成长状态喂给节奏与审阅**（在场角色演进影响 `pace_mode`/Critic 输入），并让**节拍 `tags` 真正影响成长**（现仅作弱提示）。**SDD**：[design/evolution-pacing-coupling.md](../design/evolution-pacing-coupling.md)（SL∈**SPEC_SDD D11**）。**编码 ✅**（同日：新 `author_harness/evolution_pacing.py`（`GrowthStandings`+`load_growth_standings`+`format_standings_hint`）；`resolve_pacing_contract` 增 `growth_standings` + `infer_growth_window`/`override_contract_for_growth`（兑现边缘→契约向兑现偏置）；`evaluate_body_against_pacing` 悬置回响判据；`match_rules_for_event`/`apply_growth_transition_for_turn`/`apply_event_and_state_write` 透传 `beat_tags` 补足命中；`run_novel` 按 `evolution_pacing` 门控前馈/反馈；可观测走日志；8 条单测，全量 **359 通过 + 1 跳过**）。验收：两层在同一回合互相可影响且全程可观测。
3. **G3 用户可调收敛 + 运行时主角切换**：**两层二分**——演进层关键多角色各自独立演进（成长/记忆/视野/关系边，与镜头无关）；导出层**运行时镜头 = 最终选定的小说内容（正篇成文）**，作者可切换查看。能力开关现散落于 `runtime_config` 深层 `.get(..., False)`，缺统一「能力开关」外观面；把 D9 工作台 `/system`（**W3 可写**、**W4 正篇**）作为作者侧可调出口，并把「单一主角导出」从**仅配置期**（`protagonist_id`/`is_protagonist`，`protagonist.py` 保留）扩展到**运行时可重选**（按章/弧重选导出镜头，**前向**、不回写历史章节，演进不受影响）。**SDD（文档闸 ✅，2026-08-31）**：[design/user-adjustable-and-runtime-lens.md](../design/user-adjustable-and-runtime-lens.md)（SL∈**SPEC_SDD D12**）——统一「能力外观面」`runtime.features` + `CapabilityFlags`/`resolve_features`（旧深层位置回退 WARN）、per-novel `config/features.yaml` 覆盖；运行时镜头 `ProtagonistContext`/`switch_protagonist`/`effective_protagonist`（持久化 `state/protagonist_runtime.yaml`）；CLI 作者「镜头/开关」菜单 + D9 `/system`（W3）同契约映射。**编码 ✅ 一次 MVP**（同日：`capabilities.py`（外观面+嵌套位置回退 WARN+features.yaml）；`protagonist_switch.py`（`ProtagonistContext`/`switch_protagonist`/`effective_protagonist`/`format_lens_snippet`，持久化续读）；`alt_draft.py`（候选备选稿写/列/提升，提升替稿+切镜头）；run_novel 迁移 G1/G2 门闩到 `CapabilityFlags` + 作者「镜头/开关/备选稿」菜单（默认关零打扰）；16 条单测，全量 **375 通过 + 1 跳过**）。验收：作者不改配置文件即可开关能力/换导出镜头/生成&提升备选稿，操作均显式；演进层多角色独立、镜头只管谁进入正篇；D9 W3 落地即复用本表面契约。
4. **承接主线（全部 ✅，续接为主）**：大纲 **MVP-2**（progress 写回 + 作者在环节拍推进）、**成长状态机 MVP**（1a 信息视野 + 语义边 + 骨架、**1b** 五维迁移、**2 GrowthGuard**）、**三层记忆分层**（L1/L2/L3，`memory_layers` 默认关）、**U-6 回合内二次反应链**（`react_chain` 默认关）、**主角姓名一致性注入**（`format_main_characters_snippet`）——全量 **329 通过 + 1 跳过（live）**。
5. **并行**：任务 E（初稿→终态书名 E2E）、小说级路径收口、`run_novel_with_author` LLM 连续超时降级。
6. **上下文压缩（D8）**：文档 ✅；编码 **CC-b ✅**（CompressionContract + 软原型生成器，2026-08-31）；**CC-c～** 见待办。
7. **智能体基础方案 I 系列**：I1–I5 ✅；下一步 **I6**（A/B 与回滚）。
8. **小说作者在环工作台（D9）**：**W0 ✅**；编码 **W1 阅览 → W2 壳+系统设置只读 → W3 设定交互+`/system` 可写 → W4 正篇交互**。**G4 Novel-Data 工作台（SDD 文档闸 ✅，D13）** 承接：多小说进度 ⇄ 六类数据图谱（关系/成长/视野/记忆/屏外/节拍，均走已建的确定性模块）⇄ 作者控制台（复用 G3 能力/镜头/备选稿 + D9 Session）。**编码**：**G4a 后端确定性服务层 ✅**（2026-08-31：`src/workbench/` 纯 Python、无 LLM 无 Web 依赖——`novels.py`（多小说进度卡）、`graph.py`（全量/ego 心图/单对+change_log）、`characters.py`（五维成长/信息视野/L1 记忆/屏外线）、`outline.py`（大纲+节拍指针+missing_ref）、`console.py`（G3 能力/镜头/备选稿读写口，全走白名单）；G4b FastAPI 对其薄包装；20 条单测，全量 **395 通过 + 1 跳过**）；**G4b Web 后端 + 静态工作台 ✅**（同日：`web/api/app.py` FastAPI 工厂 `create_app(project_root)` 挂 `/api` 五 router 对 `src/workbench/` 薄包装 + `web/static/index.html` 无构建静态仪表盘——多小说进度卡 + 单小说关系谱/人物/节拍/作者控制台（能力开关 PATCH、镜头 PUT、备选稿写/提升），浏览器直读 `/api/*` JSON；10 条 TestClient 单测（fastapi 缺失自动跳过，核心 pytest 不受影响），全量 **405 通过 + 1 跳过**）；**G4c 作者控制台（Session 作者在环 + 互斥）✅**（2026-08-31：`src/author_harness/workbench_ingress.py`《`WebInputAdapter` 阻塞式 pending_prompt→reply 桥 + `LogOnlyAuthorIngress` 仅日志不读 stdin》+ `web/api/session_runner.py`《`WorkbenchSession` 后台线程跑 `run_novel_with_author.main(input_fn=adapter.read)`、`SessionRegistry` data_root 一地对一新会话锁》+ `web/api/routers/session.py`（POST /session 建会话 ∓ GET /session/{key} pending 轮询 ∓ POST reply 喂答案 ∓ abort ∓ DELETE ∓ 已活跃 data_root 建会 409）；互斥门 `author_workbench.enabled`（默认 false）落 `config/novel_writing.yaml`，CLI 直跑且 enabled=true 时终端不读 stdin、仅日志，作者交互只在 `web/api` Session Runner/前端；11 条新单测（ingress 纯测 + Session TestClient 端到端），全量 **416 通过 + 1 跳过**）；**G4c+/system 系统设置（GG5）✅**（同日：`src/workbench/system.py`（`system_status` 读 effective LLM/工作台/联网 + `patch_system` 白名单写 per-novel `config/runtime.yaml` 合并保留既有键）+ `web/api/routers/system.py`（GET/PATCH `/api/system`）+ 静态面板「系统」分区；LLM 只读展示、工作台互斥 + `internet_search.*` 可写；改后下一会话生效）；见 [novel-data-workbench.md](../design/novel-data-workbench.md)。

---

## 进行中

- **作者在环统一交互（深化）**：§13 **M1–M6 基础设施已完成**；**Harness R0–R8 ✅**；**2026-05-01** 设定讨论链深化：**检索压缩 profile** + **Assembler 分层 layout** + 讨论超时重试 + I5 联网门闩（见 [author-interaction §9.4](../design/author-interaction.md)）。后续：**D8 CC-b～**、大纲 **MVP-2**、任务 E 等（文首「当前焦点」）。
- **小说作者在环工作台（D9）**：**W0 ✅**；定位 **阅览 + 作者在环交互**（同终端 `read_line` 模型）。编码：**W1** Read API → **W2** UI 壳 + 交互区 → **W3** 设定讨论 → **W4** 章节回合审阅；见 [novel-reader-ui.md §11](../design/novel-reader-ui.md)。
- **设定研究 Agent 优化与设定文件重新设计**：迭代完成整体设定；不同设定配置与内容文件需重新设计承载内容与配置（具体方案待细化）。
- **产品级多智能体（文档 SSOT）**：[design/novel-assistant-pm-agent-model.md](../design/novel-assistant-pm-agent-model.md)（**D7**）；PM 多阶段人格、小说管家按需加载、跨书**匿名偏好**、全局 **Tools**（记忆/知识库/联网）、**DevAgent** 向记录者/观察者演进、联网 **Playwright** 备忘（暂不实现）。**落地排期**见下方 **「产品级路线」**，与 Harness **并行**、**不替代** R7 编码顺序。

---

## 产品级路线：PM / 全局 Tools / DevAgent / 跨书偏好

**SSOT**：[design/novel-assistant-pm-agent-model.md](../design/novel-assistant-pm-agent-model.md)（登记表 **SPEC_SDD D7**）。与 [author-agent-harness.md](../design/author-agent-harness.md)（Harness 工程切片）**互补**：前者定**产品叙事与能力边界**，后者定**作者在环入口与实现步骤**。

| 代号 | 内容 | 与代码关系 | 状态 |
|------|------|------------|------|
| **P0** | 概念共识：PM 可换人格且保持意图连续；小说管家能力**按需加载**（非独立常驻 Agent）；跨书记忆**默认仅匿名偏好**；Tools 共用；DevAgent 弱化编码主叙事 | 文档 | ✅ |
| **P1** | **匿名跨书偏好**：存储键、TTL、用户清除路径；与 `author_interaction` 或独立配置衔接 | 实现 | 待立项 |
| **P2** | **全局 Tool 注册表**扩展：在现有 `retrieval_registry` / Harness 侧统一登记**记忆搜索、知识库、联网**等；各 Agent 按策略与预算调用 | 实现 | 待立项；可部分吸收 **R7c** 审阅检索经验 |
| **P3** | **DevAgent** 演进为工作**记录者/观察者**（进度、失败、任务包、规约偏差）；修订 [guides/cursor-and-devagent-workflow.md](../guides/cursor-and-devagent-workflow.md) 与 `dev_agent/` 行为 | 文档 + 代码 | 待立项 |
| **P4** | **联网 Tool**：可选技术路线 **Playwright** 等**受控浏览器**；沙箱/超时/配额；**当前仓库不实现** | 文档备忘 | 冻结 |
| **P5** | **策略自我迭代**：`PolicyStore/PolicyAssembler/Critic/PolicyUpdater` 文档先行，先建议模式后自动生效 | 文档 + 实现 | 规划中 |

**排期原则**：**Harness R7**、**大纲 MVP-1b/2** 仍为近期**工程主线**；**P1–P5** 按需插入。**W 系列（D9）**：**W3–W4 作者在环交互** 为工作台核心，与 MVP-2 可并行；**W5–W6** 为演进视图与增强。

### 小说作者在环工作台：W0–W6（与 novel-reader-ui §11 一致）

**SSOT**：[design/novel-reader-ui.md](../design/novel-reader-ui.md)（**D9**）。Web 与 CLI **平行入口**；`WebInputAdapter` 替换 `read_line`；**单 PR 不跨 W 阶段**。

| 代号 | 交付物 | 依赖 | 状态 |
|------|--------|------|------|
| **W0** | SDD + 登记 + 排期（含作者在环交互定位） | 无 | ✅ 2026-06-14 |
| **W1** | 阅览 Read API（§8.2）+ 单测 | W0 | 待立项 |
| **W2** | React 阅览四页 + **AuthorInteractionPanel** 壳 + **`/system` 系统设置（只读）** | W1 | 待立项 |
| **W3** | Session API + `WebInputAdapter` + **`author_workbench.enabled`** + CLI `LogOnlyAuthorIngress` + **`/system` 可写** | W2、D6 R5 | 待立项 |
| **W4** | **章节工作台**：单回合 plan→审阅→写回（`review_turn_result`） | W3、Harness | 待立项 |
| **W5** | 角色演进 + 章聚合 timeline API | W2、MVP-2 可选 | 待立项 |
| **W6** | progress PATCH、流式 LLM、设定 md 编辑 | MVP-2 | 远期 |

---

### I 系列：智能体基础增强（动态策略 + 自我迭代 + 联网知识）

| 代号 | 目标 | 主要波及模块 | 交付边界 |
|------|------|--------------|----------|
| **I0** | 文档闸与方案确认 | `specs/author-in-loop-spec`、`design/author-agent-harness`、本文件、`WORKLOG` | 文档可评审、无代码 |
| **I1** | 规则存储模型（PolicyStore） | `src/author_harness/`、`config/novel_writing.yaml`（策略区） | 可加载与版本化，不改现有行为 |
| **I2** | 动态规则组装（PolicyAssembler + Pacing Contract） | `prompt_assembler`、设定/审阅 ingress、正文 prompt 组装 | 至少 1 条设定链 + 1 条审阅链接入；正文可读取节奏约束 |
| **I3** | 质量评估器（Critic） | `author_harness`、日志与可观测字段 | **✅ 已完成（最小实现）**：规则评分 + `pace_deviation`/`subplot_reveal_deviation` 日志接入 |
| **I4** | 候选规则补丁（PolicyUpdater） | `author_harness`、策略存储 | **✅ 已完成（最小实现）**：`I4a` candidate patch + `I4b` Gate 校验；建议模式不自动生效 |
| **I5** | 受控联网 Tool（Playwright+Bing；按需 `internet_search_*`） | `classify_intent`、`retrieve_for_intent`、`playwright_search` | **✅ 最小实现**：分类门闩 + `internet_query` 按 genre/theme 收窄 + Playwright 摘录；`require_classifier_signal` 可关 |
| **I6** | 策略收益评估与回滚 | `author_harness`、可观测、A/B 评估脚本 | 可回滚，不破坏作者在环门闩 |

---

## Agent Harness 与作者在环：落地步骤 ↔ Spec / SDD 对照

下列步骤与 [design/author-agent-harness.md](../design/author-agent-harness.md) 迁移切片一致，并标明**每一步以哪份规约/设计为准**。实现前优先读 **Spec**，再读 **SDD**。

| 步骤 | 交付物 / 范围 | **Spec（规约）** | **SDD（设计）** | 验收要点 |
|------|----------------|------------------|-----------------|----------|
| **S0** | 文档与索引闭环 | [specs/author-in-loop-spec.md](../specs/author-in-loop-spec.md) §1 分工；[DESIGN.md](../../DESIGN.md) §6.7；[TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md) §6.0 | [SPEC_SDD.md](../framework/SPEC_SDD.md) 登记表 **S2、D6**；[author-agent-harness.md](../design/author-agent-harness.md) §8 | 登记表、根目录与 `docs/` 互链完整；冲突处理规则明确 |
| **H1** | 上下文单一组装点（PromptAssembler 或等价） | [author-in-loop-spec.md](../specs/author-in-loop-spec.md) §3.2 | [author-agent-harness.md](../design/author-agent-harness.md) §4.1 PromptAssembler、§6 表 H1 | 设定主菜单路径下游 LLM **仅经**组装点注入片段；与当前行为等价或可测回归 |
| **H2** | 设定 **`c` 子流程**每轮：分类 → 检索 → 注入 `discuss_freely` / `agent.run` | [author-in-loop-spec.md](../specs/author-in-loop-spec.md) §2.3、§3.1 | [author-agent-harness.md](../design/author-agent-harness.md) §4.2 `DESIGN_FREETEXT`、§6 H2；[author-interaction.md](../design/author-interaction.md) §11 | 作者长句指涉已落盘内容时，测试可断言 prompt/日志含检索来源（如 `setting_research`、turns、memory 之一） |
| **H3** | 正篇 **MAIN_WRITING** 审阅走同一 Harness | [author-in-loop-spec.md](../specs/author-in-loop-spec.md) §2.1、§2.4 | [author-agent-harness.md](../design/author-agent-harness.md) §4.2 `MAIN_WRITING`；[memory-storage-and-retrieval.md](../design/memory-storage-and-retrieval.md) | 审阅路径意图+工具可配置；与 §6.2 两阶段审阅不冲突 |
| **H4** | 可观测与单测 | [author-in-loop-spec.md](../specs/author-in-loop-spec.md) §2.4 | [author-agent-harness.md](../design/author-agent-harness.md) §3 原则 4 | 字段约定写入 SDD 或 TECH；`pytest` 覆盖「分类 → 工具列表 → 片段含预期源」 |
| **C1**（可选） | 主动协创 / 联想强度与开关 | [DESIGN.md](../../DESIGN.md) §6.7；[author-in-loop-spec.md](../specs/author-in-loop-spec.md) §3.3 | [author-agent-harness.md](../design/author-agent-harness.md) §1.1、§7 | 默认不突破确认门禁；作者可关闭 |
| **F1**（远期单独立项） | **续写潜力评估**：综合设定/正文/对话/落盘材料，估计**可自动续写的字数或章节上限**及瓶颈（现阶段不实现，见 Spec §5、Harness §7.1） | [author-in-loop-spec.md](../specs/author-in-loop-spec.md) §5；[DESIGN.md](../../DESIGN.md) §6.7 | [author-agent-harness.md](../design/author-agent-harness.md) §7.1 扩展为可交付 SDD；依赖 H1–H4 检索与上下文质量 | 输出须区间化+缺口清单；**不等于**默认自动写满；防模型过度自信 |
| **M\***（远期单独立项） | **执行层**超长篇全自动流水线（与「评估」区分） | **若立项须先修订** §4.1 与 DESIGN §6.7 | **新建** SDD 草案（如 `mega-novel-pipeline.md`） | 与默认「百万字无审阅不承诺」显式关系；成本与质量闸门；可选与 **F1** 评估联动 |

### Harness 编码切片 R0–R8（与 author-agent-harness §6.1 一致）

**每轮迭代先做 R0**；实现阶段按表顺序推进，**单 PR 不跨多个 R**（除非实验分支）。详见 [design/author-agent-harness.md](../design/author-agent-harness.md) §6.1。

| R | 交付物 | 对应 H | 备注 |
|---|--------|--------|------|
| **R0** | 文档闸：S2 / D6 / D1 对齐；方案确认 | 闸门 | 与上表 **S0** 可同轮完成 |
| **R1** | 包空壳 + import 单测 | H1 前置 | ✅ `src/author_harness/`、`test_author_harness_package.py` |
| **R2** | PromptAssembler 纯函数 + 单测 | H1 | ✅ `assemble_retrieval_prompt_block` |
| **R3** | 设定主菜单经 Assembler | H1 | ✅ `design_phase` → `assemble_retrieval_prompt_block`；回归 `test_design_phase` |
| **R4** | Router：`retrieval_query` 生效 + 注册表骨架 | H2 前置 | ✅ `retrieval_registry` + 加权预算 + 单测 |
| **R5** | `c` 子流程：分类→检索→组装→讨论/Agent | H2 | ✅ `_run_freestyle_discussion` + `discuss_freely(assembled_context)`；`DESIGN_DISCUSSION` 分类 |
| **R6** | AuthorHarness.handle 薄层 + 委托 | H2 收口 | ✅ `apply_design_main_menu_ingress`；`AuthorHarness`；`author_loop` 懒加载 `run_design_phase` |
| **R7** | MAIN_WRITING 审阅同一 Harness | H3 | ✅ **R7a–R7e** 见 [author-agent-harness.md §6.3](../design/author-agent-harness.md) |
| **R8** | 可观测 + pytest 链 | H4 | ✅ `cli` 阶段一/二 **`[作者在环] phase=...`**；单测检索源 + 组装块关键字 |

#### R7 子步（与 author-agent-harness §6.3 一致）

| 子步 | 交付物 | 状态 |
|------|--------|------|
| **R7a** | S2 §3.4、D6 §6.3、本子表、WORKLOG | ✅ 文档闸（本轮） |
| **R7b** | 正篇审阅 phase + 分类，与 `understand_author_review_intent` 对拍或迁移说明 | ✅ `phase=MAIN_WRITING_REVIEW`；`classify_intent` + `main_review_intent_to_cli_action`；`understand_author_review_intent` 委托单源 |
| **R7c** | `retrieval_registry` + 审阅检索 1～2 工具 | ✅ `INTENT_REVIEW_REVISE`→`scope_recent_events`+`author_interaction_state`；`retrieve_for_intent(..., storage=, scope_id=)` |
| **R7d** | `apply_main_writing_review_ingress` + `review_turn_result` 委托 + `revise_body_by_feedback(assembled_context)` | ✅ 见 `author_harness.apply_main_writing_review_ingress`、`cli.review_turn_result`、`run_novel_with_author` |
| **R7e** | （可选）阶段二轻量可观测 | ✅ `review_memory_plan`：`PHASE_MEMORY_PLAN_REVIEW`、`memory_plan_action` |

---

## 远期完善与优化（近期主线交付后）

**说明**：本节只做**排期占位**；**不**在本文件写实现细则。各条**立项前**按 [SPEC_SDD §2.1](../framework/SPEC_SDD.md) 单开文档闸（新建或修订 **memory-storage-and-retrieval** / **author-agent-harness** / **TECH** 等），再动代码。

### 「检索完整方案」统一定义（每项优化的必备交付）

凡下表标注依赖本定义的条目，立项时须交付并评审通过一份**检索完整方案**（可与该条同一轮文档 PR，**须先于或同步于**检索相关大改代码），至少约定：

1. **范围**：数据源与路径边界（`book/`、渐进式目录与 README、`MemoryStorage` 与落盘双写、`author_classified`、事件簿与正文单一数据源等）。  
2. **链路**：与 Harness 一致的 **分类 → 检索/Tool → 单一组装点 → Handler**；按场景列清覆盖（设定主菜单、讨论、`MAIN_WRITING_REVIEW`、写作前分析、及本条涉及的正文/修订/大纲/成长等）。  
3. **能力矩阵**：**渐进树状导航**（与现有 [memory-storage-and-retrieval.md](../design/memory-storage-and-retrieval.md) 对齐）；**本地关键字/全文检索**；**查询变种/同义扩展**（规则或词典）；**可选本地向量化切块与增量索引**（离线、可配置开关）；与现有 `retrieve_for_intent`、`retrieval_registry` 的挂载方式。  
4. **治理**：单轮字符/token **预算**、超时、空结果 **降级**、只读与隐私边界；**可观测**（phase、intent、工具列表、来源摘要）。  
5. **规约映射**：**author-in-loop-spec** §2.3、§3.4；**memory-storage-and-retrieval.md**；**author-agent-harness**；**产品级路线 P2**（全局 Tool）。  
6. **验收**：单测/集成清单（含「应命中/不应遗漏」及负例回归）。

### 优化条目（推荐顺序；**均需**包含或更新上述「检索完整方案」）

| 顺序 | 代号 | 主题 | 备注（占位，不定技术方案） |
|------|------|------|----------------------------|
| 1 | **U-1** | **检索与 Tool 底座** | **P2** 方向：在统一注册表下叠渐进树路由、本地关键字、变种扩展、可选向量；**检索完整方案**首次成文可作为**总册**，后续条目增量修订。 |
| 2 | **U-2** | **R7/R8 审阅路径** | R7c–R7d 及 R8 可观测稳定后，审阅专用链路与 **U-1** 共用底层能力；**检索完整方案**增 **审阅** 章节。 |
| 3 | **U-3** | **记忆注入路径扩展** | 正文生成、修订、驳回重试等步骤按需注入片段；**检索完整方案**增 **生成/修订** 章节与预算表。 |
| 4 | **U-4** | **大纲 / 成长 / 关系** | 叙事状态相关摘要与检索入口（与 `outline_store`、成长状态机、图谱等衔接）；**检索完整方案**增 **数据源与工具行** ；对齐 [character-growth-state-machine.md](../design/character-growth-state-machine.md) 的 **§4.6 信息视野**——按角色可见性（private/scene_known/public）过滤的事件视图作为检索返回，作为成长 MVP 阶段 1a 的前置约定。 |
| 5 | **U-5** | **设定研究与 DevAgent（P3）** | 设定产出纳入统一检索与索引策略；DevAgent 记录检索失败与缺口；**检索完整方案**增 **自检与运维** 条目。 |
| 6 | **U-6** | **回合内角色交互 / 反应链** | 多视角内部模拟下，关键角色在当前回合内可对彼此言行**二次反应**（先发批 → 定向二次批 → 合并），形成真实对话链而非并行拼接；依赖 **§4.6 信息视野**（各角色只回应其可见部分）。**✅ 已落地**（`react_chain` 开关默认关；peers_snippet 只注入在场他人公开 `dialogue_action`、不泄私有内心）。 |

**与近期主线**：**不替代**当前 **大纲 MVP-1b/2**、任务 E、小说级路径等（**Harness R7 含 R7e/R8** 已 ✅）；**U-*** 在近期里程碑达到可接受质量后**按需**启动；**U-1** 宜作为 **U-2～U-6** 的共用底座（可并行文档预研，**不设代码抢先**）。

---

## 下一步优先（执行版；2026-03-29 与文首「当前焦点」「产品级路线」同步）

**排期 SSOT**：本条与文首 **当前焦点（G1–G3 + W0–W5）**、**产品级路线（P0–P5）** 一致；变更时优先改文首表与本节编号列表，并同步 [`WORKLOG.md`](../../WORKLOG.md) 速览。

**G 系列（2026-08-31 方向对账新增；详见文首「当前焦点」）**：**G1 屏外线/并列主线**（off-screen 演进 + 桥接摘要，大纲 Phase 3）→ **G2 演进层 ↔ 策略层耦闸**（成长/关系/视野 进 Pacing/Critic，节拍 `tags` 实影响成长）→ **G3 用户可调收敛 + 运行时主角切换**（统一「能力开关」 + D9 `/system` 出口）。立项前按 doc-first 单开文档闸。

**大纲三阶段**：见 **[outline-mvp-plan.md](./outline-mvp-plan.md)**（MVP-0 验收口径；MVP-1/1b/2 范围、API 建议、验收清单、SSOT）。

1. ~~**大纲 MVP-1（核心注入）**~~：**已实现**（2026-03-29）— 同上。~~**MVP-1b（单向生成 API）**~~：**已实现** — `outline_store`：`extract_chapter_outline_from_setting`、`outline_dict_from_setting_chapter_outline`、`materialize_outline_from_setting_research`（映射见 [outline-mvp-plan §2](./outline-mvp-plan.md)）；单测 `test_outline_store`。**可选后续**：在设定完成或 CLI 中一键调用并提示作者复核。  
2. **大纲 MVP-2（开发）**：按 `outline-mvp-plan.md` §5 — 阶段一确认后作者在环推进 **`progress.yaml`**（`[大纲进度]` 日志已在 MVP-1 每回合打印）。  
3. 与上并行：**任务 E**（初稿 `draft-*` + `current_novel`：E2E 覆盖初稿→终态书名）、**小说级路径收口**、**成长状态机 MVP**、**`run_novel_with_author` LLM 连续超时降级**（见下方待办明细）。
4. ~~设定门闩与 §13 M3~~：**已实现** — `ensure_current_novel_for_design_phase`；**M3 `classify_intent`**、**M4 `retrieve_for_intent`**、**M5 主流程 `read_line` + 书名确认同会话**、**M6/digest 与 M2 同链**；详见下表与 `WORKLOG.md`「2026-03-29（续）」。
5. ~~基础设定未完成不得结束设定阶段~~：**已实现** — `world.name` 等为空时拦截 y/默认确认，默认走 c；自由讨论与归纳支持 **章节大纲**，提示避免写作课式跑偏；见 `WORKLOG.md`「2026-03-29（再续）」。
6. ~~**Harness 正篇审阅 R7e/R8**~~：**已实现** — **R7e** `review_memory_plan`：`phase=MEMORY_PLAN_REVIEW`、`memory_plan_action`；**R8** 阶段一 Harness 行日志含 `intent_id` / `retrieval_sources` / `retrieval_chars`；`test_apply_main_writing_review_ingress_revise` 断言检索源与组装块；**`apply_main_writing_review_ingress` 于 `review_turn_result` 内懒加载**以打破与 `author_loop` 包初始化的环状 import。见 **R7 子步**、[author-agent-harness §6.3](../design/author-agent-harness.md)。
7. **上下文压缩（D8）**：**文档闸 ✅** — [context-compression-adaptive-layered.md](../design/context-compression-adaptive-layered.md)（**CC-b～d** 编码待办）。**局部预演 ✅**（2026-05-01）：设定讨论 `RETRIEVAL_PROFILE_DESIGN_DISCUSSION` + Assembler `layout=design_discussion`（见 [author-interaction §9.4](../design/author-interaction.md)）；全意图 **CompressionContract** 仍从 **CC-b** 起。
8. **智能体基础增强（I 系列）**：**I1～I5 最小链路已落地**（I5 见 WORKLOG 2026-05-01）；下一步 **I6**（A/B 与回滚）或 **CC-b**，不与大纲主线硬冲突。
9. **小说作者在环工作台（D9）**：**W0 ✅**；**W1–W2** 阅览与 UI 壳 → **W3** 设定讨论交互 → **W4** 章节回合交互（与 CLI 对拍）。

### 作者在环后续（非阻塞、按需排期）

- **产品级路线（P1–P5）**：见上文 **「产品级路线」**；**D7** [novel-assistant-pm-agent-model.md](../design/novel-assistant-pm-agent-model.md)。
- **Agent Harness**：见 [design/author-agent-harness.md](../design/author-agent-harness.md)（Classifier / RetrievalRouter / PromptAssembler / Handler；设定子流程与主循环共用入口）。
- **组装后上下文压缩**：**D8** [context-compression-adaptive-layered.md](../design/context-compression-adaptive-layered.md)（与 `retrieve_for_intent` 硬截断衔接；**U-1** 治理互链）。
- **小说作者在环工作台（D9）**：[novel-reader-ui.md](../design/novel-reader-ui.md)；**W1** Read API；**W2** 交互区壳；**W3–W4** 设定/章节作者在环。
- 将 `design_phase` 写入的 **`session.extra["intent_retrieval"]`** 接到具体生成/讨论 **prompt**（过渡方案；长期以 Harness **PromptAssembler** 为唯一注入点）。
- **`MAIN_WRITING` / `TURN_*`** 的 `classify_intent` 白名单与 `retrieve_for_intent` 映射表扩展。
- **`digest_llm_compress`**：压缩结果 **max token/字符硬上限** + 抽检与提示词迭代。

### 作者在环「统一入口」实现拆解（与专题 §11 / §13 对齐）

下列为 **方案文档已写明的分阶段计划** 在迭代清单中的落点；细节与验收仍以 [design/author-interaction.md](../design/author-interaction.md) 为准。

| 代号 | 内容 | 状态 |
|------|------|------|
| **§11 前置** | `design_only` 下先保证有效 `current_novel` 再进入设定 | ✅ `ensure_current_novel_for_design_phase`，失败则退出 |
| **M1** | `AuthorSession` 雏形 + 统一 `read_line`；至少一处现有模块改用 | ✅ 已实现：`src/author_loop/author_session.py`，`design_phase` / `run_supplement_setting_during_turn` 已改用；单测 `test_author_session.py` |
| **M2** | `author_state` + `last_round_digest` 持久化；规则生成 digest | ✅ `author_interaction_state.yaml`（`author_interaction_state.py`）；`AuthorSession.record_round_digest`；设定阶段/补充设定写入；单测 `test_author_interaction_state.py` |
| **M3** | 入口 `classify_intent` + 合法意图白名单；Dummy 兜底 | ✅ `src/author_loop/classify_intent.py`；设定主菜单经 `design_main_menu_key` 分支；`runtime.author_interaction.intent_classify_llm`；单测 `test_classify_intent.py` |
| **M4** | `retrieve_for_intent` 最小实现（1～2 类意图） | ✅ `retrieve_for_intent.py`：设定类与保存类两路；**讨论 profile** `design_discussion`（YAML 提要 + md 行级压缩）；总长度可配；`design_phase` 写入 `session.extra["intent_retrieval"]` 或 `assembled_context`；单测 `test_retrieve_for_intent.py` |
| **M5** | 吞并 `run_novel_with_author` 主循环中裸 `input()` | ✅ `AuthorSession.for_main_loop`；`main(input_fn=...)`；`design_only` 下 **书名确认** `confirm_title_and_persist(..., input_fn=session.read_line)` 与回合循环 **同一会话**（编排器重载后同步 `runtime_config`）；审阅/补充设定同 `read_line`；单测 `test_author_session` |
| **M6** | LLM 压缩 digest（可选） | ✅ 已实现（与 M2 同链）：`digest_compress_llm.compress_round_digest_fields` ← `AuthorSession.record_round_digest`；`runtime.author_interaction.digest_llm_compress`（默认 true）；Dummy/失败/关闭则**原文**落盘；单测 `test_digest_compress_llm.py`。**可选后续**：token 上限硬约束、压缩质量抽检与提示词迭代 |

---

## 待办（按实现顺序）

- **智能体基础增强（I 系列，文档先行）**：
  - **SSOT**：`docs/design/author-agent-harness.md` §4.3 / §6.2，`docs/specs/author-in-loop-spec.md` §3，`docs/design/novel-assistant-pm-agent-model.md` §4.3。
  - **I1/I2/I3/I4（已完成）**：`PolicyStore` + `PolicyAssembler` + `pacing_contract` + `Critic` + `PolicyUpdater/Gate` 最小链路已落地（见“已完成”与 WORKLOG 2026-04-13）。
  - **I4（已完成）**：`PolicyUpdater` + `Gate` 最小链路已落地，建议模式不自动生效。
  - **I5（已完成，最小实现）**：`internet_search_needed` / `internet_query`；`require_classifier_signal` 门闩；讨论阶段按 genre/theme 收窄；Playwright+Bing 摘录；单测 `test_classify_intent`、`test_retrieve_for_intent`。
  - **I6**：A/B 与回滚策略；必须可证据化追溯「规则变更为何生效」。
- **上下文压缩（D8，组装后；与 `retrieve_for_intent` 硬截断衔接）**：
  - **SSOT**：[design/context-compression-adaptive-layered.md](../design/context-compression-adaptive-layered.md)；登记表 **SPEC_SDD D8**；Harness 互链 [author-agent-harness.md](../design/author-agent-harness.md) §4.1 表后。
  - **CC-a（讨论链预演，✅ 2026-05-01）**：`RETRIEVAL_PROFILE_DESIGN_DISCUSSION` + `format_snippets_design_discussion` + Assembler `layout=design_discussion`；见 [author-interaction §9.4](../design/author-interaction.md)。
  - **CC-b（✅ 2026-08-31）**：`src/author_loop/context_compression.py` `CompressionContract`（task_thread/structure_preservation/layer_roles/sacrifice_order/query_focus/prototype_id）+ 规则式软原型生成器（纯确定性、无 LLM）——原型匹配（design_discussion/design_edit/save_progress/main_review/general 按 phase+intent），自适应修正（长输入抬高「作者原句」层、短输入不触发），**兜底最小安全集**（低置信/fallback → 任务句+作者原句+来源骨架+事实锚点，禁止单段结论）；`to_dict`/`contract_summary` 供 §5 可观测；11 条单测（多意图契约字段合理 + 兜底路径 + 自适应），全量 **427 通过 + 1 跳过**。尚未挂载检索链路（=CC-c）。
  - **CC-c**：PromptAssembler 或组装出口 **门限**（建议 0.75×cap）+ 分块压缩提示；集成测输出仍含分块/来源结构。
  - **CC-d**（可选）：LLMLingua 等第二路压缩；配置开关；默认不改变未触门限行为。
  - **与远期**：**U-1「检索完整方案」** 须吸收或引用 D8 **治理** 子条，避免检索与压缩双源漂移。
- **小说作者在环工作台（D9）**：
  - **SSOT**：[novel-reader-ui.md](../design/novel-reader-ui.md)；**阅览 + Session 作者在环交互**。
  - **W0（✅）**：含 `WebInputAdapter`、`/session` API、设定/章节工作台交互。
  - **W1**：Read API。
  - **W2**：`AuthorInteractionPanel` + 阅览页。
  - **W3**：`run_design_phase` / `discuss_freely` 浏览器内多轮讨论。
  - **W4**：`run_novel_with_author` 单回合 plan/审阅/写回。
  - **W5–W6**：角色时间线、progress、流式。
- **大纲与节拍 + 主角正文轴 + 多线并行（分阶段落地）**：
  - **设计文档**：`docs/design/outline-and-beats.md`
  - **MVP 执行方案（三阶段细化 + SSOT + 验收）**：`docs/planning/outline-mvp-plan.md`
  - **已定原则**：节拍可跨多回合（建议单节拍 &lt;3 回合为软提示）；卷/章/节拍为**指导**不限死死节奏；**正文以主角为主线**，他线仅以**必要摘要**桥接主书；每角色在系统内仍为**完整并列主线**（长期独立记忆），可导出同文番外。
  - **MVP-0**（已实现）：`book/outline/outline.yaml` + 可选 `progress.yaml`；`src/runtime/outline_store.py`（`load_outline_snapshot`、轻量校验、`OutlineSnapshot.log_line()`）；无文件时返回 None；`run_novel_with_author` 在存在 `data_root` 且有大纲文件时 **INFO** 打一行摘要。示例：`docs/examples/outline.yaml`、`docs/examples/outline_progress.yaml`。  
  - **MVP-1 / MVP-2**：以 **[outline-mvp-plan.md](./outline-mvp-plan.md)** 为准（含设定 **`章节大纲`** 与 `outline.yaml` 的 SSOT、可选 MVP-1b 导入、`progress.yaml` 写回策略）。
  - **后续**：屏外记忆类型（`off_screen` / `parallel_thread`）、桥接触发、可选副轨低成本更新、单角色同文导出 CLI。
- **关键角色成长状态机（新设计落地）**：
  - **设计文档**：`docs/design/character-growth-state-machine.md`（已互链 `outline-and-beats.md`）
  - **目标**：对关键角色引入 `power/mind/social/goal/resource` 五维状态，按事件驱动“语义迁移”并落盘，形成可验证成长轨迹。
  - **原则**：默认 `narrative_only`（非游戏题材避免过度数据化）；按题材可切换 `hybrid` / `numeric`。
  - **改造点**：新增 `src/runtime/character_growth.py`、`src/retrieval/growth.py`；关系图谱已有 `src/runtime/relationship_graph.py`、`src/retrieval/relationship.py`（回合写回 `co_presence`、角色 prompt 注入）；在 `apply_event_and_state_write` 后执行成长迁移与关系语义更新（与图谱并存），在角色 prompt 注入成长快照与关系摘要。
  - **下一步（先做）**：`growth_state.yaml` + 语义迁移规则 MVP + `GrowthGuard` 基础；图谱侧进入证据与副线摘要衔接（见大纲文档 §5）。
  - **约束**：实现 `GrowthGuard`（跨级上限、无代价收益禁止、关系变化上限、目标切换频率限制）。
  - **验收**：连续回合无“突变式成长”，迁移日志可审计，单元+集成测试通过。
- **新小说链路 E2E 验收（任务 E）**：
  - **目标**：补集成测试覆盖“空项目首次启动 -> **初稿目录 `draft-*` 与 `current_novel`（provisional）** -> 进入完整设定交互 -> **书名确认与终态化（draft → design_done）** -> 同轮切换小说目录配置”。
  - **验收**：单测 + 集成测试都可稳定通过；关键日志包含 `novel_root`、初稿/终态 slug 与“已切换到当前小说目录”。
- **小说级路径收口**：
  - **目标**：`design_session_persistence`、`file_sync` 及设定文档写入路径全部优先走当前小说目录，消除全局散点写入。
  - **验收**：运行一轮后，全量产物集中在 `data/novels/<slug>/` 下，根 `config/` 仅保留系统配置与当前指针。
- **LLM 请求超时与自动降级策略**：当前已具备 `timeout` 与 `max_retries`；下一步在 `run_novel_with_author` 增加“连续超时 N 次后自动切换到占位输出（或提示切 dummy）”策略，并把触发次数、最近错误写入日志/提示，避免交互长时间无响应。
- **作者归类记忆注入路径扩展（可选）**：当前主要注入 **写作前分析**（`generate_turn_plan_for_turn`）；后续可在 **正文生成**（`generate_turn_body`）、**驳回后修订正文** 等步骤按配置或同一渐进策略注入 `author_classified_memory` 片段，保持与硬约束一致。
- 设定研究 Agent 优化：迭代完成整体设定；设定配置文件与内容文件重新设计承载内容与配置。
- **世界配置为空时引导填写（深化）**：已有 **结束门闩**（须 c/e）与 **初稿前题材收集**；后续可补：**world.yaml 字段清单式校验**（名称/时代/主矛盾等）与主菜单提示文案迭代。
- **DevAgent 演进（与 [novel-assistant-pm-agent-model.md](../design/novel-assistant-pm-agent-model.md) §4.4、**P3** 对齐）**：
  - **方向（新）**：弱化「自动改代码 / 替代开发者」的主叙事；强化**整体工作记录者、观察者**——沉淀进度、失败、建议任务、与规约/测试偏差，**便于作者与人类开发者推进**，**不**抢占作者在环主对话。
  - **保留（可渐进迁移）**：对接 Cursor 等专业工具、以测试为闸门、`dev_agent/output/` 产物等仍可参考；与 **P3** 落地时统一修订 [guides/cursor-and-devagent-workflow.md](../guides/cursor-and-devagent-workflow.md)。
  - **历史方案摘要**：`CodingProvider`、task bundle、patch 不自动应用、`tests/` 回归——可作为 P3 实现子项，而非唯一目标。
- **LLM 调用层可选「联网」「深度思考」与全局 Tools（与 **P2 / P4** 对齐）**：
  - **目标**：设定讨论、剧情推动等环节可拉取外部参考再进 LLM；与 **§4.3 全局 Tools** 一致：联网宜抽象为 **Tool**（注册表 + 预算），**各智能体可调用**，而非仅绑在某一 `generate` 参数上。
  - **实现要点**：① 抽象「生成前预处理」与 **Tool 注册**（见 **P2**）；② `get_llm_provider` / 调用处可组合 Tools；③ 成本、延迟、缓存、配额；④ **受控浏览器 / Playwright** 仅作 **P4** 备忘，**当前不实现**。
- **写作前分析中的“设定深挖决策”两段式迭代（待确认方案后实现）**：
  - **问题**：仅靠提示词要求“只用概要/必要时深挖”，可能不够稳定；需要让模型先“决策是否要深挖哪些设定维度”，再在第二轮中按决策扩大可用设定上下文进行简要深挖。
  - **目标**：把“是否深挖设定”的判断变成可解析的结构化输出（可为空），并据此控制第二轮是否注入更细的设定内容。
  - **约束**：本条在实现前先与作者讨论方案（输入/输出格式、第二轮如何注入上下文、失败/空结果时如何回退），再写代码落地与补测试。
- 可选（低优先级）：将全局 **example_world** / **example_characters** 改为代码内置默认，进一步减少 `config/` 占位文件（需改 `load_world_config` / `load_characters_config`）。
- 可选：设计会话加载与「继续上次设定」增量流程；设定研究/ search_ideas 联网扩展。

---

## 已完成

- [x] **小说作者在环工作台 SDD（D9，W0）**（2026-06-14）：[novel-reader-ui.md](../design/novel-reader-ui.md) — **阅览 + CLI 等价交互**（Session/`WebInputAdapter`、设定与章节工作台）；W0–W6；**SPEC_SDD D9**。
- [x] **设定讨论：检索压缩 + 分层 Assembler + 超时重试 + I5 联网**（2026-05-01）：见 WORKLOG 与 [author-interaction §9.4](../design/author-interaction.md)。
- [x] **I1/I2 最小链路（PolicyStore + PolicyAssembler + Pacing Contract）**（2026-04-13）：`policy_store.py` + `policy_assembler.py`；`turn_planning` 注入节奏约束块；单测 `test_policy_store`、`test_policy_assembler`、`test_turn_planning_pacing` 通过。
- [x] **I3 最小实现（Critic 可观测评分）**（2026-04-13）：新增 `src/author_harness/critic.py`，正文生成后输出 `pace_deviation` / `subplot_reveal_deviation` 与原因日志；单测 `test_critic.py` 通过。
- [x] **I4 最小实现（PolicyUpdater + Gate）**（2026-04-13）：新增 `src/author_harness/policy_updater.py` 与 `src/author_harness/policy_gate.py`；支持 `candidate_patch` 产出、schema/白名单/核心规则保护校验；单测 `test_policy_updater_gate.py` 通过。
- [x] **Harness R7e/R8（阶段二可观测 + 审阅链日志与单测）**（2026-03-29）：`review_memory_plan` / `review_turn_result` 结构化日志；`apply_main_writing_review_ingress` 懒加载；`test_apply_main_writing_review_ingress_revise` 扩展；见 [author-agent-harness.md §6.3](../design/author-agent-harness.md)。
- [x] **大纲 MVP-1b（章节大纲 → outline.yaml API）**（2026-03-29）：`outline_store.materialize_outline_from_setting_research` 等；见 [outline-mvp-plan §4.5](./outline-mvp-plan.md)。
- [x] **上下文压缩 SDD（D8，文档闸）**（2026-03-29）：[design/context-compression-adaptive-layered.md](../design/context-compression-adaptive-layered.md)；登记表 **SPEC_SDD**、**docs/README**、**D6** 互链；编码待 **CC-b～**（见上文待办）。
- [x] **作者在环 Spec / SDD 拆分与 Harness 落地对照表**（2026-04-05）：新增 [specs/author-in-loop-spec.md](../specs/author-in-loop-spec.md)（L1 行为规约）；[DESIGN.md](../../DESIGN.md) §6.7、[TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md) §6.0、`author-agent-harness.md` 文首与 §8、`SPEC_SDD` **S2** 登记；本清单新增「Agent Harness 与作者在环」步骤表（S0–H4、C1、M\*）。
- [x] **docs 文档体系（Spec + SDD）**（2026-03-29）：`docs/README.md` 总索引；`docs/framework/SPEC_SDD.md` 规约分层与开发流程；根目录 README / TECH / `docs/guides/development` / `docs/planning/next-iteration` 互链。
- [x] **大纲 MVP-1 核心注入**（2026-03-29）：节拍/主角进 `build_turn_plan_prompt` / `build_turn_body_prompt`；`build_outline_prompt_snippet`；`[大纲进度]` INFO；`runtime.outline.enabled` / `soft_max_turns_per_beat`；见 `WORKLOG.md`「大纲 MVP-1」。
- [x] **大纲 MVP 三阶段执行方案文档**（2026-03-29）：新增 `docs/planning/outline-mvp-plan.md`（MVP-0 验收、MVP-1/1b/2 范围与代码接入点、与设定 **`章节大纲`** 的 SSOT、`progress.yaml` 写回策略）；`docs/design/outline-and-beats.md` §8 互链；`WORKLOG.md`、本清单已同步。
- [x] **设定阶段门闩 + 讨论聚焦 + 章节大纲入设定**（2026-03-29）：`design_phase` 基础世界未齐时禁止直接结束；`discuss_freely` / 归纳侧强调可归档设定与 **章节大纲**，减少写作前成篇分析；初稿 YAML 与 LLM 合并保留 `章节大纲` 等扩展键；`book/setting` 展示章节列表；`.gitignore` 增加 `config/current_novel.yaml`；见 `WORKLOG.md`「2026-03-29（再续）」。
- [x] **design_only 下作品解析失败时可交互**（2026-03-29）：`novel_bootstrap` 交互绑定/初稿；`run_novel_with_author` 接入；单测 `test_ensure_novel_for_design.py`。
- [x] **新小说初稿目录与全局 runtime 减负**（2026-03-29）：删除仓库内 `config/example_runtime.yaml`，缺失时用 `DEFAULT_RUNTIME_NOVEL`；新小说不再写全局 `example_world`/`example_characters`，改为 `data/novels/draft-*/` 初稿 + `current_novel`（provisional）；书名确认终态化 draft→`design_done`；最小全局 `example_world`/`example_characters` 占位供未绑小说时校验；文档与单测已同步（见 `WORKLOG.md` §2026-03-29）。
- [x] **大纲、章节骨架与多线叙事方案定稿**（2026-03-28）：`docs/design/outline-and-beats.md`（节拍多回合、大纲指导、正文主角轴、桥接摘要、并列主线与同文导出）；`CHARACTER_GROWTH_STATE_MACHINE_DESIGN.md` 增加关联小节；工作日志与本文待办已同步。
- [x] **大纲 MVP-0 加载与日志**（2026-03-28）：`outline_store.py`、示例 YAML、`run_novel_with_author` 启动时 `[大纲]` 日志；单测 `test_outline_store.py`。
- [x] **关系图谱基础（代码 + 示例 + 主流程）**（2026-03）：`graph.yaml` 路径约定、`get_relation` / `get_neighbors` / `get_relation_change_log`、`docs/examples/relationship_graph.yaml`；`apply_event_and_state_write` 后同步 `co_presence`；`CharacterAgent` 注入关系摘要；解析「内心独白：」「言行：」前缀长度修复。
- [x] **新小说启动引导（任务 A）**（2026-02-11）：新增 `src/author_loop/novel_bootstrap.py`；无设定+无正文时自动生成最小 `example_world/example_characters` 骨架，并强制 `setting_research=design_only`，空项目首次启动不再因缺配置中断。
- [x] **设定后书名确认与身份持久化（任务 B）**（2026-02-11）：新增 `src/author_loop/novel_identity.py`；设定后生成书名候选并确认，写入 `meta.yaml` / `index.yaml` / `config/current_novel.yaml`；无 LLM（Dummy）时明确报错。
- [x] **LLM 统一交互重试入口**（2026-02-11）：新增 `src/llm/call.py` `call_with_user_retry`；“是否继续重试”从业务层迁到 LLM 调用统一层，`novel_identity` 已接入。
- [x] **小说级配置优先加载与同轮切换（任务 C + D 部分）**（2026-02-11）：`src/config/__init__.py` 支持从 `current_novel.root/config/{runtime,world,characters}.yaml` 优先加载；命名后主流程重建编排器并切换到小说目录。
- [x] **测试与请求防卡死基础防护**（2026-02-11）：新增 `pytest.ini`（`--timeout=60`）与 `pytest-timeout` 依赖；LLM 配置支持 `framework.llm_options.timeout`、`max_retries`（OpenAI 兼容与文心），并在 `system_config.yaml` 提供默认值（30s / 1 次重试）。
- [x] **作者在环记忆：LLM 归类 + 目录持久化 + 渐进检索 + 启动进展 + 动态分类**（2026-02-11）：`book/memory/author_classified/<id>/entries.md`；**runtime.author_classified_memory**（`include_defaults`、`categories` 扩展或全自定义、`fallback_id`）；启动打印设定摘要（`design_only`）与最近 N 回合（**MIN_AUTOBOOK_RECENT_TURNS**，默认 3）正文摘要/预览；补充要求归类落盘；**generate_turn_plan_for_turn** 注入渐进片段。见 **docs/design/memory-storage-and-retrieval.md**、**config/novel_writing.yaml**（与 **system_config**、可选 **example_runtime** 或内置默认合并加载）。
- [x] **LLM 额度/配额用尽提醒与占位回退**：在 `src/llm/base.py` 增加 `QuotaAwareLLMProvider` 识别“insufficient_quota/配额用尽/余额不足/硬限制”等错误；首次触发打印明确提醒，后续直接抛 `LLMQuotaExhaustedError`；写作前分析/正文生成/正文修订/摘要生成处捕获并回退，避免反复刷失败日志与交互卡住。
- [x] **阶段一驳回后可修改写作前分析并重试正文**：`run_novel_with_author.py` 中当阶段一输入 `n` 驳回后，额外询问是否在本回合内补充“写作前分析要求”→ 修订 plan → 重新生成正文并回到阶段一审阅。
- [x] **单测适配**：更新 `tests/unit/test_llm.py` 以匹配 LLM 适配层包装，并新增“额度用尽触发”覆盖。
- [x] **设定讨论满意后归档与重启不再提示未完成**：满意后列出本轮更新的设定文件、提醒作者查看并确认（y）后再询问是否保存与逻辑校准；本轮回合结束 save_session 时显式写 current_discussion=None；_backfill_current_discussion 仅当 state_snapshot 不含该键时才回填，重启后不再提示「未完成讨论」。
- [x] **写作前分析补充要求后继续追问**：补充要求后呈现修订后写作前分析，并继续追问「可在此补充对本回合正文的要求…」；仅当作者直接回车（不再补充）时才进入「同意按此分析生成本回合正文？」并生成正文；多轮要求合并传入 generate_turn_body。
- [x] **正文展示后自由交流与摘要写入**：阶段一审阅支持作者直接输入修改意见，意图识别（understand_author_review_intent）后按反馈修订正文（revise_body_by_feedback）并再次展示；作者「没问题」时从正文生成摘要（generate_turn_summary_from_body）写入主线事件（summary+body 对应）；审阅提示 CONFIRM_HINT 明确「直接回复 y 或 没问题 表示满意，将写入本回合摘要到主线记忆并进入下一回合」。
- [x] **正文单一数据源与持久化一致**：正文仅存于范围事件（storage）；展示从记忆取（get_turn_body_from_storage）；data_root 时启动从磁盘 load_scope_events_from_disk、写回时 sync_scope_turn，避免多处存正文导致不一致。
- [x] **每回合写作前分析先行与正文生成**：先呈现本回合写作前分析及预计字数，作者同意后再生成本回合小说正文（≤ 可配字数）；TurnResult.body_narrative、turn_planning（generate_turn_plan_for_turn、generate_turn_body）；字数可配置且可临时改；作者可补充本回合正文要求；**作者补充要求后由大模型修订写作前分析**（revise_turn_plan_with_author_requirements），再呈报修订后分析后询问是否生成正文。
- [x] **重启覆盖确认**：设定阶段启动时若检测到已有设定或会话，先询问作者「是否保留现有设定」(y/n)，选 y 则跳过 agent.run() 避免覆盖；design_phase 新增 _has_existing_setting_output、first_iteration 与首次迭代确认逻辑。
- [x] **叙事节奏与写作前分析**：范围/角色 Agent prompt 增加【叙事节奏】画卷徐徐展开、本回合克制推进；增加【写作前分析】七步（场景/角色/受害者与冲突方/其他人员与生物/本段目标/基调风格/分场景或分镜构思），再输出约束与事件摘要或内心独白与言行。
- [x] **写作前分析中的设定概览仅概要**：`build_turn_plan_prompt` 将设定注入限制为截断的基础概览，并要求只有在最近事件/最近剧情/次要角色信息触发时，才简要点出需深挖的设定维度；否则不提前展开完整体系内容。
- [x] **逻辑校准后保留归纳结果**：从讨论子流程（满意→归纳→保存/校准）返回主菜单时不再执行 agent.run()，避免覆盖刚写回的 setting_research_output.yaml；design_phase 增加 skip_next_agent_run 标志，两处从 _run_freestyle_discussion 返回前置 True（2026-03-04）
- [x] **世界配置动态化**：example_world.yaml 支持可空段、brief 由主菜单 p 保存时自动更新、setting_documents 在新增设定方向时动态登记；config 新增 update_world_brief / add_setting_document_to_world_config / is_world_config_empty；design_phase 新增方向同步到 world、p 时更新 brief、world 为空时 DEBUG 提示通过 c 填写（2026-02-11）
- [x] **设定阶段 s/d 合并为 c、集成测试修复**：主菜单 s 与 d 合并为 c 输入想法（一句补充或讨论，可选多轮后归纳）；test_design_phase 改为 c 分支；test_orchestrator 使用 _first_scope_id/_present_characters 从配置动态取 scope 与角色，全量 113 通过
- [x] **17. 记忆与内容目录存储与检索**：新增 src/runtime/file_sync.py（get_data_root、next_turn_index、write_turn_content、sync_scope_turn、sync_character_turn、ensure_memory_root_readmes）；编排器在 runtime.storage.data_root 配置时双写 content/turns、memory/scopes、memory/characters，README 索引；单测 test_file_sync 共 7 个；单元 105 通过
- [x] **16. 设定阶段按方向讨论流程**：实现 DESIGN §6.6。主菜单 d 讨论；作者直接输入想法（可交叉多维度）→ 自由讨论（discuss_freely）→ 作者「满意」后 summarize_and_extract_by_directions 归纳到多方向并写回 YAML；设定维度动态扩展不写死。主菜单 p 保存进度；讨论中输入「保存」可持久化；design_session_persistence 记录全部输出与状态至 config/design_session.yaml，便于后续增量续写。SettingResearchAgent 新增 discuss_freely、summarize_and_extract_by_directions；design_phase 使用 _run_freestyle_discussion、会话事件与 p/保存；单测 test_design_phase_direction_then_confirm；单元通过
- [x] **15. DevAgent search_ideas 充实**：run_search_ideas 支持 setting_research_output_path 读取已有设定研究 YAML，或 theme + runtime_config_path 调用 SettingResearchAgent，从 power_system/level_system 产出 search_ideas/power_system.md、level_system.md 等真实条目；无配置时仍写占位。单测 test_run_search_ideas_from_setting_yaml_produces_real_entries；单元 97 通过
- [x] **14. 设定研究 Agent 充实**：run() 接 LLM（get_llm_provider）、_build_setting_prompt 生成 prompt、解析 YAML 写入 setting_research_output.yaml（power_system/level_system 等）；design_phase 传入 runtime_config；单测 test_run_with_mock_llm_produces_power_and_level_system（patch src.llm.get_llm_provider）；联网检索留作后续扩展
- [x] **13. 角色/范围 Agent 接 LLM**：CharacterAgent/ScopeAgent 在 turn() 中拼 prompt（含检索）、调 get_llm_provider、解析为 CharacterTurnOutput/ScopeTurnOutput；Orchestrator 注入 storage/runtime_config/characters_config/world_config；mock LLM 单测（test_agent_shells）；单元 95 通过
- [x] **关键角色与次要角色列表**：配置仅列关键角色；Storage 次要角色列表（get_secondary_characters/append_secondary_character）；Retrieval format_secondary_characters_snippet；TurnContext.secondary_characters_snippet 注入；文档与配置说明（2026-02-17）
- [x] **开书前设定阶段**：trigger=design_only 时先运行设定研究 Agent 并与作者交互（y/e/s），完善世界模型与设定后再进入正篇；编辑后重载配置与编排器；run_design_phase、load_special_settings_config；test_design_phase（3 个）（2026-02-17）
- [x] **12. LLM 接入**：真实 Provider（OpenAI 兼容、通义 tongyi/qwen 预设、文心 wenxin 直连）；framework.llm 可配；API Key 仅环境变量；方案见 `docs/design/llm-and-agents.md`；全量 90 通过（2026-02-11）
- [x] **11. 设定研究 Agent**：壳实现（SettingResearchAgent.run(theme, genre, reference, output_dir) 占位写 YAML 到 setting_research_output.yaml）；单元测试 test_setting_research（3 个）；全量 84 通过（2026-02-11）
- [x] **10. LLM 与检索**：记忆与事件检索模块（src/retrieval：retrieve_character_memory、format_scope_events_snippet）；LLM 抽象层（src/llm：LLMProvider、DummyLLM、get_llm_provider）；单元测试 test_retrieval、test_llm；全量 81 通过（2026-02-16）
- [x] **9. DevAgent**：自我迭代机制（运行与测试通过才保留、cursor_tasks 强化修复/回滚；搜索与联想扩展点 search_ideas + search_ideas_enabled 配置；单元测试 test_dev_agent_search_ideas），全量 70 通过（2026-02-16）
- [x] **8. 配套测试**：单元/集成测试补充与回归；新增 run_novel_with_author 集成测试（作者全同意一回合），全量 68 通过（2026-02-16）
- [x] **7. 作者在环**：两阶段审阅与确认（CLI：review_turn_result、review_memory_plan；run_one_turn(auto_write=False) + apply_event_and_state_write + apply_memory_write；run_novel_with_author.py）（2026-02-16）
- [x] **6. 冲突裁决**：简单规则合并 scope 与角色输出（resolve_turn_conflict），写回裁决后摘要（2026-02-16）
- [x] **5. 回合循环**：多回合、状态持久化并影响下一回合；run_n_turns、run_novel.py 入口（2026-02-16）
- [x] **4. Orchestrator**：按配置创建 Agent，单回合流程（下发 Context → 并行调用 → 收集），写回事件簿/状态，记忆留作者确认（2026-02-16）
- [x] **3. 单 Agent 壳**：CharacterAgent、ScopeAgent 壳（CharacterTurnOutput、ScopeTurnOutput，固定输出，不接 LLM）（2026-02-16）
- [x] **2. Context**：TurnContext 及构建方式（scope_id, time, place, present_character_ids, last_turn_summary 等；build_turn_context、build_turn_context_from_storage）（2026-02-16）
- [x] **1. 配置与存储**：配置加载（YAML）、enabled_ids 校验、Storage 抽象（内存版、键结构 §7）（2026-02-16）
- [x] 设计文档与技术文档、配置示例、目录与工作日程纪要（2026-02-16）

---

*DevAgent 产出的建议可合并进本清单“待办”；Cursor 处理后可勾选并移到“已完成”。*
