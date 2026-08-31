# 工作日程纪要

每日追加更新，记录当日完成工作、优劣分析及下一步计划。

### 速览：当前状态与下一步（2026-08-31）

| 项 | 说明 |
|----|------|
| **排期 SSOT** | [`docs/planning/next-iteration.md`](./docs/planning/next-iteration.md)（**当前焦点：G1–G3 方向主轴 + W0–W5** + **产品级路线 P0–P5** + Harness **R0–R8** + **CC-b～** + **I6** + 待办）；大纲见 [`outline-mvp-plan.md`](./docs/planning/outline-mvp-plan.md)。 |
| **近期已完成** | **2026-08-31** **工作台面板 #3 迁移日志时间线 ✅（GG-W）**（人物卡内 `growthTimeline` 按 turn 升序展开 `transition_log` 两类条目——成长命中 `{rule,turn,scope_id,reason,deltas}`（维度 label+key±value 徽标）+ guard 审计「钳制/跳过」warn 徽标+guard_reason；纯前端零后端改动，全量 **450 通过 + 1 跳过**））+ **工作台面板 #2 五维成长雷达图 ✅（GG-W）**（`characters.py::radar_vector` 确定性度量 `level=min(1, Σ/6)` 成长深度非绝对特质 + `character_detail.growth_radar` + 前端人物卡内嵌 SVG 五角雷达；2 单测，全量 **450 通过 + 1 跳过**））+ **GG6 远程访问与鉴权 ✅**（`config/web_api.yaml` `server.host/port` 可配监听 + `auth.enabled` Basic Auth 密码登录默认关；`web/api/security.py` 常量时间校验 `verify_credentials` + 全站中间件，`web/api/server.py` `python -m web.api.server` 按配置启动、空口令启动报错不裸奔；D13 §6.5 + §7 GG6 行））+ **G4c+/system 系统设置 ✅（GG5）**（`src/workbench/system.py` `system_status`（effective LLM/工作台/联网）+ `patch_system` 白名单写 per-novel `config/runtime.yaml` 合并保留既有键；`web/api/routers/system.py` GET/PATCH `/api/system`；静态面板「系统」分区；LLM 只读展示、`author_workbench.enabled` + `internet_search.*` 可写、改后下一会话生效）+ **CC-b 编码 ✅（上下文压缩 D8）**（`src/author_loop/context_compression.py`：`CompressionContract` + 规则软原型生成器，纯确定性无 LLM——五类原型 + 自适应修正（长输入抬作者原句 / 短输入不触发）+ 低置信/fallback **最小安全集兜底**；11 条单测，全量 **427 通过 + 1 跳过**）+ **G4 编码三阶段收口（G4a/G4b/G4c）**：**G4c 编码 ✅ 作者控制台（Session 作者在环 + 互斥）**（`workbench_ingress.py` `WebInputAdapter`（阻塞 pending→reply）+ `LogOnlyAuthorIngress`（不读 stdin 仅日志）；`session_runner.py` `WorkbenchSession` 后台线程跑 `run_novel_with_author.main(input_fn=adapter.read)` + `SessionRegistry` data_root 一地对一新会话锁；`routers/session.py` POST/GET/reply/abort/delete + 已活跃 data_root 建会 409；互斥门 `author_workbench.enabled` 落 `config/novel_writing.yaml` 默认 false；**416 通过 + 1 跳过**）、**G4b 编码 ✅ Web 后端 + 静态工作台**（`web/api/app.py` FastAPI 工厂 `/api` 五 router 薄包装 `src/workbench/` + `web/static/index.html` **无构建**静态仪表盘——多小说进度卡 + 单小说关系谱/人物/节拍/作者控制台（能力开关 PATCH、镜头 PUT、备选稿建稿+提升）；fastapi 缺失自动跳过，10 条 TestClient 单测，全量 **405 通过 + 1 跳过**）、**G4a 编码 ✅ 后端确定性服务层**（`src/workbench/`：`novels`/`graph`/`characters`/`outline`/`console` 五模块，纯 Py 无 LLM 无 Web 依赖，G4b FastAPI router 薄包装即可；盘上只持久 L1 事实+屏外线，L2/L3 记忆与平行线为运行期内存态故标 `runtime_only_layers: true`；20 条单测，全量 **395 通过 + 1 跳过**）、**G4 文档闸 · SDD D13**（Novel-Data 工作台：多小说进度 ⇄ 六类数据图谱 ⇄ 作者控制台，承接 D9 壳 + G1/G2/G3 数据与表面，`novel-data-workbench.md`）、**G3 编码 ✅**（能力外观面 `capabilities.py` + 运行时镜头 `protagonist_switch.py` + 候选备选稿 `alt_draft.py`，run_novel 迁移 G1/G2 门闩统一开关 + 作者「镜头/开关/备选稿」菜单；16 条单测，全量 **375 通过 + 1 跳过**）、**G3 文档闸 · SDD D12**（用户可调收敛 + 运行时镜头（候选备选稿档）定稿，`user-adjustable-and-runtime-lens.md`）、**G2 编码 ✅**（成长站姿前馈契约/Critic + 节拍标签补足成长，8 条单测）、以及此前**全仓结构梳理 + G1 屏外线全套（数据/桥接/批处理）+ G2 文档闸**，**G2 文档闸 · SDD D11**（演进层↔叙事策略层耦闸方案定稿，`evolution-pacing-coupling.md`）、**G2 编码 ✅**（成长站姿前馈契约/Critic + 节拍标签补足成长，8 条单测）、**G1 文档闸 · SDD D10**（屏外线/并列主线方案定稿）、**G1a 编码 ✅**（`storage`/`memory_layers`/`file_sync` 增屏外线数据通道 + `character_growth.apply_off_screen_transitions` 批回放演进，9 条单测）、**G1b 桥接注入 ✅**（`bridging.py` + `TurnContext.bridging_snippet` + 正文 prompt 桥接块 + 回环按 `parallel_threads.enabled`/`bridge_ids` 门控注入，9 条单测，全量 **347 通过 + 1 跳过**）、**G1c 屏外批处理 ✅**（`write_off_screen_threads` + `apply_off_screen_batch`/`scan_off_screen_batch_for_all`，`trigger=batch` 幂等演进，4 条单测，全量 **351 通过 + 1 跳过**）、**G2 编码后全量 359 通过 + 1 跳过**；**2026-08-30** **真实 LLM 联调验证**（火山方舟 deepseek-v4-pro 下作者在环一回合全链路 E2E 通过）、**主角姓名一致性修复**与**角色独立演进：设计文档对账**、**阶段 1a/1b/2 编码 + 成长状态注入**（信息视野 + 语义关系边 + 五维迁移 + GrowthGuard + **U-6 回合内二次反应链**，全量 300 通过）、**三层记忆分层落库**（L1/L2/L3 写回+检索可开关）、**大纲 MVP-2**（progress.yaml 写回 + 作者在环节拍推进，全量 319 通过）；**2026-08-27** **Linux 迁移收口**（全量 251 通过）；**2026-06-14** **D9** **W0 文档闸**；**2026-05-01** 设定讨论链。 |
| **当前优先** | **方向**：**多视角独立演进 ⊕ 单一主角导出** + **用户可调**（增强默认关、可开可关）。**G 系列**：**G1 屏外线/并列主线 ✅**（off-screen 演进 + 桥接摘要 + 批处理）→ **G2 演进层 ↔ 策略层耦闸 ✅**（成长/关系/视野进 PacingContract/Critic，节拍 tags 实影响成长）→ **G3 用户可调收敛 + 运行时主角切换 ✅**（能力开关/镜头/备选稿）→ **G4 Novel-Data 工作台 ✅**（G4a 确定性服务层 + G4b Web 后端/静态仪表盘 + G4c Session 作者在环/互斥）。**下一步**：React/Vite 换壳（W 系列）、任务 E、D9 W 系列、**CC-c**（组装后门限+分块压缩）、I6。**工作台面板**（已列入 next-iteration 待办 `工作台面板补全`）：`/system` ✅ → #2 五维雷达 ✅ → #3 迁移日志时间线 ✅ → #4 L1记忆·屏外线时间线 / #5 跨卡联动。**联网**：`/system` 可配 `internet_search`（enabled/provider/max_chars/trust_level）；`require_classifier_signal` **保持 I5 默认=true**（重排不暴露，联网勿须作者明确要求才抓）。**续工程**：**D9 W1→W4**、**CC-b**、**I6**、任务 E、同文导出。 |
| **文档入口** | [`docs/README.md`](./docs/README.md)；[`SPEC_SDD.md`](./docs/framework/SPEC_SDD.md)（**D9**）；作者在环 [`author-in-loop-spec.md`](./docs/specs/author-in-loop-spec.md)；阅读 UI [`novel-reader-ui.md`](./docs/design/novel-reader-ui.md)。 |

---

## 2026-08-31

### 全仓结构梳理 +「多视角独立演进 ⊕ 用户可调」方向对账（分析 / 文档）

- **背景**：成长状态机（1a/1b/2）、三层记忆、信息视野、U-6 反应链、大纲 MVP-2 相继落地后，用三个并行子系统映射 + 逐模块阅读对全仓做一次结构化梳理，把每项能力对齐既定大方向——**多视角内部独立演进 ⊕ 单一主角导出**，并确认**用户可调**是被一致遵守的默认（增强一律默认关、`config` 可开可关；导出镜头由用户选择）。
- **三层子系统映射（落地文件）**：
  1. **核心编排 + LLM + 数据**：`src/orchestrator`（并行回合、双阶段写回、冲突裁决）、`src/runtime/{storage,file_sync,relationship_graph}`、`src/context`、`src/llm`（重试/超时/配额）、`src/config`（小说级合并加载）。
  2. **独立演进 + Harness**：`src/runtime/{character_growth,memory_layers,outline_store,protagonist}`、`src/retrieval/info_view`、`src/author_harness`（I1–I5 策略链 + Facing/Critic）。
  3. **作者在环体验**：`run_novel_with_author`、`src/author_loop`、`src/agents/setting_research`、`src/agents/dev`（设定讨论、回合 plan→审阅→写回、大纲推进、DevAgent）。
- **逐功能点对账结论**：多数能力已按「多视角独立演进」到位——每个关键角色独立记忆/信息视野/五维成长/关系边，写回仅在**在场**角色上累积；「用户可调」靠 `react_chain`/`memory_layers`/`outline.enabled` 等开关保持默认不破、全量 329 通过。
- **识别出的三大优化主轴（新 G 系列，见 next-iteration）**：
  - **G1 屏外线 / 并列主线（最对齐空白）**：角色只在**在场**事件上成长（`apply_growth_transition_for_turn` 仅遍历 `present_character_ids`）；未入场的独立生活（`off_screen`/`parallel_thread` 记忆、屏外时间线、桥接摘要）尚无真实载体——对应大纲 **Phase 3**。
  - **G2 演进层 ↔ 策略层耦闸**：演进（成长/关系/视野）在编排器写回内，策略/节奏（PacingContract/Critic/Harness）在 `turn_planning` 内——共享 `runtime_config` 但不互调；成长应先喂给节奏/审阅，节拍 `tags` 才真正影响成长。
  - **G3 用户可调收敛**：能力开关散在 `runtime_config` 深层 `.get(..., False)`，缺统一「能力开关」外观面；D9 `/system`（W3 可写、W4 正篇）与**运行时主角切换**（现仅配置期 `protagonist_id`）是落点。
- **文档落地**：`docs/planning/next-iteration.md` 新增 G 系列当前焦点与下一步优先；`WORKLOG` 速览与本节同步。
- **下一步**：续 **D9 W1–W4**、**CC-b**、**I6**、任务 E；并正式立项 **G1**（屏外演进 + 桥接摘要）。

---

## 2026-08-31（续）

### G1 文档闸（屏外线 / 并列主线，SDD）

- **立项背景**：上一节对账识别出"角色只在在场事件上成长"是「多视角独立演进」最大空白；本节将 [outline-and-beats.md](./docs/design/outline-and-beats.md) **Phase 3** 蓝图落成可执行 **SDD**。
- **新增** [`docs/design/parallel-thread-bridging.md`](./docs/design/parallel-thread-bridging.md)：屏外数据模型（`threads/<id>/off_screen.yaml` + `$thread` 标签，复用 memory_layers 分层）、**触发模型裁决**（§9.2 开放项：默认**按需/按标签**、批处理可选 G1c、不做逐回合全量刷新）、桥接摘要注入（`TurnContext.bridging_snippet` + `build_turn_body_prompt` 块，`bridge_budget_chars` 预算）、屏外成长复用 `GrowthGuard`、`parallel_threads.enabled` 默认关。
- **登记**：`SPEC_SDD` **D10**；`next-iteration` 当前焦点 G1 项挂 SDD 链接与 G1a/G1b/G1c 分阶段。
- **下一步编码**：从 **G1a**（`storage.file_sync.memory_layers` 增 `threads`/`off_screen` + `append_off_screen_refinement` + `apply_off_screen_transition_for_turn`）起步。**（文档闸待作者评审后再动代码）**

---

## 2026-08-31（再续）

### G1a 编码：屏外线数据落盘 + 屏外演进

- **范围**：SDD D10 §8 **G1a**——屏外线数据的进程内存桶、磁盘持久化与成长回放入口；本轮不接入主循环（接桥接注入留 **G1b**）。全程无 LLM、默认不改变既有行为。
- **`src/runtime/storage.py`**：新增 `_char_threads` 桶 + `append_off_screen_refinement` / `get_recent_off_screen(thread, limit)`（筛 `thread`），与主书 `_char_events`（在场事实卡）分离。
- **`src/runtime/memory_layers.py`**：`build_layer_entry` 增 `thread` 字段（非空才写，向后兼容）；新增 `THREAD_OFF_SCREEN`/`THREAD_PARALLEL` 常量。
- **`src/runtime/file_sync.py`**：`off_screen_threads_yaml_path`（`book/characters/<id>/threads/off_screen.yaml`）+ `load_off_screen_threads`（缺省返回 []）+ `append_off_screen_thread`（读旧→追加→写回）；`import yaml`。
- **`src/runtime/character_growth.py`**：新增 `apply_off_screen_transitions(storage, data_root, *, character_id, entries, guard)`——把一批屏外条目**批量回放**进该角色成长状态（复用 `apply_growth_transition_guarded` + `GrowthGuard`），落盘 `growth_state.yaml`、mind 变化写 emotions；**不经过主书 scope 事件簿**；返回 `(fired, guard_audit)`。跨条目平衡得以体现（先损耗后可收益放行、无代价收益被拒）。
- **测试**：新增 `tests/unit/test_off_screen_threads.py` 9 条——thread 字段向后兼容、storage 桶隔离、YAML round-trip、非在场角色屏外演进、growth_state 落盘+回读、GrowthGuard 无代价收益被拒 / 先损耗后收益放行、无命中不变。全量回归 **338 通过 + 1 跳过（live）**（基线 329 + 9）。
- **下一步**：**G1b**（`TurnContext.bridging_snippet` + `build_turn_body_prompt` 桥接块 + 触发/桥接菜单），再 **G1c**（可选批处理）。

## 2026-08-31（再续二）

### G1b 编码：桥接摘要注入（屏外结果带回主书）

- **范围**：SDD D10 §8 **G1b**——当主书下一场景依赖某**非在场**角色屏外结果时，向正文生成注入一段规则截断的短摘要；默认关（`runtime.parallel_threads.enabled=false`），不改变无桥接场景行为。
- **新增 `src/retrieval/bridging.py`**：
  - `format_bridging_snippet(entries, name="", budget_chars=400)`——纯格式化：把该角色最近屏外条目拼成 `【桥接摘要（<name> 屏外结果）】` 块，预算截断；空条目返回空串。
  - `build_bridging_snippet_from_storage(storage, present_character_ids, parallel_threads_cfg, characters_config)`——enabled=false 或未给 `bridge_ids` → 空串；对每个明示 `bridge_ids` 且**非在场**角色取 `storage.get_recent_off_screen` 组装，已在场角色跳过（主书仍主角轴，§5.3）。
- **`src/context/__init__.py`**：`TurnContext` 增 `bridging_snippet: str = ""` 字段，贯通 `build_turn_context` 与 `build_turn_context_from_storage`（默认为空，向后兼容）。
- **`src/author_loop/turn_planning.py`**：`build_turn_body_prompt` / `generate_turn_body` 增 `bridging_snippet=""` 参数；块渲染置于写作前分析之后、主要角色名册之前（§5.2）。
- **`run_novel_with_author.py`**：回环内按 `runtime.parallel_threads.enabled`（默认 false）+ `bridge_ids` 门控，从 `orch.storage` `build_bridging_snippet_from_storage` 组装并传入两处 `generate_turn_body`；缺配置/异常 → 空串，船身不破。
- **测试**：新增 `tests/unit/test_bridging.py` 9 条——`format_bridging_snippet` 空/标签/预算截断；`build_bridging_snippet_from_storage` 默认关、`bridge_ids` 明示、已在场跳过、无条目空串；`TurnContext` 字段往返；`build_turn_body_prompt` 有桥接块/无桥接块。全量回归 **347 通过 + 1 跳过（live）**（基线 338 + 9）。
- **下一步**：**G1c（可选）**（`trigger=batch`：每 `batch_turns` 扫一次各角色 `threads` 累积演进），加载态桥接菜单作者补屏外戏/勾选留后续。

## 2026-08-31（再续三）

### G1c 编码：屏外线批处理（trigger=batch，幂等演进）

- **范围**：SDD D10 §4/§8 **G1c（可选）**——`trigger=batch` 时每 `batch_turns` 扫一次各角色 `threads` 已累积未消费屏外条目，一次性回放进成长状态；**无新戏不空转、幂等**。默认关，不改变既有回合行为。
- **`src/runtime/file_sync.py`**：新增 `write_off_screen_threads(novel_root, character_id, entries)` 整表写回（`append` 与 batch 消费标记共用），refactor 原 `append_off_screen_thread` 委托之。
- **`src/runtime/character_growth.py`**：
  - `apply_off_screen_batch(storage, data_root, *, character_id, guard, max_entries)`——取 `threads` YAML 中无 `consumed` 标记的条目，一次性交 `apply_off_screen_transitions` 回放（**跨条目平衡批内保持**），随后把本轮条目标 `consumed=true` 整表写回 → 再扫即空转（幂等）；`max_entries` 只截断本轮批次，剩余留待下轮；返回 `(fired, guard_audit, consumed)`。
  - `scan_off_screen_batch_for_all(storage, data_root, *, character_ids, guard, max_entries)`——按配置角色扫描入口，无待处理条目自动空转，汇总 `(fired_by_char, guard_audit)`。
- **`run_novel_with_author.py`**：回环前预读一次 `parallel_threads` 配置（桥接/批处理共用）；仅当 `enabled && trigger=="batch"` 且 `(turn+1)%batch_turns==0` 时对 `orch.character_agents.keys()` 跑 `scan_off_screen_batch_for_all`（`GrowthGuard` + `batch_budget_entries` 上限），异常降级 WARN 不影响主书。
- **测试**：新增 `tests/unit/test_off_screen_batch.py` 4 条——无待处理空转；批次触发演进 + 消费标记落盘 + 幂等二扫不重复涨；`max_entries` 上限分成两批消费；扫描入口跳过无内容角色。全量回归 **351 通过 + 1 跳过（live）**（基线 347 + 4）。
- **下一步**：**G2 演进层 ↔ 叙事策略层耦闸**（成长/关系/视野进 PacingContract/Critic，节拍 `tags` 实影响成长）；G1 串（屏外演进 + 桥接 + 批处理）收口。

## 2026-08-31（再续四）

### G2 文档闸 · SDD D11：演进层 ↔ 叙事策略层耦闸（方案定稿）

- **立项**：触发 G1 串收口后接续主轴的第二步（紧接 G1）。按 doc-first 惯例单开文档闸，**编码待作者评审后再动**。
- **文档**：新增 `docs/design/evolution-pacing-coupling.md`；登记 `SPEC_SDD` **D11**；`next-iteration` G2 项挂 SDD 链接并标「文档闸 ✅」。
- **方案要点（默认关，船身不破）**：
  - **前馈 · 成长→节奏**：新 `author_harness/evolution_pacing.py` `GrowthStandings` + `load_growth_standings`（聚合在场角色五维计数与「兑现边缘」`payoff_edge`）；`policy_assembler.resolve_pacing_contract(…, growth_standings)` + `infer_growth_window` + `override_contract_for_growth`（成长到兑现点 → 契约向「兑现」偏置）。
  - **前馈 · 成长→审阅**：`critic.evaluate_body_against_pacing(…, growth_standings)` 增悬置回响判据（`payoff_edge` 非空且正文未承接 → 小幅上调 `subplot_reveal_deviation`）。
  - **反馈 · 节拍→成长**：`character_growth.match_rules_for_event(summary, extra_tags)` + `BEAT_TAG_TO_RULES` 映射补足命中（节拍意图实测影响当回合演进，经 GrowthGuard 复核）；`apply_growth_transition_for_turn(…, beat_tags)` + `apply_event_and_state_write(…, beat_tags)` 透传 `outline_beat.tags`；`TurnContext.growth_hint` 可观测。
- **配置**：`runtime.evolution_pacing.{enabled=false, beat_tags_to_growth=false}`；默认全量回归与 G1 末一致。
- **下一步**：作者评审后按 SDD §7 编码 G2 一次 MVP（承载下一条）。

## 2026-08-31（再续五）

### G2 编码：演进层 ↔ 叙事策略层耦闸（SDD D11 · 一次 MVP）

- **范围**：SDD D11 §6/§7——两层在同一回合互可影响；默认关（`runtime.evolution_pacing.enabled=false`），开启才影响行为。全程无 LLM。
- **前馈 · 成长→节奏**：新增 `src/author_harness/evolution_pacing.py`：`GrowthStandings` + `load_growth_standings`（读在场角色 `growth_state.yaml`，聚合五维计数 + 由 goal-state 里程碑/目标重估/动机转变 ≥1 判定 `payoff_edge` 兑现边缘）+ `format_standings_hint`。`policy_assembler.resolve_pacing_contract` 增 `growth_standings` 可选参 + `infer_growth_window`（有兑现边缘 → 偏置 "兑现"）+ `override_contract_for_growth`（基部契约盖写为兑现口径并追加「勿悬置兑现边缘角色回响」禁止项；基部已兑现则原样）。
- **前馈 · 成长→审阅**：`critic.evaluate_body_against_pacing` 增 `growth_standings` 可选参 + `_with_hanging`——存在兑现边缘角色但正文无揭示词 → 判「悬置回响」，`subplot_reveal_deviation` 上调 +0.15（封顶 1.0）并追加原因。
- **反馈 · 节拍→成长**：`character_growth` 增 `BEAT_TAG_TO_RULES`（`growth:power/social/goal/loss/gain/pivot` → 规则补足）`match_rules_for_event(summary, extra_tags)` 补足命中（未知/无标签忽略，逐字节向后兼容）；`apply_growth_transition_for_turn(…, beat_tags)` 与 `orchestrator.apply_event_and_state_write(…, beat_tags)` 透传；`run_novel` 把 `outline_beat.tags` 按 `evolution_pacing.beat_tags_to_growth` 门控传写回。
- **接线**：`generate_turn_body`/`run_novel` 增 `growth_standings`（回环前预读 `evolution_pacing` 配置；`_evo_enabled` 时加载并 debug 日志 `[G2] 前馈成长站姿`，异常降级 None）；可观测走日志而非新增 `TurnContext.growth_hint`（SDD §6 已注明）。
- **测试**：新增 `tests/unit/test_evolution_pacing.py` 8 条——`load_growth_standings` 兑现边缘/空；契约偏置（有兑现边缘→兑现、空/已兑现→不变、默认 None 逐字节不变）；Critic 悬置回响（上调+0.15 与原因、已揭示不计、None 一致）;`match_rules_for_event` 补足命中/未知标签忽略；`apply_growth_transition_for_turn` beat_tags 实际施加（先损耗后可放行，增益 =1）。全量回归 **359 通过 + 1 跳过（live）**（基线 351 + 8）。
- **下一步**：G 系列三主轴已收口 G1/G2，剩 **G3 用户可调收敛 + 运行时主角切换**（能力开关外观面 + D9 `/system` 可写 + 主角镜头运行时切换）。

---

## 2026-08-31（再续六）

### G3 文档闸 · SDD D12：用户可调收敛 + 运行时主角切换

- **登记**：**SPEC_SDD D12** 挂屏；`docs/design/user-adjustable-and-runtime-lens.md` 定稿；next-iteration G3 项标注「**文档闸 ✅ · 编码 ⏳**」。
- **问题**：(1) 能力开关散落 `runtime_config` 深层 `.get(..., False)`（`setting_research.enabled`、`runtime.parallel_threads.enabled`、`runtime.evolution_pacing.*`、`react_chain`、`internet_search`、`agents.*.enabled_ids`），无统一读法/写口，作者要改能力只能手改 YAML；(2) 导出镜头仅**配置期**解析（`protagonist.py resolve_protagonist_id`，run_novel L99 loop 外定死 `_prot_id/_prot_name`），整本不可换镜头；(3) D9 `/system` 可写（W3）待立项，作者侧可调出口无承载面。
- **两层二分（作者澄清，主文档 §1.1/§4 已显式化）**：**演进层**关键多角色各自独立演进（成长/记忆/视野/关系边，与镜头无关，照常累积）；**导出层**任意时刻只有一条「运行时镜头」= 作者最终选定的小说内容（正篇成文）。镜头是**最终内容的选择器**，不是演进的对象。
- **方案（一次 MVP，作者选定「候选镜头·备选稿」档）**：
  1. **能力外观面** `src/runtime/capabilities.py`：`CapabilityFlags`（全默认关）+ `resolve_features(runtime_config, *, features_override=None)`（规范读 `runtime.features`；缺失回退旧深层位置并一次性 WARN；`features_override` 最后覆盖）+ 序列化 + per-novel `config/features.yaml` 覆盖 `load_features`/`save_features`。
  2. **运行时镜头** `src/runtime/protagonist_switch.py`：`ProtagonistContext`（可变、会话内持有）+ `switch_protagonist`（校验 target 在 characters 存在再翻转）+ `effective_protagonist`（ctx override > 配置期）+ 持久化 `state/protagonist_runtime.yaml`（跨回合/续读生效）；`protagonist.py` 不改、被复用。
  3. **候选备选稿** `src/runtime/alt_draft.py`：`write_alt_draft`/`list_alt_drafts`/`promote_alt_draft`——作者在某章下临时以另一镜头生成该章正文备选稿（**dry-run 不立库**：不触发成长迁移/事件/记忆；不生成各角色平行整树），选定后**提升**为该章最终成文并由此 `switch_protagonist` 切镜头；每时刻仍只有一条成文。
  4. **CLI 作者出口**：run_novel 既有 `read_line` 交互点挂「🧭 镜头/开关」菜单（换主导镜头 / 生成&提升候选备选稿 / 开/关能力 → 会话 `features_override` + 可选 `save_features`，下一回合起生效）；G1/G2 门闩改走 `CapabilityFlags`。
  5. **D9 同契约映射（只留文，W3 立项复用）**：`GET/PATCH /system/config` → `resolve_features`/`save_features`；`PUT /session/protagonist` → `switch_protagonist`/备选稿提升。
- **不动**：`protagonist.py` 保留、多 `is_protagonist` 告警原样、D9 Web 不建（W3 待立项）、不做多主角并列、不改成长/收益数值。默认 `features={}` → 行为逐字节等价。
- **验收**：默认全量回归与 G2 末一致（**359 通过 + 1 跳过**）；开启后单测断言规范读法命中、features.yaml 覆盖生效、旧深层命中 WARN、`switch_protagonist` 校验+替换+持久化、`effective_protagonist` override 优先；备选稿 dry-run 不立库、提升替稿并切镜头。
- **下一步**：按 SDD §7 编码（`capabilities.py` + `protagonist_switch.py` + `alt_draft.py` + run_novel 接线 + 作者菜单 + 单测）。

---

## 2026-08-31（再续七）

### G3 编码 · 一次 MVP（SDD D12，作者选定「候选备选稿」档；全量 **375 通过 + 1 跳过** = 基线 359 + 16 新测）

- **能力外观面** `src/runtime/capabilities.py`（新）：`CapabilityFlags`（11 项全默认关，`empty`/`any_on`/`to_dict`）+ `resolve_features(runtime_config, *, features_override=None, data_root=None)`（规范读 `runtime.features`；缺失字段回退**旧深层位置**（`_LEGACY_LOOKUPS`，含 `parallel_threads.enabled`/`evolution_pacing.*`/`internet_search` 等）并一次性 WARN 提示迁移；per-novel `config/features.yaml` 覆盖 > canonical > legacy；`features_override` 最高）+ `load_features`/`save_features`（原子写 features.yaml，不整树改 runtime）。
- **运行时镜头** `src/runtime/protagonist_switch.py`（新）：`ProtagonistContext`（可变，`is_override`）+ `effective_protagonist`（ctx override > `resolve_protagonist_id` 配置期）+ `switch_protagonist`（校验 target 在 `characters[].id` 存在才翻转，不在→WARN 保持）+ `format_lens_snippet`（按显式 id/name 重建主角提示块，换镜头后同一代码路径；`protagonist.py` 不改）+ 持久化 `state/protagonist_runtime.yaml`（`load`/`save`，override 才写、续读生效）。
- **候选备选稿** `src/runtime/alt_draft.py`（新）：`write_alt_draft`（`state/drafts/{chapter}_{lens}.md`，带头 `status=draft`）+ `list_alt_drafts`（按章读回）+ `promote_alt_draft`（置 `promoted`、可选 `canonical_writer` 落正篇副本、返回 `(canonical_path, lens)` 供切镜头；已提升→None）。备选稿**不**触发演进/事件/记忆立库（由 run_novel 侧抑制，是「试探镜头」非真实事件）。
- **接线** `run_novel_with_author.py`：loop 外 `resolve_features`（一次）+ `effective_protagonist`（会话 override > 配置期，L99 改走）；`main_characters_snippet` 改由 `format_lens_snippet` 按当前镜头重建；**G1/G2 门闩迁移到 `CapabilityFlags`**（桥接→`bridging`、屏外批→`off_screen_batch`、演进耦闸→`evolution_pacing`、节拍标签→`beat_tags_to_growth`，均保留原配置块读参）；作者「🧭 镜头/开关」菜单（仅 `_flags.alt_draft` 或工作台开启时展示，默认零打扰）：`l` 换主导镜头（校验+重建提示块+持久化）、`c` 开/关能力（写 features.yaml 会话生效）、`a` 列&提升候选备选稿（提升→替稿+切镜头）。
- **测试**：`test_capabilities.py`（6：默认全关/canonical 读/旧深层 WARN/features.yaml 覆盖优先/override 最高/序列化往返）+ `test_protagonist_switch.py`（6：配置期/override 优先/校验+持久化/非法 no-op/镜头提示块）+ `test_alt_draft.py`（5：写列/提升写 canonical+翻转/未知返 None/无 canonical_writer/空返回）。默认 `features={}` 全量回归 **375 通过 + 1 跳过**。
- **下一步**：D9 Web `/system`（W3）落地复用本表面（`resolve_features`/`save_features`/`switch_protagonist`）。

---

## 2026-08-31（再续八）

### G4 文档闸 · SDD D13：Novel-Data 工作台（多小说进度 ⇄ 数据图谱 ⇄ 作者控制台）

- **登记**：**SPEC_SDD D13** 挂屏；`docs/design/novel-data-workbench.md` 定稿；next-iteration D9 承接项挂链。
- **背景**：G1/G2/G3 已建六类**确定性数据面**（成长五维+迁移日志、关系语义边、信息视野、大纲进度+节拍、记忆 L1/L2/L3、屏外/并列线），D9（novel-reader-ui）只开了壳并把成长标「远期」→ 本 G4 把它们串成可直接实现的整体前端。
- **三主线**：①**多小说进度总览**（`/novels` 索引 → 各小说 progress 摘要卡片）；②**单小说数据图谱**（`/novels/:slug`：关系全书谱/角色心图/角色对、人物五维雷达+迁移时间线、信息视野开关、记忆分层时间线、屏外线、章节节拍情志条）；③**作者控制台**（复用 G3 `parse_features`/`switch_protagonist`/`alt_draft` 三写点 + D9 Session 作者在环 + `/system`）。
- **首切片**：**G4a 后端确定性 Read/写口 API**（`novels`/`graph`/`characters`/`outline`/`console`，全委托既有模块、无 LLM、可单测）；**G4b 前端壳+图谱页**（承接 D9 W1–W2）；**G4c 作者控制台**（写口 + W3–W4）。
- **不动**：不重建领域模型、不重写引擎、不做整树多镜头成文（仍 G3 单导出镜头+单章备选稿）；所有视图只读/固定性，写回仅经 G3 白名单。
- **下一步**：从 **G4a 后端 Read API** 起（可先实现、单测全绿、不破船）。

---

## 2026-08-31（再续九）

### G4a 编码：后端确定性服务层（`src/workbench/`）

- **定位**：无 `web/`、无 FastAPI → G4a 实作**纯 Python 确定性服务层** `src/workbench/`（无 LLM、无 Web 依赖、单测全绿）；G4b 的 FastAPI router 只需对同名模块薄包装，不重复实现聚合逻辑。
- **模块（对齐 SDD D13 §5 各 Router）**：
  - `common.py`：多小说发现（`data/novels/index.yaml`，缺失回退 glob）、`meta.yaml`、角色名册（`config/characters.yaml`）、scope 事件目录扫描。
  - `novels.py`：`novel_summary`/`index_novels` —— 每书进度卡（当前章/拍/回合 + 成长爆发 + 关系边数 + scope 事件数），委托 `outline_store`/`relationship_graph`/`character_growth`。
  - `graph.py`：`full_graph` / `ego_graph`（BFS 1..hops）/ `pair`（关系 + change_log）；inactive 边标 `inactive: True` 供前端虚线。
  - `characters.py`：五维成长 + 迁移日志、信息视野（复用 `info_view.event_visible_to_character` 盘读已知/未知）、L1 记忆（`book/characters/<id>/events/turn_*.md` + `classify_memory_layer`）、屏外线（`load_off_screen_threads`）。
  - `outline.py`：整树大纲 + 当前指针 + `missing_ref`（进度引用失效显式标注）；无大纲降级 `{"present": False}`。
  - `console.py`：读 `console_status`（镜头/能力面/备选稿）；写口 `patch_features`→`save_features`、`switch_lens`→`switch_protagonist`+`save_protagonist_context`、`write_draft`/`list_drafts`/`promote_draft`→`alt_draft`，全走 G3 白名单。
- **落盘现实（口径已在 SDD §4 备注）**：盘上只持久 **L1 事实 + 屏外线**；**L2/L3 记忆、平行主线线程为运行期内存态（`MemoryStorage`），未落盘** → 工作台记忆视图给 L1 分层时间线并标 `runtime_only_layers: true`（不为此新增 L2/L3 持久化，超 G4 只读视野）。
- **测试**：20 条单测（novels×4、graph×3、characters×4、outline×4、console×5）对临时 data/novels/<slug> 树断言；全量 **395 通过 + 1 跳过** = 基线 375 + 20 新。
- **文档**：next-iteration G4 承接项标 G4a ✅；SDD D13 §4 补落盘现实脚注、§5 标服务层落地位、§7 G4a 行标 ✅。
- **下一步**：**G4b 前端壳 + 图谱页**（承接 D9 W1–W2，读 G4a）。

---

## 2026-08-31（再续十）

### G4b 编码：Web 后端 + 静态工作台（浏览器读 G4a / `src/workbench/`）

- **定位**：G4a 是纯 Python 确定性服务层；G4b 给出浏览器入口。环境已备 FastAPI 0.115 + uvicorn + node v20；但 `requirements.txt` 不钉 fastapi（web 为可选层）→ web 测试用 `importorskip` 守卫，缺 fastapi 时跳过、核心 pytest 不受影响（船身不破）。
- **后端薄包装** `web/api/app.py`：`create_app(project_root)` FastAPI 工厂，`/api` 前缀挂五 router——`novels`（索引/摘要）、`graph`（全书谱/ego 心图/单对+change_log）、`characters`（人物索引/详情/信息视野）、`outline`（大纲/进度指针，含 missing_ref）、`console`（读镜头/能力面/备选稿；写 PATCH features / PUT protagonist / GET+POST drafts / POST drafts:promote，全走 G3 白名单）；`app.state.WORKBENCH_ROOT` 供按 slug 解析 `data/novels/<slug>/`（404 守卫）。根路径挂 `web/static/`。模块级 `app = create_app()` 供 `python -m uvicorn web.api.app:app`。
- **静态仪表盘** `web/static/index.html`：**无构建**（纯 HTML+JS+fetch，node --check 通过）——多小说进度卡 + 单小说关系谱（SVG 力导向式布局，inactive 虚线）/人物（五维+迁移+视野+L1 记忆+屏外线）/节拍情志条（当前拍高亮）/作者控制台（能力开关 pill 切换 PATCH、导出镜头 select PUT、备选稿建稿+提升）。L2/L3 记忆以 `runtime_only_layers` 标「会话内可见」。
- **测试**：`tests/unit/test_web_api.py` 10 条 TestClient（对临时 data/novels/<slug> 树）——索引/摘要、graph 三态、characters 详情/视野、outline/progress、console 读写（PATCH features 落盘、PUT protagonist 切换、drafts 建稿+提升）、404、静态根页；无 fastapi 时整模块跳过。
- **全量**：**405 通过 + 1 跳过** = 基线 395 + 10 新。
- **文档**：next-iteration G4 承接项标 G4b ✅；SDD D13 §7 G4b 行标 ✅（React/Vite 前端仍留 W 系列替换静态页）。
- **下一步**：**G4c 作者控制台**（写口 + D9 Session 作者在环 W3–W4，`author_workbench.enabled=true` 时前端为唯一作者交互、终端静默）。

---

## 2026-08-31（再续十二）

### CC-b 编码：CompressionContract + 规则/软原型生成器（上下文压缩，D8）

- **定位**：SDD `context-compression-adaptive-layered.md`（**D8**，文档闸 ✅ 2026-03-29）分阶段落地中的 **CC-b**——**CompressionContract 数据结构 + 规则/软原型生成器**。纯确定性、**无 LLM**、**不挂载检索链路**（挂载=CC-c），不改变现有 `retrieve_for_intent` 硬截断行为（船身不破）。
- **`src/author_loop/context_compression.py`**：
  - `LayerRole`（name/importance/compress_strategy）+ `CompressionContract`（task_thread / structure_preservation / layer_roles / sacrifice_order / query_focus / prototype_id）+ `to_dict`/`contract_summary`（§5 可观测）。
  - `build_compression_contract(phase, intent_id, user_input, retrieval_query, confidence)`：软原型匹配（`design_discussion`/`design_edit`/`save_progress`/`main_review`/`general`，按 phase+intent 对齐，仅给 layer_roles/structure/sacrifice 初值）+**自适应修正**（长输入 ≥120 字抬高「作者原句」层到 keep、短输入不触发）+**兜底最小安全集**（低置信 <0.5 或 `intent_fallback` → 任务句+作者原句(或截断)+来源标签骨架+事实锚点，**禁止合为单段结论**）。
  - `task_thread` 为**过程性**描述（“辅助作者<阶段动作>——意图：<…>（作者输入：…）”），非剧情结局式概括。
- **测试**：`tests/unit/test_context_compression.py` 11 条——五类原型契约字段合理（高权重层最后牺牲）、fallback/低置信最小安全集、长输入自适应、query_focus 回退作者输入、task_thread 过程性、to_dict/summary 往返；全量回归 **427 通过 + 1 跳过**（基线 416 + 11）。
- **排障（预先存在的测试水位泄漏，非 CC-b 引入）**：全量初次 427 绿，随后一次因 `data/book/events/main/` 跨多次全量测试累计 **507 个 turn 事件**、超过 `get_recent_events(k=500)` 截断窗口而假失败（`len(events)>=n_before+1` 恒不成）。修复=**两者都做**：① `test_orchestrator.py` 该断言改用 `get_event_count` 增量 + 新事件 summary（对累计 state 稳健）；② 清理累计归位（保留最新 20 turn，事件水位降至 <<500）。整改后连续两轮全量 **427 通过 + 1 跳过**。
- **下一步**：**CC-c**（组装后钩子 + 门限 threshold_ratio=0.75 + 分块压缩提示模板；超阈触发、输出仍含分块/来源）；或 `I6`（策略 A/B 与回滚）、任务 E。

---

## 2026-08-31（再续十一）

### G4c 编码：作者控制台（Session 作者在环 + 互斥）

- **定位**：G4a/G4b 已把「读 + 定制调整写口」落到 Web；G4c 接 D9 **Session 作者在环（W3–W4）**——把 `run_novel_with_author.main(input_fn=adapter.read)` 放进后台线程、作者经由 `web/api` 的 pending_prompt → `POST /reply` 作答，并落实 §6.1 **互斥**：`author_workbench.enabled=true` 时前端为唯一作者交互、终端不读 stdin 仅日志。
- **传输层** `src/author_harness/workbench_ingress.py`（纯 Py、无 LLM 无 Web 依赖）：`WebInputAdapter`——`read(prompt)` 设 pending 并阻塞，`set_reply(text)` 唤醒、`abort()` 令其立即返回隐含串；`LogOnlyAuthorIngress`——**永不读 stdin、永不阻塞**，任何 prompt 立即返回空串并打 `[作者在环] AWAIT_AUTHOR` 日志。
- **Session Runner** `web/api/session_runner.py`：`WorkbenchSession`（daemon 线程跑 `run_fn(input_fn=adapter.read)`，run_fn 可注入，默认 `run_novel_with_author.main`）+ `SessionRegistry`（data_root → 活跃会话 一地对一；已 running 再建由 router 回 409）。
- **路由** `web/api/routers/session.py`：`POST /session`（建会，已活跃 409 互斥）、`GET /session/{key}`（状态 + pending_prompt 轮询）、`POST /session/{key}/reply`（喂答案）、`POST /session/{key}/abort`、`DELETE /session/{key}`（释放锁）。`create_app` 挂 registry + 可注入 `SESSION_RUN_FN`。
- **互斥门**：`runtime.author_workbench.enabled` 落 `config/novel_writing.yaml`（默认 `false`，行为不变）；`run_novel_with_author.main` 顶部——`enabled=true` 且未注入输入源时把 `input_fn` 置为 `LogOnlyAuthorIngress`（终端仅日志、不读 stdin），已注入（前端 adapter）则原样直通。
- **测试**：`tests/unit/test_author_ingress.py`（6 条，阻塞读/回喂/取消/仅日志）+ `tests/unit/test_web_session.py`（5 条 TestClient，假回环隔离 LLM——建会→pending 轮询→reply 推进→done；409 互斥；404；abort 解阻塞+释放锁；fastapi 缺失自动跳过）。11 条新单测。
- **全量**：**416 通过 + 1 跳过** = 基线 405 + 11 新。
- **文档**：next-iteration G4 承接项标 G4c ✅；SDD D13 §6 增 G4c 落地位置、§7 G4c 行标 ✅。
- **前端接线** `web/static/index.html`：作者控制台顶部增「作者在环（互斥）」卡——开始作者在环（`POST /session`，data_root=当前 slug）、**pending 卡 + reply 输入框**（`POST /session/{key}/reply`）、中止 / 结束清理（abort/delete）；900ms 轮询 `GET /session/{key}` 续接同 uvicorn 进程内会话；`node --check` 通过。控制台从「纯定制调整写口」升级为「在环交互 + 定制调整」双区（G4c 收口）。
- **全量复查**：**416 通过 + 1 跳过**。
- **下一步**：React/Vite 换壳（W 系列）、任务 E、D9 W 系列、**CC-c**（组装后门限+分块压缩）、I6。

---

## 2026-08-31（工作台 /system 系统设置，GG5）

### `/system` 系统设置面板（G4c+，LLM 只读 + 工作台/联网可写）

- **背景**：G4 工作台缺 `config` 级别系统设置读口（D9 §5.6 `W3 /system` 可写未落）；前端 `/`→`/api/novels` 存在但无系统设置面板。
- **写口设计（复用 G3 features.yaml 同构）**：`load_runtime_config` 的 per-novel `deep_merge` 覆盖顶层 → 写 **per-novel `data/novels/<slug>/config/runtime.yaml`** 顶层 `runtime:` 下 `author_workbench`/`author_harness.internet_search`，**只写白名单键、合并保留既有键**（e2e 的 `novel_run` 照留），**不动 `config/*.yaml` canonical**；删除 override 键即回默认。**生效边界**：设置由 `main` 启动时快照 → 改后下一会话生效（诚实标注）。
- **新增** `src/workbench/system.py`：`system_status(project_root)`（读 effective `framework.llm/llm_options` + `runtime.author_workbench.enabled` + `internet_search`）+ `patch_system(project_root, patch)`（白名单深写 + yaml.dump 保留顺序）。**LLM 只读**（真实提供方由 `.env`/密钥驱动，中途改易断链）；**`author_workbench_enabled` + `internet_search.{enabled,provider,max_chars,trust_level}` 可写**。
- **新增** `web/api/routers/system.py`：GET `/api/system` + PATCH `/api/system`（薄包装 system.py）；`create_app` 挂 `/api`（StaticFiles mount 之前）。fastapi 缺失自动跳过。
- **前端静态面板**：`index.html`「系统」按钮切换到 `secSystem` 分区——当前书 slug/root、LLM 只读卡（openai_compatible/火山方舟 model·base_url·timeout）、workbench 互斥开关、联网 enabled/provider/max_chars/trust_level 控件；任一改动作 PATCH → GET 刷新；标「下一会话生效」。
- **测试/全量**：`test_system.py`（纯 service；temp project config/current_novel → novel，写 PATCH → 读回断言 + 保留既有键 + LLM 忽略写）+ `test_web_system.py`（fastapi importorskip，GET/PATCH round-trip + 校验 400）；全量 **438 通过 + 1 跳过**。
- **下一步**：工作台面板 #2 五维雷达 / #3 迁移日志时间线 / #4 L1记忆/屏外线时间线 / #5 跨卡联动。
- **规划补录**：面板 #2-#5 正式列入 next-iteration「待办·工作台面板补全」块（此前仅 WORKLOG 一行备忘）；确认 `require_classifier_signal` **保持 I5 默认=true** 不暴露（联网须作者明确要求才抓），`/system` 联网闸维持 enabled/provider/max_chars/trust_level 四键可写。

---

## 2026-08-31（工作台远程访问与鉴权，GG6）

### 远程访问可配 + 密码登录（Basic Auth，默认关）

- **背景**：web 工作台默认 uvicorn loopback 仅本机；用户确认要**前端可通过互联网访问**，并要求先支持**鉴权·密码登录**、监听可配。现状 app 无任何鉴权、写口全开，直接锁公网=裸奔。
- **方案（doc-first，D13 §6.5 + §7 GG6 行）**：新增 **`config/web_api.yaml`**（web 服务层专用，独立于小说运行时配置）：
  ```yaml
  server: { host: "127.0.0.1", port: 8000 }   # 改 0.0.0.0 = 允许局域网/公网监听（见 ⚠）
  auth: { enabled: false, username: "", password: "", realm: "Novel-Data Workbench" }
  ```
  - `auth.enabled=true` 时 **全站 Basic Auth 中间件**（`/api/*` + 静态页一并保护，浏览器原生「密码登录」弹窗）——`web/api/security.py::load_web_settings/verify_credentials/ + 中间件工厂`，口令 `hmac.compare_digest` 常量时间比较。
  - **空口令启动报错**：`enabled=true` 但 username/password 空 → `web/api/server.py` fail-fast，绝不静默无鉴权。
  - **可配监听**：`python -m web.api.server` 读 `server.host/port` 直接 `uvicorn.run`（免手敲 `--host`）。
- **暴露边界（诚实）**：app 无 OAuth/CORS 层；Basic Auth 为服务器明文共享口令，只适合单作者局域网/反代后自用，**不建议直接对公网**；公网请反代 + 更强认证或 `ssh -L` 隧道零暴露写口。
- **测试**：`test_web_security.py`（importorskip）——`verify_credentials` 正/误/关、`load_web_settings` 默认/override、TestClient 启用鉴权后 401/200 + 静态也拦截、默认关不破既有。全量回归保持绿。
- **下一步**：面板 #2-#5；或按需把 Basic Auth 升级为 nginx 反代/OAuth 供公网长期暴露。
- **定策补录（2026-08-31，用户确认自用）**：工作台主要**自用**，安全整体后置（Basic Auth 已够单作者局域网/反代后自用）；「安全强化」记为后期任务（反代+OAuth、HTTPS/TLS、口令存储最小化、会话/限流、CORS 白名单），已列入 next-iteration 待办「远程访问安全强化」，近期不立项、不阻塞功能主线。

---

## 2026-08-31（工作台面板 #2 五维成长雷达图）

### 后端确定性度量 + 前端内嵌 SVG 雷达（GG-W #2，doc-first D13 §6.6）

- **背景**：`character_detail` 已返回五维成长（`growth.power/mind/social/goal/resource_state`，均为 `dict[str,int]` 且 ~3-5 项），但卡片只是无渲染的字典。用户按 next-iteration 待办优先级开工 —— **#2 五维成长雷达图** 打头。
- **方案（doc-first，D13 §6.6 metric + §7 GG-W 行）**：
  - **度量** `growth_radar`：每维 `intensity = Σ(数值型子状态值)`；`level = min(1.0, Σ/6.0)`（四舍五入 3 位）——**确定性无 LLM**，语义为**成长深度**（无状态=0、多个成熟子状态=1），**非绝对特质分**；非数值型（str/bool）不计入，缺失维给 `attributes=[]`、`level=0`。
  - **实现**：`src/workbench/characters.py` 新增 `radar_vector(growth) -> list[5]`（`dim/label/level/intensity/attributes`）+ `_DIM_LABELS`（能力/心理/关系/目标/资源）+ `_GROWTH_DEPTH_SCALE=6.0`；`character_detail` 返回并入 `growth_radar`。
  - **前端**：`web/static/index.html` 新增 `radarSVG(rad)` —— 5 点正多边形 SVG（环 0.33/0.66/1.0 + 轴 + 每维标签/level 值，150×132 viewBox 内联），人物卡标题下直插。
- **测试**：`test_workbench_characters.py` 增 `test_radar_vector_levels_and_detail_field`（power Σ6→level 1.0、goal Σ1→0.167、无状态 0.0、标签/attributes、非数值剔除）+ `test_radar_vector_empty_growth_all_zero`（空五维 → `[0.0]*5` 空 attributes）。全量 **450 通过 + 1 跳过**。
- **下一步**：**#3 迁移日志时间线**（`transition_log` 时间线视图）。

---

## 2026-08-31（工作台面板 #3 迁移日志时间线）

### 前端人物卡按 turn 展开 transition_log（GG-W #3，doc-first D13 §6.6）

- **背景**：`character_detail.growth.transition_log` 已含完整迁移审计（cap 100），但卡片只显示计数。按 #2 后优先级推进 #3 —— 纯前端渲染时间线。
- **方案（doc-first，D13 §6.6 + §7 GG-W 行）**：人物卡内 `growthTimeline(gr.transition_log)` 按 `turn` 升序展开两类条目——
  - **成长命中**：`#turn` + scope + 规则名 + deltas（`dim→label(key)+±value` 徽标）+ reason（截 60 字）；
  - **guard 审计**：`guard.clamp/skip` →「钳制/跳过」warn 徽标 + `guard` + `guard_reason`。
  - 无日志显示「无迁移记录」；**无新增后端读口**（零后端改动，default 不破）。新增 `.tl`/`.tl-row`/`.pill.warn` 样式。
- **验证**：`node --check` 全部 inline JS 通过；`growthTimeline` 成长/guard 双分支样例逻辑核对正确；全量 **450 通过 + 1 跳过**。
- **下一步**：**#4 L1记忆 / 屏外线时间线**。

---

## 2026-08-30

### 大纲 MVP-2：progress.yaml 写回 + 作者在环节拍推进

- **背景**：大纲**读侧**（MVP-0 加载/日志、MVP-1 注入分析/正文、MVP-1b 设定→大纲生成）已收口，但停在「只读不写」——`turns_in_beat` 恒 0、「建议单节拍 <N 回合」软提示从不增长、节拍 `status` 无人置 done、进度不可重启续读。
- **新增写回 API**（`src/runtime/outline_store.py`，确定性计算与 I/O 分离）：`bump_turns_in_beat`（+1）、`advance_to_next_beat`（同章下一拍→下一章首拍→末章末拍返 None）、`save_progress`（写盘补 `updated_at`）、`resolve_outline_context`（单次解析返回 snippet+beat）；`BeatContext` 增 `missing_ref`（引用失效显式置位）。
- **接线**（`run_novel_with_author.py`）：每确认写回一个有效回合即 `turns_in_beat += 1` 写回；作者在环显式菜单推进节拍/章（`+`/`b`/`c`/`s`），**无静默跳章**；每回合改用 `resolve_outline_context` 单次解析（消除重复 `resolve_current_beat`/`outline_injection_options`）；大纲构建异常由静默 `log.debug` 改为**首损 WARN**。
- **测试**：`tests/unit/test_outline_store.py` 追加 bump/advance/save+reload/missing_ref 等；全量回归通过。
- **下一步**：大纲 Phase 2（全量回写 outline.yaml、拆 beats）、任务 E、D9 工作台 W1–W4、CC-b、I6。

### 三层记忆分层落库 + 写入校验 + 检索消费（角色独立演进）

- **背景**：成长状态机各阶段已收口，但角色记忆仅存 L1 事实标签；本节把 §4 三层记忆**真正落地**——每个关键角色除「发生了什么」（L1）外，还独立保留「我如何理解」（L2，可更新）与「我下一步打算」（L3，可过期）。
- **新增** `src/runtime/memory_layers.py`：确定性分类器（`classify_memory_layer` 关键词 L3→L2→L1）、`interpretation_subject`（L2 upsert 键）、`strategy_expires_turn`（ttl）、`build_layer_entry`（统一标签）。
- **存储** `src/runtime/storage.py`：新增 L2 `_char_interpretations`（`upsert_interpretation` 按 subject 原地替换）、L3 `_char_strategies`（`append_strategy` + `get_active_strategies` 过期过滤）+ `get_event_count`。
- **写回** `src/orchestrator/orchestrator.py::apply_memory_write`：`agents.characters.memory_layers` 开关门——**默认关**只写 L1（船身不破）；开启时 L2→upsert / L3→append_strategy（带 expires_turn）。写入校验语义即槽位语义（事实不动/解释可更新/策略可过期，§9 阶段2 承诺闭合 ✅）。
- **检索** `src/retrieval/memory.py::retrieve_character_memory(include_layers=False)`：开启追加 `[解释（L2）]`/`[短期计划（L3）]`；`CharacterAgent.turn()` 传 `include_layers=bool(memory_layers)`，仅注入自身 L2/L3、无跨角色泄露（信息视野一致）。
- **测试**：新增 `tests/unit/test_memory_layers.py`（分类 L1/L2/L3、upsert 原地更新、策略过期过滤、apply_memory_write 开关两态、retrieve include_layers 两态），全量回归通过。
- **下一步**：大纲 MVP-1b/2、任务 E、D9 工作台 W1–W4、CC-b、I6、成长 MVP 后续。

### 真实 LLM 联调验证（Linux 移植收尾）

- **背景**：2026-08-27 Linux 迁移收口时，LLM 侧仅完成配置对齐，真实联调未验证；本次补上「真实 LLM 下作者在环一回合全链路」验证，闭合 Linux 移植最后一项。
- **LLM 端点**：`config/system_config.yaml` 的 `framework.llm_options` 切换为 **火山方舟（Volcengine Ark）OpenAI 兼容端点** `https://ark.cn-beijing.volces.com/api/coding/v3`，模型 **deepseek-v4-pro**；密钥仍走 `DASHSCOPE_API_KEY` 环境变量（`.env` 本地注入，gitignored）。
- **验证产物**：新增 `tests/integration/test_llm_live_e2e.py` —— 真实 LLM 下作者在环一回合全链路（设定保留→y 完成→写作前分析（LLM）→正文生成（LLM）→阶段一 y→事件簿/状态写回→阶段二 y→角色记忆写回）；**默认跳过**，仅在项目根 `.env` 同时含 `DASHSCOPE_API_KEY` 与 `LLM_E2E=1` 时执行。辅助脚本 `_llm_e2e_runner.py`（本地临时清理/移植，不入库）已删除。
- **结果**：LLM smoke（`deepseek-v4-pro` 应答正常）+ 全链路 E2E **通过**；正文落盘 `data/book/events/main/events/turn_0001.md`（真实模型产出，含「摘要/正文」段）；日志含「设定阶段结束，进入正篇」「已写回角色记忆」。
- **收尾**：`.env` 中 `LLM_E2E=1` 已移除（保留 Key），默认 `pytest tests/` 跳过 live 用例；全量 **251 通过 + 1 跳过（live）**。
- **后续**：回到工程主线 **MVP-2**、任务 E、**D9 工作台 W1**、**CC-b**、**I6**（见 [docs/planning/next-iteration.md](./docs/planning/next-iteration.md)）。

### 主角姓名一致性修复（主线叙事者注入主角名册）

- **问题**：真实 LLM 联调生成的正文中，主线叙述把主角写成了「苏明」，而 `characters.yaml` 定义的是「林昭」。根因：**ScopeAgent（范围/主线叙事者）的 prompt 未注入主角姓名与关键角色名册**，模型自行虚构姓名；`build_turn_plan_prompt` / `build_turn_body_prompt` 同理。
- **修复**：新增 `src/runtime/protagonist.py::format_main_characters_snippet(runtime_config, characters_config)`，复用 `resolve_protagonist_id` 生成「【主角与主要角色】」提示块（叙事主角 + 主要角色名册 + 「不得虚构或替换主角姓名、以主角为镜头主轴」约束）；无主角时返回空串。注入三处：`ScopeAgent._build_scope_prompt`、`build_turn_plan_prompt`、`build_turn_body_prompt`（`Orchestrator.from_config` 向 ScopeAgent 传 `characters_config`；`run_novel_with_author.py` 计算一次并传入计划/正文两阶段）。补齐 MVP-1「正文以主角为主线」对**大纲文件缺失时**的主角注入。
- **测试**：新增 6 条单测（`test_protagonist.py`×3、`test_agent_shells.py`×1、`test_turn_planning_pacing.py`×2），断言主角名与「不得虚构」约束出现在 scope/plan/body prompt；全量 **257 通过 + 1 跳过（live）**。

### 角色独立演进：设计文档对账与优化（doc-first 闸门）

- **背景 / 定位定稿**：确立两层模型 **多视角内部模拟 ⊕ 单一主角导出**（§1.2a）——**内部**是一个类似真实世界的多视角世界：每个关键角色（含主角）各持完整独立的经历/记忆/知情视野/成长状态，独立演进、互不合并、无主角特权；**导出**则由用户从关键角色中选择其一作为本小说叙事主角（`protagonist_id`/`is_protagonist`），主书以该主角为镜头重导出——这仅是对某个已完成视角的渲染收敛，不限制内部哪些角色演进。该定位与既有原则（[outline-and-beats.md](./docs/design/outline-and-beats.md)：正文以主角为主线、每角色系统内为平行主线）一致，`protagonist.py` 单主角导出逻辑保留、不推翻。
- **文档与代码对账（三处脱节修复）**：优化 [docs/design/character-growth-state-machine.md](./docs/design/character-growth-state-machine.md)——
  1. **关系图谱已实现**：原文档把 `relationship_graph.py`/`retrieval/relationship.py` 写成"新增"，实际已存在且仅落 `co_presence` 共现边；修订为"扩展为语义关系"（`relation_type/intensity/status/方向` + 复用既有 `evidence_events`/`get_relation`/`get_neighbors`/`get_relation_change_log`）。
  2. **`emotions[]` 槽位落地**：`MemoryStorage` 每角色 `emotions[]` 已定义但无人写入，明确作为 `mind_state` 的进程内承载。
  3. **信息视野/感知不对称（新 §4.6）**：补上独立演进前置机制——`shared_story_snippet` 由全量公开流改为**按角色知情的过滤视图**（可见性标签 private/scene_known/public），未知剧情给占位而非剧透，让两个关键角色对同一事件可产生差异化解读；与主角单镜头不冲突（信息不对称作用于系统内演进，主书仍以主角视角）。
- **接入方案修正（§5）**：`relationship_graph.py` 移到"已存在需扩展"；新增 `src/runtime/character_growth.py`、`src/retrieval/growth.py`、`src/retrieval/info_view.py`；注入点对齐既有 `format_main_characters_snippet`（已接入 ScopeAgent 计划/正文三处）。
- **分阶段重排（§9）**：阶段 1a（差异化视野 + 语义关系，独立演进前提）→ 阶段 1b（五维状态迁移）→ 阶段 2（GrowthGuard + 校验）。§8/§10 增加"信息视野过滤"类测试与验收（角色不得获得未知事件剧透）。
- **结果**：文档对账完成，无过时"新增关系图谱"表述；全量 **257 通过 + 1 跳过（live）**（纯文档改动，无代码变更）。
- **下一步**：按修订后 §9 **阶段 1a** 立项编码（先做差异化视野 + 语义关系，再铺五维迁移）；见 [docs/planning/next-iteration.md](./docs/planning/next-iteration.md) 当前焦点第 3 项。

### 角色独立演进（阶段 1a 编码）：信息视野 + 语义关系边 + 成长骨架

- **背景**：在修订后设计文档 §9.1a 之上落地 MVP-A 三项，为"关键角色独立演进"提供机制本体；全程不新增 LLM 依赖（DummyLLM 路径保持现状），LLM 增强挂开关后。
- **信息视野（§4.6，头号）**：
  - 事件写回打可见性标签 `event_entry["present_characters"] = 在场角色`（`orchestrator.apply_event_and_state_write` 两分支统一）；`file_sync.sync_scope_turn` frontmatter 持久化该字段并回读，跨进程 reload 后信息视野仍可判。
  - 新增 `src/retrieval/info_view.py`：`event_visible_to_character`（按 `present_characters` / `visibility==public` / 旧数据默认可见）、`build_character_event_view`（按角色过滤视图，未知部分只计数不泄内容）。
  - `CharacterAgent` 的"最近剧情"改为注入该角色自身信息视野（有 storage 时），堵住上帝视角；壳路径无 storage 时沿用原 `shared_story_snippet`，不破坏既有壳行为。
- **语义关系边（§4.5）**：`relationship_graph.py` 增 `infer_scene_relation`（轻量词典）+ `upsert_semantic_edge`（带 `rel_type/intensity/status/方向`，复用 `evidence_events`/`change_log` 去重累积）+ `sync_semantic_relations_from_event`（场景关键词命中则升级在场语义边，无命中保持 co_presence）；编排器在共现边之后接入。
- **成长状态骨架（§2）**：新增 `src/runtime/character_growth.py`——`CharacterGrowthState` 数据类 + `load/save_growth_state`（落盘 `<novel_root>/book/characters/<id>/growth_state.yaml`）+ `record_mind_emotion`（接入已有 `storage.emotions[]` 空槽位）+ `format_growth_snippet`。完整五维迁移规则留阶段 1b。
- **三层记忆标签（§4）**：`apply_memory_write` 的 `event_refinement` 带 `layer="L1"`（分层迁移逻辑留 1b）。
- **测试**：新增 `test_info_view.py`（角色仅见在场事件、未知不泄内容、public/缺省可见性）、`test_character_growth.py`（字段/持久化 round-trip/emotions 写入）、`test_stage1a_wiring.py`（编排器打 `present_characters` + CharacterAgent 注入信息视野且不含未知剧透）；扩展 `test_relationship_graph.py`（语义边创建/去重/关键词升级/无命中不建边）。全量 **277 通过 + 1 跳过（live）**。
- **下一步**：阶段 **1b**（五维状态迁移规则，接入 `apply_growth_transition`），并可启动 **U-6** 回合内角色交互/反应链预研；见 next-iteration 当前焦点第 3 项。

### 角色独立演进（阶段 1b 编码）：五维语义迁移规则

- **背景**：落地设计文档 §2/§3 的迁移机制——把一条回合事件按关键词命中迁移规则，对该角色五维子状态（power / mind / social / goal / resource）做**确定性、非数值**的语义增量并写入 `transition_log`（round-trip 可审）。
- **规则集（`src/runtime/character_growth.py`）**：约 10 条 `_RULES`，每条含 `name`/`keywords`/`apply`，命中其一即触发——`near_death`（濒死/劫后余生）、`trusted_betrayal`（背叛/出卖/欺骗）、`rescue_debt`（救命/恩人）、`conflict_showdown`（对峙/决战/交手）、`deep_loss`（死别/遇害）、`resource_gain`/`resource_loss`（获得/损失）、`goal_affirmed`（领悟/起誓）、`horror_trap`（陷阱/被擒/中毒）、`romance`（爱慕/表白）。配套辅助 `_bump`（计数维度累加，软上限 `_MAX_BUMP=5`）、`_set`（语义值 low/med/high 覆盖）、`_delta`。
- **入口**：`match_rules_for_event(summary)`（命中哪些规则）、`apply_growth_transition(state, event_bundle) -> (state, fired)`（施加增量 + 写 `transition_log`，截留最近 100 条）、`apply_growth_transition_for_turn(storage, data_root, *, scope_id, turn_index, present_character_ids, event_entry)`（对**在场**关键角色循环 加载→迁移→落盘 `growth_state.yaml`→mind 变化写 `storage.emotions[]`，返回 `{cid: fired}`）。
- **接线**：`orchestrator.apply_event_and_state_write` 的 `data_root` 门内、语义关系边之后调用 `apply_growth_transition_for_turn`；仅在场角色受影响（与信息视野一致）。不新增 LLM 依赖，Dummy 场景无命中则状态不变，全量回归不受影响。
- **测试**：`test_character_growth.py` 新增 5 条——规则关键词命中、多规则增量 + transition_log、计数维度软上限、无命中状态不变、`apply_growth_transition_for_turn` 落盘 + emotions 写入 + 不在场角色不受影响。全量 **282 通过 + 1 跳过（live）**。
- **下一步**：GrowthGuard（阶段 2，强约束避免无代价膨胀）；可预研 **U-6** 回合内角色交互/反应链；见 next-iteration 当前焦点第 3 项。

### 角色独立演进（阶段 2 编码）：GrowthGuard 强约束

- **背景**：落地设计文档 §6 强约束——对阶段 1b 的迁移做叙事一致性校验，避免「无铺垫神跳级/无代价收益/立场反转」与目标动机抖动；校验失败**拒绝写回**或做**最小安全迁移**（钳制到界限），并把「被拒/被钳」记为 `transition_log` 告警条目（含失败规则与原因），满足 §7.1 可观测。
- **`GrowthGuard`（`src/runtime/character_growth.py`）**：确定性、非 LLM，四类校验与 §6 一一对应——
  1. **无代价收益禁止**（`balance_required`）：纯收益规则（`resource_gain`/`goal_affirmed`）缺同事件代价或既有积欠（`_has_prior_cost` 查 `损耗/人情债/伤势损耗/应激/创伤`）时被 `skipped`。
  2. **关系连续性**：同回合同时命中正向关系（`rescue_debt`/`romance`）与负向关系（`conflict_showdown`/`trusted_betrayal`）→ 跳过正向关系（避免「无事件铺垫立场反转」）。
  3. **目标切换冷却**（`goal_cooldown_turns`，默认 3）：目标类规则（`goal_affirmed`/`trusted_betrayal`/`deep_loss`）距上次目标变动不足冷却窗口时被 `skipped`（扫 `transition_log` 取最近目标回合）。
  4. **单回合跃迁边界**（`per_turn_delta_cap`，默认 3）：迁移后对计数维度净增超界做**最小安全迁移**钳制到 `old+cap`（`clamp`）——由于同事件多规则可累加同键（如 `损耗` 由 `horror_trap`+`resource_loss` 各 +1），单事件也会产生越界而被钳制。
- **入口**：`GrowthGuard.decide(fired, state, bundle)->(allowed, decisions)`，`apply_growth_transition_guarded(state, bundle, guard)->(state, fired, decisions)`（`guard=None` 时与无约束 `apply_growth_transition` 等价，兼容既有壳）；`apply_growth_transition_for_turn` 增 `guard` 参数并返回 `(results, guard_audit)`。
- **接线**：`orchestrator.apply_event_and_state_write` 传入默认 `GrowthGuard()`；`guard_audit` 中被拒/被钳条目打 `logger.info`（含角色/规则/原因）。
- **测试**：`test_character_growth.py` 新增 9 条——`guard=None` 等价、无代价收益被拒、有代价/有积欠放行、目标冷却跳过/超窗放行、同回合立场反转跳过正向、界内不钳、越界钳制并记告警。全量 **291 通过 + 1 跳过（live）**。
- **下一步**：可预研 **U-6**（回合内角色二次反应/对话链）、成长状态注入角色/范围 prompt（`format_growth_snippet` 消费）；见 next-iteration 当前焦点第 3 项。

### 角色独立演进（成长状态注入 prompt）：角色 + 范围叙事者

- **背景**：成长状态机三阶段（1a/1b/2）已落库并有 `format_growth_snippet`，但尚未供 agent 消费——关键角色行为不受自身成长驱动、主叙述与主角演进脱节。本次把成长状态注入**角色 prompt**（让每个关键角色决策真实反映其五维成长）与**范围叙事者 prompt**（让「单一主角导出」的叙述与在场角色演进一致）。
- **角色侧（`src/agents/character/agent.py`）**：`turn()` 有 `data_root` 时 `load_growth_state` + `format_growth_snippet`，经 `_build_character_prompt` 新参 `growth_snippet` 注入「当前目标」之后；并加一句引导「成长状态影响言行判断，但不主动念出状态名目」。无成长文件则该块不注入（保持既有壳行为）。
- **范围侧**：新增 `character_growth.format_present_growth_snippet(data_root, characters_config, present_ids)` 汇总**在场**关键角色的非空成长（按名标注，全空返回空串）；`TurnContext` 加 `present_growth_snippet` 字段并贯通 `build_turn_context(_from_storage)`；编排器 `run_one_turn` 在 `data_root` 门内计算并注入；`ScopeAgent._build_scope_prompt` 在主要角色名册之后渲染。
- **测试**：`test_stage1a_wiring.py` 新增 5 条——角色注入自身成长（含空模板不注入）、聚合 helper（只含非空在场角色、全空为空串）、范围注入在场成长、范围空成长不注入。全量 **296 通过 + 1 跳过（live）**。
- **下一步**：可预研 **U-6**（回合内角色二次反应/对话链）；见 next-iteration 当前焦点第 3 项。

### U-6：回合内角色二次反应链（先发批 → 定向二次批 → 合并）

- **背景**：成长状态机收口后，多角色场面的单回合仍是并行拼接——各角色独立产出言行，没有「听到对方、再回应」。U-6（backlog 第 6 项）要形成真实对话链，且依赖 §4.6 信息视野（只回应可见部分）。
- **两波模型（`src/orchestrator/orchestrator.py::run_one_turn` + `_apply_react_chain`）**：
  - **先发批**：现有并行 `turn(ctx)` 产出各角色首波（不变）。
  - **定向二次批**：`react_chain` 开关（`runtime_config.agents.characters.react_chain`，默认关）且在场 ≥2 个已注册角色时，为每角色并行 `CharacterAgent.react_to_peers(ctx, peers_snippet)`——peers_snippet 只含其他在场角色的**公开 `dialogue_action`**（同场可闻），**不注入任何他人 `inner_monologue`**（私有内心不跨角色，承接 §4.6）。
  - **合并**：把二次反应并入该角色 `dialogue_action`/`inner_monologue`；`CharacterTurnOutput` 增 `reaction` 字段供观测；写回/记忆/成长不变。
- **`CharacterAgent.react_to_peers`（`src/agents/character/agent.py`）**：精简 prompt「你已先行说过话；你听到在场其他角色的公开言行：…；请对其中与你相关的一人给出一段简短回应」，复用 `get_llm_provider`/`_parse_character_llm_response`；Dummy/异常 → 空 reaction。
- **配置**：`src/config/__init__.py` 默认 `agents.characters` 增 `react_chain: False`。
- **测试**：新增 `tests/unit/test_react_chain.py` 4 条——默认关无二波、开关开两波合并 + `reaction` 字段、**B 的 peers_snippet 不含 A 私有 inner（负例不泄）**、仅 1 个在场不触发二波。全量 **300 通过 + 1 跳过（live）**。

---

## 2026-08-27

### Linux 迁移收口（开发环境与文档）

- **背景**：本项目最初在 Windows 下开发；经核验，代码本身纯 Python 跨平台（统一 `pathlib`、全部文件 I/O 显式 `encoding="utf-8"`、无 Windows 专用库、无硬编码盘符）。「移植」工作集中在**开发环境文档、入口健壮性与过时文档状态**。
- **Linux 实测基线**：全量测试 250 通过；`run_novel.py`、`run_dev_agent.py`、`run_novel_with_author.py`（启动/配置/交互引导）均正常运行；依赖（含 playwright + chromium）齐备。
- **入口健壮性**：`run_novel_with_author.py` 主入口捕获 `EOFError`/`KeyboardInterrupt`，优雅提示退出（原为打印崩溃栈）；新增集成测试 `test_entry_script_exits_cleanly_on_stdin_eof`（子进程 stdin=DEVNULL，断言无 Traceback、含中断提示、非零退出码）。全量 251 通过。
- **文档 Linux 化**：`docs/guides/development.md` 重写为 Linux 指引（venv/依赖/常用命令/环境自检/LLM Key 配置）；`README.md` 修正「当前状态」（原「代码结构为占位，待实现」严重过时）与 Git 提交指引（去除 PowerShell/--trailer 历史段落）；`usage.md` 修正「Agent 为壳/主流程不调 LLM」过时描述、命令改 `python3`/`export`；`git-commit.md`、`cursor-and-devagent-workflow.md`（去 Windows 计划任务行）、`tests/README.md`、`SPEC_SDD.md` O2 行、三个入口脚本 docstring、`src/agents/dev/agent.py` 建议文案同步去 Windows 专有命令。WORKLOG 历史条目保留原文（历史记录不改写）。
- **LLM**：`config/system_config.yaml` 已是 `qwen-plus`（DashScope 兼容端点），Linux 下仅需 `export DASHSCOPE_API_KEY`；待真实联调验证（test_llm_chat + 1 回合作者在环）。

---

## 2026-06-14

### 小说作者在环工作台（D9，W0 定位修订）

- **修订**：由「只读观测前端」改为 **作者在环工作台** — Web 与 CLI **平行入口**；`WebInputAdapter` 等价 `AuthorSession.read_line`。
- **交互范围**：**设定工作台**（主菜单 `c`、`discuss_freely` 多轮）；**章节工作台**（写作前分析、正文审阅、`review_memory_plan`）。
- **运行模式**：`author_workbench.enabled=true` → **Web 唯一交互**，CLI **`LogOnlyAuthorIngress` 仅日志**（§5.5、§10）；禁止双循环。
- **系统设置**：路由 **`/system`**（侧栏 + 顶栏 ⚙），与小说 **设定工作台** `/settings` 分离；`GET/PATCH /system/config`（§5.6、§8.7）；**W2 只读**、**W3 可写**（含 `internet_search.enabled`）。
- **排期**：**W3–W4** 提升为交互核心（非远期）；见 D9 §11、next-iteration **W0–W6** 表。

### 小说阅读 Web UI（D9，W0 文档闸）

- **SDD**：[docs/design/novel-reader-ui.md](./docs/design/novel-reader-ui.md) — 六页 IA（概览/大纲/正文/设定/关系/角色演进）、Read API §8.2、章↔turn 聚合 §6、与作者在环边界 §10、**W0–W5** 切片。
- **登记**：`SPEC_SDD` **D9**；`docs/README` 设计表；`next-iteration` **W 系列**表与文首焦点第 7 项。
- **下一步编码**：**W1** FastAPI Read API（委托 `outline_store` / `file_sync` / `relationship_graph`）；**W2** React 四页只读 MVP。

---

## 2026-05-01

### 设定讨论：归档摘录分层排版（Assembler）

- **行为**：`assemble_retrieval_prompt_block(..., layout="design_discussion")` 走 `format_snippets_design_discussion`（序号标题 + 固定阅读顺序）；`design_phase._assembled_context_for_discussion` 已接线。主菜单 Harness 仍为默认 layout，与既有单测兼容。`discuss_freely` 任务段增加「**回复体例**」——先对齐各层归档摘录再分条列可归档条款。

### 设定讨论：优先通用范式 + 联网触发

- **`internet_query` 按类型**：读 `design_session.yaml` genre/theme，`classify_intent(..., config_dir=...)` 由 `design_phase` / 主菜单 Harness 传入；`_internet_query_type_augment` 按正文+标签拼西幻/都市/科幻/修仙等后缀，替换固定「修仙」套话。
- **规则**：`classify_intent` 在 `DESIGN_DISCUSSION` 增加「常规/主流修仙等级、多阶并列」等 `_internet_signals_generic_convention_heuristic` 兜底；分类 LLM 路由提示增加第③条「对齐常见档位需站外条目」。
- **提示词**：`discuss_freely` 增加「通用范式优于空想」条款，要求有外网摘录时先对齐、未要求原创时不独白编造小众刻度。
- **文档**：`author-interaction` §8.3 一条。

### OpenAI 兼容 LLM 默认 timeout

- **行为**：`build_openai_llm_from_config` 未显式指定 `timeout` 时默认 **180s**（原 30s）；`config/system_config.yaml` 中 `framework.llm_options.timeout` 同步为 **180**，减轻长 prompt 下 DashScope 等服务首包读超时。
- **叠加**：绑定作品后 `<小说>/config/runtime.yaml` 常带旧模板 `timeout: 30`，会覆盖 system；在 `load_runtime_config` 末尾若检测到仍为 **30** 则提升为 **180** 并打日志。草稿 `data/novels/draft-20260501-102116/config/runtime.yaml` 已改为 180。单测 `test_legacy_llm_timeout_30_elevated_when_novel_runtime_overlays`。

---

### 设定讨论：LLM 传输超时交互重试

- **行为**：`discuss_freely` 接入 `llm_invoke_with_transport_timeout_retry`（`httpx`/`APITimeoutError`/`socket.timeout`）；`design_phase` 传入 `session.read_line`。每次超时后提示作者是否继续；用尽预算后返回「多次未完成」占位说明。**SDD**：`author-interaction` §8.3 增补一条。

---

### I5 按需联网：分类器 intent + 检索门闩

- **行为**：`IntentClassification` 新增 `internet_search_needed`、`internet_query`。`DESIGN_MAIN`（LLM/Dummy）与 `DESIGN_DISCUSSION`（可选 LLM + 规则兜底）写出上述字段；主菜单 Harness 与 `_assembled_context_for_discussion` 传入 `retrieve_for_intent`。
- **门闩**：`InternetSearchSettings.require_classifier_signal` 默认 **true**；仅当分类器同意且 `internet_query`/`retrieval_query` 满足 `min_query_tokens` 时才调用 `search_web_bing_sync`。**闭包测试**可设 `require_classifier_signal: false` 恢复「仅配置 + token」的旧行为。
- **文档**：`author-in-loop-spec` §3、`author-agent-harness` §6/I5、§6 映射；`author-interaction` §8.2 表；`next-iteration` I5 表述；`novel_writing.yaml` 示例注释。
- **单测**：`test_classify_intent`（讨论/主菜单启发式）、`test_retrieve_for_intent`（门闩、`internet_query` 优先）。

---

## 2026-04-13

### 智能体基础方案完善（文档闸）

- **Spec（S2）更新**：`docs/specs/author-in-loop-spec.md` 新增目标态 SHOULD：  
  1) 受控联网知识检索；2) 规则动态加载；3) 策略自我迭代门禁（candidate patch → gate → 生效/回滚）。  
- **SDD（D6）更新**：`docs/design/author-agent-harness.md` 增补：  
  - §3 设计原则（动态装配、可审计迭代）；  
  - §4.3 自我迭代闭环（Critic / PolicyUpdater / Gate / PolicyStore）；  
  - §6.2 I0–I6 切片（从文档闸到联网 Tool 与回滚评估）。  
- **存储检索方案（D?）同步**：`docs/design/memory-storage-and-retrieval.md` 新增「外网知识缓存（可选）」分类、目录与检索映射（`book/knowledge/internet_cache/entries.md`）。  
- **排期同步**：`docs/planning/next-iteration.md` 新增 I 系列执行表与待办，并将产品级路线扩展到 **P5（策略自我迭代）**。

### 方案结论（本轮）

1. 保持作者在环与两阶段审阅为硬边界，不允许自我迭代直接覆盖核心门闩。  
2. 联网检索先做受控工具与证据落盘，再接入正文链路；默认“检索摘要用于参考”，不直接覆写正文。  
3. 动态规则加载先实现可版本化策略包（I1/I2），再做自我迭代（I3+），避免一步到位造成不可回滚风险。

### 下一步（执行版）

1. 继续推进 **I4（PolicyUpdater）** 最小实现：先产出 `candidate_patch`，保持建议模式不自动生效。  
2. 增加 **Gate** 基础校验与审计字段，确保策略更新可回滚、可追溯。  
3. I5（Playwright 路线）立项前补齐预算、超时、来源信任级与失败降级规则。

### 2026-04-13（续）· 节奏控制 SDD 草稿补充

- 在 `docs/design/author-agent-harness.md` 新增 **§4.4 章节目标驱动节奏约束（Pacing Contract）**：  
  - 将“写作前分析”后的约束结构化为 `pacing_contract`；  
  - 定义 `pace_mode / goal_window / subplot_reveal_budget / character_action_caps / forbidden_moves`；  
  - 明确暗线显露四级：`hint -> signal -> partial -> reveal`。  
- 将该约束并入 **I 系列**：  
  - **I2** 增补 `PolicyAssembler + Pacing Contract`；  
  - **I3** 增补 `pace_deviation / subplot_reveal_deviation` 评分字段。  
- 结论：节奏快慢由章节目标窗口决定，角色活动与暗线显露都受预算约束，并纳入自我迭代闭环（Critic/PolicyUpdater）。

### 2026-04-13（再续）· I1 PolicyStore 最小实现（代码）

- 新增 `src/author_harness/policy_store.py`：  
  - `PolicyStoreConfig`（版本 + 四层规则：global/novel/phase/intent）；  
  - `load_policy_store_from_runtime`（支持 `runtime.author_harness.policy_store` 与兼容路径 `runtime.policy_store`）；  
  - `resolve_rules`（按 global→novel→phase→intent 叠加，去重保序）。  
- `src/author_harness/__init__.py` 导出 `PolicyStoreConfig` 与 `load_policy_store_from_runtime`。  
- 新增单测 `tests/unit/test_policy_store.py`（默认空配置、加载路径、分层合并与去重）。  
- `config/novel_writing.yaml` 增加 I1 配置示例注释（默认不改变现有行为）。  
- 验证：`.venv/Scripts/python -m pytest tests/unit/test_policy_store.py tests/unit/test_author_harness_package.py -q` 通过。

### 2026-04-13（四续）· I2 PolicyAssembler + Pacing Contract 最小链路

- 新增 `src/author_harness/policy_assembler.py`：  
  - `PacingContract` 数据结构；  
  - `resolve_pacing_contract`（默认 `balanced`，支持动态调速与章节目标窗口推断）；  
  - `assemble_pacing_prompt_block` / `assemble_policy_prompt_block`。  
- `turn_planning` 接入最小链路：  
  - `build_turn_plan_prompt` / `build_turn_body_prompt` 支持注入 `pacing_prompt_block`；  
  - `generate_turn_plan` / `generate_turn_body` 在运行时生成并注入节奏约束块；  
  - 新增可选参数 `chapter_goal`、`requested_pace_mode`（保持向后兼容）。  
- `PolicyStore` 扩展：  
  - 增加 `default_pace_mode`（默认 `balanced`）与 `allow_dynamic_pace_adjust`；  
  - 增加 `resolve_pace_mode`。  
- 单测新增：`test_policy_assembler.py`、`test_turn_planning_pacing.py`，并扩展 `test_policy_store.py`。  
- 验证：`.venv/Scripts/python -m pytest tests/unit/test_policy_store.py tests/unit/test_policy_assembler.py tests/unit/test_turn_planning_pacing.py tests/unit/test_author_harness_package.py -q` 通过。

### 2026-04-13（五续）· I3 Critic 最小实现（代码）

- 目标：先落地**规则评分版 Critic**，不引入额外 LLM 调用；把节奏偏差与暗线越级偏差接到正文生成日志。
- 代码：
  - 新增 `src/author_harness/critic.py`：
    - `CriticScore` 数据结构；
    - `evaluate_body_against_pacing(contract, body)`，按 `goal_window` 做最小规则评分，输出：
      - `pace_deviation`
      - `subplot_reveal_deviation`
      - `reason`
  - `src/author_loop/turn_planning.py`：
    - 在 `generate_turn_body` 生成正文后调用 Critic；
    - 记录结构化日志：`pace_deviation` / `subplot_reveal_deviation` / `reason` / `goal_window` / `pace_mode`。
  - `src/author_harness/__init__.py` 导出 Critic 对外接口。
- 测试：
  - 新增 `tests/unit/test_critic.py`（覆盖铺垫窗口越级揭示、推进窗口常规推进）。
  - 回归执行：`tests/unit/test_critic.py`、`tests/unit/test_policy_assembler.py`、`tests/unit/test_turn_planning_pacing.py` 通过。
- 结论：I3 最小链路已具备可观测评分能力；下一步进入 I4（candidate patch + gate）。

### 2026-04-13（六续）· I4 文档闸细化（I4a/I4b）

- 对齐 `docs/design/author-agent-harness.md`：
  - 在 §4.3 明确 `candidate_patch` 最小字段：`patch_id/scope/target/operation/content/evidence/risk_level/manual_review_required`；
  - 明确 `Gate` 最小校验项：schema、作用域白名单、操作白名单、证据完整性、核心规则保护。
- 对齐 `docs/planning/next-iteration.md`：
  - I4 验收改为 `I4a（PolicyUpdater 产出）+ I4b（Gate 校验）`；
  - 下一步优先从 “I3” 更新为 “I4”；
  - 明确约束：建议模式，不自动生效。
- 下一步代码落地：
  1. 新增 `policy_updater.py`（先规则驱动 candidate patch）；
  2. 新增 `policy_gate.py`（基础门禁校验）；
  3. 补单测并导出接口。

### 2026-04-13（七续）· I4 PolicyUpdater + Gate 最小实现（代码）

- 目标：落地 I4a/I4b，先建立候选补丁与门禁校验能力，保持“建议模式，不自动生效”。
- 代码：
  - 新增 `src/author_harness/policy_updater.py`：
    - `PolicyCandidatePatch` 数据结构；
    - `build_candidate_patch(...)`：基于 Critic 分数生成 `candidate_patch`，包含 `scope/operation/evidence/risk_level/manual_review_required`。
  - 新增 `src/author_harness/policy_gate.py`：
    - `GateResult` 数据结构；
    - `validate_candidate_patch(...)`：执行 schema、作用域白名单、操作白名单、证据完整性、核心规则保护校验。
  - `src/author_harness/__init__.py` 导出 I4 新接口。
- 测试：
  - 新增 `tests/unit/test_policy_updater_gate.py`，覆盖：
    - 高偏差场景 candidate patch 产出；
    - 合法 patch 通过 gate；
    - 非法 scope 与证据缺失被拒绝。
  - 回归执行：`test_policy_updater_gate.py` + `test_critic.py` + `test_author_harness_package.py` 通过。
- 结论：I4 最小链路完成；下一步聚焦 I5 前置（配额/超时/信任级与日志字段）与受控联网接线方案。

---

## 2026-03-29（排期与工作日志同步）

- **next-iteration.md**：「下一步优先（执行版）」标题与 [`WORKLOG.md`](./WORKLOG.md) 速览日期对齐；**R7b–R7d** 仍为已完成，编码下一步为 **R7e（可选）** 与 **R8**（可观测 + pytest 链），并行 **MVP-1b/2**、任务 E、小说级路径等（见该文 **当前焦点** / **待办**）。  
- **dev_agent/output/next_plan.md**：下一步表与 SSOT 互链日期同步。  
- **TECH_IMPLEMENTATION.md §6.0**：R7 表述与 **R7b–R8 ✅** 一致（见下节 **Harness R7e / R8（续）**）。

### Harness R7e / R8（续）

- **`cli.review_memory_plan`**：`PHASE_MEMORY_PLAN_REVIEW`、`memory_plan_action`（confirm / reject / supplement / edit / edit_fallback）；每轮打印 `scope_id`、时间与地点。  
- **`cli.review_turn_result`**（传 **storage** 时）：每轮 **`[作者在环] phase=MAIN_WRITING_REVIEW`** 行含 `intent_id`、`intent_cli`、`retrieval_sources`、`retrieval_chars`；**`apply_main_writing_review_ingress` 改为函数内 import**，避免 `author_loop` 包初始化与 `author_harness` 环状依赖。  
- **单测**：`test_apply_main_writing_review_ingress_revise` 扩展为 **R8** 链（`scope_events:` + `author_interaction_state` 源 + 组装块关键字）。

### 大纲 MVP-1b（章节大纲 → outline.yaml）

- **`outline_store`**：`extract_chapter_outline_from_setting`、`outline_dict_from_setting_chapter_outline`、`materialize_outline_from_setting_research`（写入 `book/outline/outline.yaml`，可选 `progress.yaml`；`overwrite` 控制覆盖）。  
- **单测**：`test_outline_store` 新增映射、落盘与「已存在则跳过」。  
- **文档**：`outline-mvp-plan.md` §4.5、`next-iteration` 当前焦点。

### D8 上下文压缩（自适应分层任务锚定，SDD）

- **新增** [`docs/design/context-compression-adaptive-layered.md`](docs/design/context-compression-adaptive-layered.md)：Compression Contract、软原型与自适应修正、与 `retrieve_for_intent` 硬截断的关系、门限 0.75×cap、落地阶段 **CC-a～CC-d**。  
- **登记表** [`SPEC_SDD.md`](docs/framework/SPEC_SDD.md) **D8**；[`docs/README.md`](docs/README.md) `design/` 表；[`author-agent-harness.md`](docs/design/author-agent-harness.md) §4.1 表后互链；[`TECH_IMPLEMENTATION.md`](TECH_IMPLEMENTATION.md) §6.0 索引。  
- **排期**：[`next-iteration.md`](docs/planning/next-iteration.md) 当前焦点第 5 条、待办 **上下文压缩**、已完成文档闸；编码 **CC-b** 起未做。

---

## 2026-04-10

### 任务规划与产品路线同步（文档）

- **SPEC_SDD**：登记表新增 **D7** [`novel-assistant-pm-agent-model.md`](docs/design/novel-assistant-pm-agent-model.md)；§2.1 互链 **P0–P4** 与 `next-iteration`。  
- **D7**：新增 **§10.3** 与工程排期互链（`next-iteration`「产品级路线」、`author-agent-harness` **R7**）。  
- **next-iteration.md**：新增 **「产品级路线」**（**P0** ✅～**P4** 冻结）；**当前焦点** 第 4 条；**进行中** 增加 D7 与 Harness 并行说明；**待办** 重写 DevAgent、联网与 **P2/P3/P4** 对齐；**作者在环后续** 增加 P1–P4 指针；**下一步优先** 与 2026-04-10 规划对齐（见该节标题）。  
- **WORKLOG 速览**：与上同步。  
- **排期原则**：**Harness R7** + **大纲 MVP** 仍为近期工程主线；**P1–P4** 按需插入、默认不阻塞 R7。

### 下一步（执行）

1. **编码**：**R7e/R8**（阶段二可观测、审阅 pytest 链）；R7b–R7d 已完成。  
2. **并行**：**MVP-1b / MVP-2**、任务 E、小说级路径、成长状态机 MVP、连续超时降级（见 `next-iteration` 待办）。  
3. **产品**：**P1–P4** 任一项立项前按 doc-first 修订 D7 / S2 / TECH（见 **产品级路线**）。

### Harness R7b（正篇审阅分类）

- **`classify_intent`**：支持 **`phase=MAIN_WRITING_REVIEW`**，稳定 **`review_*` intent_id**、`retrieval_query`（修订意图下为作者原句）；可选 LLM 分类（与设定主菜单同 **`intent_classify_llm`** 闸）。  
- **`understand_author_review_intent`**：委托 **`classify_intent`** + **`main_review_intent_to_cli_action`**，与历史 **y/n/e/s/自由文本** 行为对拍（单测 `test_main_writing_review_rules_match_legacy_review_intent`）。  
- **集成测试**：`test_apply_event_and_state_write_then_apply_memory_write` 中 **`get_recent_events(..., k=20)`** 在事件已满窗口时易假失败，改为 **`k=500`**。

### Harness R7c（审阅检索链）

- **`retrieval_registry`**：`INTENT_REVIEW_REVISE` → **`scope_recent_events`** + **`author_interaction_state`**。  
- **`retrieve_for_intent`**：新增可选 **`storage`**、**`scope_id`**；**`review_revise`** 时拉 **最近范围事件摘要**（`format_scope_events_snippet`）与 **digest**；缺 storage 时仅 digest。单测 **`test_retrieve_review_revise_*`**。

### Harness R7d（审阅委托 + 修订注入）

- **`apply_main_writing_review_ingress`**：`MAIN_WRITING_REVIEW` 分类；**`review_revise`** 时检索并组装块。  
- **`review_turn_result`**：传入 **config_dir / project_root / storage** 时走 Harness；否则旧路径（单测）。  
- **`revise_body_by_feedback(..., assembled_context=...)`**；**`run_novel_with_author`** 已传 **storage**。单测 **`test_apply_main_writing_review_ingress_revise`**。

### 远期完善占位（文档）

- [`next-iteration.md`](docs/planning/next-iteration.md) 新增 **「远期完善与优化」**：**U-1～U-5**（近期主线后可启动）；**每条**须交付或更新统一的 **「检索完整方案」**（六要素：范围、链路、能力矩阵、治理、规约映射、验收）；**本节不展开技术细则**。

---

## 2026-04-09

### R7 文档闸（R7a，无代码）

- **S2** [author-in-loop-spec.md](docs/specs/author-in-loop-spec.md)：新增 **§3.4** 正篇回合审阅目标态（SHOULD + 不得破坏两阶段审阅）；§6 映射 **D6 §6.3**。  
- **D6** [author-agent-harness.md](docs/design/author-agent-harness.md)：新增 **§6.3**（现状表、目标态、风险、**R7a–R7e** 子切片）；§6.1 表 **R7/R8** 备注更新。  
- **next-iteration.md**：**R7 子步表**（R7a ✅）；**SPEC_SDD §2.1** 增 R7 指针；**TECH §6.0** 增 R7 规划一句。  
- **下一步编码**：**R7b**（审阅 phase + 分类）→ **R7c**（检索）→ **R7d**（Harness + `review_turn_result` + `revise_body_by_feedback`）→ 可选 **R7e**。

### Harness R6（代码）

- **`src/author_harness/author_harness.py`**：`apply_design_main_menu_ingress`、`AuthorHarness`、`DesignMainMenuHarnessResult`；主菜单 **classify → retrieve → assemble → session.extra** 从 `design_phase` 迁入。  
- **`author_loop/__init__.py`**：不再在包初始化时 import **`design_phase`**；对 **`run_design_phase`** 使用 **`__getattr__` 懒加载**，避免 `author_harness → retrieve_for_intent → author_loop 包 → design_phase → author_harness` 环状依赖。  
- **单测**：`test_author_harness_design_main.py`；`test_author_harness_package` 断言新导出。

---

## 2026-04-08

### Harness R4（代码）

- **`src/author_harness/retrieval_registry.py`**：`INTENT_RETRIEVAL_TOOL_CHAINS` 与稳定工具名常量。  
- **`retrieve_for_intent`**：解析 `retrieval_query` 为 token（过滤单字母拉丁菜单键误命中）；对设定类与 `save_progress` 两路在**首轮采样后**按命中得分 **加权重分预算** 再拉取；`logger.debug` 记录 tokens / scores / budgets。  
- **单测**：`test_intent_retrieval_tool_registry_matches_design_main`、`test_retrieval_query_boosts_matching_snippet_length`。  
- **`author_harness.__init__`** 导出 `INTENT_RETRIEVAL_TOOL_CHAINS`。

### Harness R5（代码）

- **`classify_intent`**：`phase == DESIGN_DISCUSSION` 时固定 **`input_idea_discuss`** + `retrieval_query`（与主菜单共用 M4 工具链）。  
- **`design_phase._assembled_context_for_discussion`**：每轮讨论前拉片段并写 **`session.extra["intent_retrieval"]`**。  
- **`discuss_freely`**：可选 **`assembled_context`**，提示词中注入「已落盘检索片段」。  
- **`retrieve_for_intent`**：`bk is None` 且 query 加权重建时 **`out`** 用 `if x` 过滤，避免 **`None`** 进 `_enforce_total_budget`。

---

## 2026-04-07

### Harness R1 / R2（代码）

- **R1**：新增包 **`src/author_harness/`**（`__init__.py` 导出 Assembler 入口）。  
- **R2**：**`prompt_assembler.assemble_retrieval_prompt_block`** — 委托 `retrieve_for_intent.format_snippets_for_prompt`，单测与 M4 对拍。  
- **文档**：`author-agent-harness.md` §6 / §6.1、`next-iteration.md` R 表、`TECH_IMPLEMENTATION` §6.0。

### Harness R3（代码）

- **`design_phase`**：主菜单分支写 **`session.extra["intent_retrieval"]`** 改为 **`assemble_retrieval_prompt_block(_snippets)`**，不再直接调用 `format_snippets_for_prompt`。行为与 R2 对拍一致。  
- **文档**：`author-agent-harness.md`、`next-iteration.md` R3 勾选。

---

## 2026-04-06

### Spec / SDD 是否满足迭代开发诉求（结论）

| 维度 | 结论 |
|------|------|
| **分层** | L0/L1（DESIGN、TECH、**S2**）与 L2（**D6** Harness、**D1** 状态机）分工明确；登记表见 **SPEC_SDD §3**。 |
| **可切片交付** | **H1–H4** 已有迁移方向；本次增补 **§6.1 R0–R8**，将「文档闸、空壳、Assembler 单测、主菜单接线、c 子流程、审阅、观测」拆开，便于小 PR 与回归。 |
| **迭代顺序** | **S2 §1.1** + **SPEC_SDD §2.1** + **`guides/development.md` §七** 固定「先文档/方案、后代码」；Cursor **`.cursor/rules/doc-first-spec-sdd.mdc`**（`alwaysApply: true`）约束助手默认遵守。 |
| **待编码项跟踪** | **next-iteration** 已挂 **R\*** 表与「进行中」Harness 段落互链；后续每完成一 R，勾选并必要时回写 D6「与代码映射」。 |

### 本轮文档变更摘要

- 新增 **`.cursor/rules/doc-first-spec-sdd.mdc`**。  
- **author-in-loop-spec.md**：§1.1 迭代开发与文档先行。  
- **author-agent-harness.md**：§6.1 R0–R8。  
- **SPEC_SDD.md**：§2.1；修订记录。  
- **next-iteration.md**：R0–R8 表；进行中段落互链 SPEC_SDD / S2。  
- **specs/README.md**、**guides/development.md** §七、本 **WORKLOG** 速览与本节。

**下一步（实现）**：从 **R0**（若未做）或 **R1** 起按表推进；任何跨 R 合并须显式评审。

---

## 当前主程序分析（按最新代码）

### 入口与流程

| 入口 | 用途 | 主流程 |
|------|------|--------|
| **run_novel_with_author.py** | 小说主流程（作者在环） | 1) setup_logging → Orchestrator.from_config（若 **data_root** 则从磁盘 **load_scope_events** 注入 storage）。**启动**：**print_startup_resume**——若 `setting_research.trigger=design_only` 则打印上次设定会话摘要；打印**最近 N 回合**（**MIN_AUTOBOOK_RECENT_TURNS**，默认 3）范围事件摘要与正文预览；设定改配置重载后再打印一次正文进展。2) 若 **design_only** → **run_design_phase**（**load_session_full**；主菜单 y/e/c/p 等；仅 y 结束）。若曾选 e 则重载编排器。3) n 回合（**MIN_AUTOBOOK_TURNS**）：每回合 **generate_turn_plan_for_turn**（注入 **author_classified_memory** 渐进片段）→ 作者可补充要求 → **classify_author_input** + **append_classified_entries** 落盘 **book/memory/author_classified/** → **run_one_turn(..., auto_write=False)** → **review_turn_result** → **apply_event_and_state_write** → **review_memory_plan** → **apply_memory_write**。选 s 时 **run_supplement_setting_during_turn**。分类列表由 **runtime.author_classified_memory** 配置（见 **novel_writing.yaml** 合并结果，可扩展小说类型专用维度）。 |
| **run_novel.py** | 小说主流程（自动写回） | Orchestrator.from_config → get_initial_scene → **run_n_turns(n, ...)**。每回合 run_one_turn(..., auto_write=True)，仅调用 apply_event_and_state_write（不写记忆）；若配置了 data_root 则同样双写 content/turns、memory/scopes。 |
| **run_dev_agent.py** | DevAgent 自我迭代 | run_once(project_root)：加载 dev_agent 配置 → 执行 test_command（如 pytest）→ 写 latest_run、失败时 failures/suggestions；成功且 search_ideas_enabled 则 **run_search_ideas**（可读 setting_research_output_path 或调设定研究产出 power_system.md、level_system.md）→ 写 cursor_tasks（含 next_plan 与 search_ideas 条目）。 |

**作者在环增量（2026-03-29，§13 M3–M6）**：`run_novel_with_author.main(input_fn=…)`；**`design_only`** 内书名 **`confirm_title_and_persist(..., input_fn=session.read_line)`** 与正篇回合 **同 `AuthorSession`**；设定 **`run_design_phase`** 主菜单经 **`classify_intent` → `design_main_menu_key`**，**`retrieve_for_intent`** 写入 **`session.extra["intent_retrieval"]`**；轮次摘要 **`record_round_digest`** 可选经 **`digest_compress_llm`** 压缩。详情见 **`WORKLOG`「2026-03-29（续）」** 与 **`docs/design/author-interaction.md`** §13。

### 关键依赖与配置

- **配置目录**：默认 `config/`；运行时由 **system_config** → **example_runtime（可选，缺失则用内置 DEFAULT_RUNTIME_NOVEL）** → **novel_writing**（并入 `runtime`）合并，绑定 **current_novel** 后再叠加小说目录 `config/runtime.yaml`；全局 **example_world / example_characters** 为未绑小说时的最小占位。**设定研究 YAML**：已绑定小说时为 `<novel_root>/config/setting_research_output.yaml`；未绑定时仅 `load_special_settings_config` 可读全局 **example_special_settings.yaml**（不读全局 setting_research_output，避免串本）。详见 WORKLOG「2026-03-29 · 设定研究产出路径与作者在环统一方案」。
- **编排器**：from_config 创建 MemoryStorage、CharacterAgent（含 storage/runtime_config/characters_config）、ScopeAgent（含 storage/runtime_config/world_config）；若 runtime.storage.data_root 存在则设置 _data_root，写回时触发 file_sync。
- **设定阶段**：design_phase 启动时 load_session_full 恢复会话；使用 SettingResearchAgent.run()、discuss_freely、summarize_and_extract_by_directions；主菜单 y/e/c/p（c 输入想法或继续上次讨论，多轮后归纳；p 保存进度）；**世界名等基础未齐时禁止用 y/默认路径结束**，须先 c 讨论或 e 编辑；讨论提示与 `discuss_freely` 优先「可归档设定 + **章节大纲**」，少滑向写作课式成篇分析；设计会话持久化至 config/design_session.yaml + book/setting/session_*.md 与 .yaml，仅 y 设定完成才进入正篇。
- **双写**：apply_event_and_state_write 内 next_turn_index、write_turn_content、sync_scope_turn、ensure_memory_root_readmes；apply_memory_write 内 sync_character_turn（同一 _last_turn_index）。
- **大纲（MVP-0 + MVP-1 注入）**：`src/runtime/outline_store.py`（`load_outline_snapshot`、`resolve_current_beat`、`build_outline_prompt_snippet`、`outline_injection_options`）；`src/runtime/protagonist.py`（`resolve_protagonist_id`）；存在 `book/outline/outline.yaml` 时启动 `[大纲]` INFO，**每回合** `[大纲进度]` + 将节拍/主角注入 **写作前分析** 与 **正文** prompt（`runtime.outline.enabled` 可关）；示例见 `docs/examples/outline.yaml`。
- **作者在环归类记忆**：`src/author_loop/author_classified_memory.py` — **get_author_classified_spec** 读取 `runtime.author_classified_memory`（默认内置 5 类 + 可选扩展，或 `include_defaults: false` 全自定义）；作者补充要求经 **classify_author_input** 写入 `book/memory/author_classified/{id}/entries.md`；**progressive_author_memory_for_plan** 拼索引 → LLM 选 **ordered_categories** → 注入 **turn_planning.build_turn_plan_prompt**。**book/README.md** 列出含 `memory/author_classified`。

---

## 2026-03-29

### 新小说初稿目录与全局配置减负

**背景**：此前新小说引导会向全局 `config/example_world.yaml`、`example_characters.yaml` 写骨架，与「作品进小说目录」不一致；`config/example_runtime.yaml` 作为必填入口易与旧项目模板混淆。

**实现要点**

| 项 | 说明 |
|----|------|
| **初稿目录** | 无设定、无正文、且无 `current_novel` 时，`novel_identity.ensure_provisional_novel_directory` 创建 `data/novels/draft-<时间戳>/`，书名 **（初稿）待命名**，`meta.status=draft`，并写入小说级 `config/{world,characters,runtime}.yaml` 与 `config/current_novel.yaml`（`provisional: true`）。 |
| **不再写全局 world/characters** | `novel_bootstrap.prepare_new_novel_if_needed` 不再创建全局 `example_world.yaml` / `example_characters.yaml`。 |
| **书名终态** | `is_provisional_novel`；设定完成后 `confirm_title_and_persist` 仍进入命名；`persist_novel_identity` 对 draft 做目录重命名（若 slug 变）、`meta.status=design_done`、`current_novel.provisional=false`。 |
| **运行时入口** | 删除仓库内 **example_runtime.yaml**；`load_runtime_config` 在文件缺失时使用 **`DEFAULT_RUNTIME_NOVEL`**（占位 `main` / `protagonist`）。全局保留最小 **example_world.yaml**、**example_characters.yaml**（与上述 id 一致），供未绑小说时 `validate_runtime_and_ids` 通过。 |
| **文档与测试** | `README.md`、`docs/guides/usage.md`；`tests/unit/test_config.py`（含无 example_runtime 用例）、`test_dev_agent_config`、`test_novel_bootstrap`、`test_novel_identity`。 |

**下一步（与初稿同日后续）**：见下方「设定研究产出路径与作者在环统一方案」及 `docs/planning/next-iteration.md`。

### docs 子目录与内链（术语化命名）

**要点**：`docs/design/`（专题设计）、`docs/planning/`（迭代清单 `next-iteration.md`、大纲 MVP `outline-mvp-plan.md`）、`docs/guides/`（使用/开发/Cursor 协同等）、`docs/specs/`（L0/L1 索引）、`docs/framework/`（SPEC/SDD）。根目录 `DESIGN.md`、`TECH_IMPLEMENTATION.md` 仍为 L0/L1 SSOT；文内相对链接与部分历史条目中的旧文件名已对齐到新路径。

### 设定研究产出路径与作者在环统一方案（本阶段代码 + 文档）

**背景**：`setting_research_output.yaml` 不应长期放在全局 `config/`，应与 world/characters 一致落在**当前作品目录**；未绑定作品时不应在配置层静默混用他书产物。与作者沟通上，希望缺作品时走**程序引导**而非手写 YAML（长期由统一交互架构承接）。

**代码与行为**

| 项 | 说明 |
|----|------|
| **`special_settings_config_dir`** | 仅当存在有效 `current_novel.root` 时返回 `<novel_root>/config`；否则 **`RuntimeError`**，文案强调须通过主流程完成「创建/选择作品」交互，勿手写配置。 |
| **`load_special_settings_config`** | 有小说时只读小说下 `setting_research_output.yaml`；否则只读全局 `example_special_settings.yaml`（**不**读全局 `setting_research_output.yaml`）。 |
| **`design_phase` / `SettingResearchAgent`** | 产出与写回均使用 `special_settings_config_dir`；绑定小说提示中区分「小说 config」与全局示例。 |
| **`novel_bootstrap._has_setting`** | 仅以**小说目录**下 `config/setting_research_output.yaml` 判定已有设定；全局该文件视为废弃路径，**不**再阻止新小说引导。 |
| **`.gitignore`** | `**/setting_research_output.yaml`（全局与小说下产出均忽略）。 |
| **单测** | `test_special_settings_config_dir.py`；`test_design_phase` 用 `_ensure_bound_novel`；`test_novel_bootstrap` 中「仅全局 setting 文件」改为期望仍触发引导（`test_prepare_new_novel_ignores_obsolete_global_setting_yaml`）。 |

**新方案文档（尚未改主循环，仅设计 SSOT）**

| 文档 | 内容 |
|------|------|
| **`docs/design/author-interaction.md`** | 作者在环**统一入口**、**状态机**、**入口 LLM 分类**、**`last_round_digest`（轮次摘要，非全量历史）**、**分类后按需检索**、Handler 与提示词外置、迁移路线 M1–M6。 |
| **`docs/planning/next-iteration.md`** | 「进行中」已挂本专题与文档链接。 |
| **`TECH_IMPLEMENTATION.md`** | 第六章首段互链至上述专题文档。 |

**优劣与风险**

- **优点**：作品级设定文件与数据目录一致；引导与初稿 `draft-*` 链路对齐；大改交互前有可评审的专题文档。  
- **风险**：若用户在无 `current_novel` 时仍进入 `run_design_phase`，会直接抛错；**下一步**应通过调整主流程顺序（先绑定/初稿再设定）或统一交互门闩（见专题 §11、§13 M2/M3）消除。

**本阶段下一步（实现优先序）**（2026-03-29 末刷新；**当前以页首速览为准**）

1. ~~**流程**~~：**已实现** — `run_novel_with_author` 在 `run_design_phase` 前调用 **`ensure_current_novel_for_design_phase`**（`src/author_loop/novel_bootstrap.py`）：先 `prepare_new_novel_if_needed`；仍无有效 `root` 时，若无 `current_novel` 指针且非「已有正文无指针」，则用当前编排器 world/characters 创建初稿；失败则 `sys.exit(1)`。单测见 `tests/unit/test_ensure_novel_for_design.py`。  
2. ~~**架构 M1–M6**~~：**已实现** — 详见下方「2026-03-29（续）」。后续侧重 **正文阶段意图/检索与 Handler 深接**、**digest 压缩 token 硬约束（可选）**、关系图谱是否接入 `retrieve_for_intent`（收尾优化轮再议）。  
3. ~~**大纲 MVP-1**~~：**已实现**；**并行**仍以 **MVP-1b / MVP-2**、任务 E、成长状态机 MVP、LLM 超时降级为主 — 见 `docs/planning/next-iteration.md` 与页首 **速览**。

---

## 2026-03-29（续）· 作者在环专题 §13 M3–M6 与主流程读入统一

**背景**：`docs/design/author-interaction.md` §13 分阶段；M1–M2 已先行，`classify_intent` / `retrieve_for_intent` / 主流程裸 `input` 吞并及 digest 与文档对齐在本轮闭合。

### 实现摘要

| 项 | 说明 |
|----|------|
| **M3** | `src/author_loop/classify_intent.py`：设定主菜单 **DESIGN_MAIN** 白名单 + LLM（可 `intent_classify_llm: false` 纯规则）；`design_phase` 用 `design_main_menu_key` 分支；单测 `test_classify_intent.py`。 |
| **M4** | `src/author_loop/retrieve_for_intent.py`：设定类（讨论/编辑）与 **save_progress** 两路文件型快照；预算 `retrieve_max_total_chars`；`design_phase` 结果进 `AuthorSession.extra["intent_retrieval"]`；单测 `test_retrieve_for_intent.py`。 |
| **M5** | `AuthorSession.for_main_loop`；`run_novel_with_author.main(input_fn=…)` 回合内凡阻塞读入均 **`read_line`**；`review_turn_result` / `review_memory_plan` / `run_supplement_setting_during_turn` 同链；**书名确认** `confirm_title_and_persist(..., input_fn=session.read_line)`，编排器重载后 **`author_session.runtime_config = runtime`**；修正了驳回重试分支里 `append_classified_entries` 缩进。单测 `test_author_session`。 |
| **M6 与 digest** | **已并入 M2 链路**：`digest_compress_llm.compress_round_digest_fields` ← `record_round_digest`；`digest_llm_compress` 默认 true；Dummy/失败/关闭则原文落盘；单测 `test_digest_compress_llm.py`。路线图文档已与代码对齐。 |

### `run_novel_with_author` 行为补充（相对本页表「入口与流程」）

- **design_only** 路径内在 **`confirm_title_and_persist` 前**创建 **`AuthorSession.for_main_loop`**，书名与后续回合**同一会话**（含可选 **`input_fn`** 注入）。
- **设定主菜单**：在既有 y/e/c/p 上增加 **意图分类 + 检索片段**（供后续扩展注入 Agent；当前不改变核心分支语义）。

### 配置与文档

- `config/novel_writing.yaml`：`intent_classify_llm`、`retrieve_max_total_chars`、`digest_llm_compress` 等注释示例。
- `docs/planning/next-iteration.md`、`docs/design/author-interaction.md` §13：M1–M6 状态与**下一步优先**已刷新。

### 下一步（执行向，历史记录）

与页首 **速览** 中「当前优先」一致；当时成文时 MVP-1 尚未全部合入，故下列「产品向」中 MVP-1 已达成。

1. **产品向**：~~大纲 MVP-1~~（已实现）；**MVP-1b / MVP-2**（章节大纲与 `outline.yaml` 对齐、`progress.yaml`）。  
2. **工程向**：任务 E（初稿→终态书名 E2E）、小说级路径收口、成长状态机 MVP、`run_novel_with_author` LLM 连续超时降级。  
3. **作者在环深化（可选）**：将 `session.extra["intent_retrieval"]` 接入 **Handler/提示词**；`MAIN_WRITING` 阶段 **classify_intent** 与白名单扩展；M6 可选 **digest** 输出长度硬限。

---

## 2026-03-29（再续）· 设定阶段门闩、初稿交互与「设定 vs 写作课」

### 背景

运行中常见两类问题：**世界名仍空却想直接 y 进入正篇**；设定讨论里模型偏向**修辞/开场/成篇分析**，偏离「先把规则与大纲钉死」。另需把**全书或分章剧情骨架**明确纳入设定产物，并与后续 `book/outline/`（MVP）衔接思路一致。

### 实现摘要

| 项 | 说明 |
|----|------|
| **结束门闩** | `_design_exit_blocked_by_incomplete_world`：若 `world.name` 等仍为空，拦截主菜单 **y** 与「其他输入当作确认」；提示须 **c** 讨论或 **e** 编辑；默认菜单项倾向 **c**；被拒后 **`skip_agent_after_menu_block`**，避免同一轮重复 `agent.run()` 刷 LLM。 |
| **初稿前题材** | `_prompt_author_intent_for_setting_research`：世界名为空时先收类型/核心说明，再结合 `_build_setting_prompt` 的**非玄幻勿默认修仙境界**约束生成初稿。 |
| **正文存在但未绑作品** | `novel_bootstrap.interactive_resolve_novel_for_design_phase` 等；`run_novel_with_author` 在 `ensure_current_novel_for_design_phase` 失败时可交互新建初稿或绑定路径；单测 `test_ensure_novel_for_design.py`。 |
| **自由讨论聚焦** | `discuss_freely` / `discuss_direction`：强调**可写入设定档**的内容（规则、势力、体系、**章节级骨架**），**少谈**句式/镜头/润色；作者聊人物桥段时**收敛为设定条款**。子循环 `read_line` 提示同步简短强调。 |
| **章节大纲入设定** | `_build_setting_prompt` 可选 **`章节大纲`**（`chapters` 每章一句功能，非正文）；`summarize_and_extract_by_directions` 明确 **章节大纲** 为可归纳方向；`_generate_with_llm_if_available` **保留**除 power/level 外的顶层键；`DIRECTION_LABELS`；`_format_special_summary` / `_direction_to_md` 展示章节列表。 |
| **单测** | `test_design_exit_blocked_when_world_name_empty`、`test_collect_setting_intent_updates_genre_and_reference`、`test_format_special_summary_includes_chapter_outline`、`test_direction_to_md_renders_chapters`；`design_phase` 运行时关 `intent_classify_llm` / `digest_llm_compress` 防卡住。 |

### 下一步（历史记录；以页首速览与 next-iteration 为准）

1. **MVP-1b**：将设定阶段的 **`章节大纲`** 与 `outline_store` / `book/outline/outline.yaml` **对齐或一次性导入**（避免双源长期漂移）。MVP-1 核心注入已完成。  
2. **任务 E**、小说级路径收口、LLM 超时降级等见 `docs/planning/next-iteration.md`。

---

## 2026-03-29（大纲 MVP）· 三阶段执行方案定稿

### 背景

原 **[outline-and-beats.md](./docs/design/outline-and-beats.md)** §8 仅表格级描述 MVP-0/1/2，缺少 **SSOT**、`outline_store` / `turn_planning` / 主流程的 **具体接入点** 与 **验收清单**。

### 文档与计划

| 文档 | 内容 |
|------|------|
| **[docs/planning/outline-mvp-plan.md](./docs/planning/outline-mvp-plan.md)** | **MVP-0**：维持已实现结论与回归验收。**MVP-1**：主角配置、`resolve_current_beat` / `format_outline_snippet_for_prompt`、`build_turn_plan_prompt`/`build_turn_body_prompt`/`generate_turn_plan_for_turn` 扩展、`run_novel_with_author` 传快照；**SSOT** 约定（`book/outline/outline.yaml` 为主，设定 **`章节大纲`** 经一次性导入对齐）；可选 **MVP-1b** 从设定生成首版 outline。**MVP-2**：进度 INFO、作者在环推进 **`progress.yaml`**、重启可读；MVP-2 优先不批量改 `outline.yaml` 整树。 |
| **outline-and-beats.md §8** | 增加与 `outline-mvp-plan.md` 互链。 |
| **docs/planning/next-iteration.md** | 「下一步优先」改为显式引用该执行方案。 |

### 实现状态

- **MVP-0**：代码与示例已具备；方案中归纳了验收口径。  
- **MVP-1（核心注入）**：**已实现** — 见下节「大纲 MVP-1」。  
- **MVP-1b / MVP-2**：**未编码**（设定章节大纲 → outline 导入；作者在环写回 `progress.yaml`）。

---

## 2026-03-29 · 大纲 MVP-1（节拍与主角注入 prompt）

### 摘要

| 模块 | 说明 |
|------|------|
| **`outline_store`** | `BeatContext`、`resolve_current_beat`、`format_outline_snippet_for_prompt`、`build_outline_prompt_snippet`；`runtime.outline.enabled`（默认 true）、`soft_max_turns_per_beat`（默认 3）。 |
| **`protagonist`** | `resolve_protagonist_id(runtime, characters_config)`：`novel_run.protagonist_id` 或唯一 `is_protagonist`。 |
| **`turn_planning`** | `build_turn_plan_prompt` / `build_turn_body_prompt` / `generate_turn_plan_for_turn` / `generate_turn_body` 增加 `outline_snippet`。 |
| **`run_novel_with_author`** | 每回合 `load_outline_snapshot` + `build_outline_prompt_snippet`；`[叙事主角]` 启动 INFO；`[大纲进度]` 每回合 INFO。 |
| **默认配置** | `DEFAULT_RUNTIME_NOVEL.novel_run.protagonist_id: protagonist`；`config/example_characters.yaml` 主角条目标 `is_protagonist: true`。 |
| **单测** | `test_outline_store`（节拍解析、禁用注入、`build_turn_plan_prompt` 含大纲块）；`test_protagonist`。 |

**未做**：MVP-1b（设定 `章节大纲` 生成 outline）；MVP-2（确认后更新 `progress.yaml`）。

---

## 2026-03-29 · docs 文档体系（Spec + SDD）

- 新增 **[docs/README.md](./docs/README.md)**：文档中心总索引（按角色入口、按类型目录表）。
- 新增 **[docs/framework/SPEC_SDD.md](./docs/framework/SPEC_SDD.md)**：L0–L4 分层、规约/SDD 登记表、SDD 式开发流程（Mermaid）、AI 引用顺序与反模式；**[docs/framework/README.md](./docs/framework/README.md)** 为目录说明。
- **互链**：[README.md](./README.md)、[TECH_IMPLEMENTATION.md](./TECH_IMPLEMENTATION.md) §一、[docs/guides/development.md](./docs/guides/development.md) §六、[docs/planning/next-iteration.md](./docs/planning/next-iteration.md) 首段。

---

## 2026-03-28

### 大纲、章节骨架与多线叙事（方案定稿）

**文档**：`docs/design/outline-and-beats.md`

**已定原则**

- **节拍 ↔ 回合**：1 节拍可跨多回合；单节拍建议 **少于 3 回合**（软提示，不强制关闸）；完成节拍以**作者在环**为主。
- **大纲与章**：全书 / 章 / 节拍为**主线指导**，不限死死节奏；与「画卷徐徐展开」的小颗粒回合兼容。
- **正文**：以**主角主线**为叙事主轴；其他角色独立活动仅在主书中以**必要摘要**推动剧情。
- **系统内多线**：每角色仍为**真·并列主线**——长期独立活动记忆与规则，可随时导出**同世界观番外 / 同文小说**；桥接层只向正文注入摘要，不灌副线全文。

**关联**

- 成长状态机：`docs/design/character-growth-state-machine.md`（叙事语义优先，节拍 `tags` 仅可选提示）。
- 关系图谱：已实现 `book/relationships/graph.yaml` 与回合后同步；大纲方案中说明证据与副线摘要的衔接方向。

**下一步（实现侧）**：见 `docs/planning/next-iteration.md` 待办「大纲与节拍（MVP）」。

### 大纲 MVP-0（已实现）

- **模块**：`src/runtime/outline_store.py`（`outline_yaml_path` / `progress_yaml_path`、`load_outline_snapshot`、`validate_outline` / `validate_progress`）。
- **主流程**：`run_novel_with_author` 在解析 `data_root` 后若存在 `book/outline/outline.yaml` 则 **INFO** 输出一行摘要（含 progress 时带 chapter/beat/turns_in_beat）。
- **示例**：`docs/examples/outline.yaml`、`docs/examples/outline_progress.yaml`。
- **单测**：`tests/unit/test_outline_store.py`。
- **路径约定**：大纲与 `file_sync` / 关系图谱共用 **`runtime.storage.data_root`**，落盘为 `<data_root>/book/outline/`，与当前小说目录下其他 `book/` 内容一致（按书名隔离）；模块与主流程注释已统一，不保留「旧版/旧模式」表述。

### 执行版下一步（2026-03-28 整理）

1. **大纲 MVP-1**：配置显式主角（`protagonist_id` 或 `characters[].is_protagonist`）；`build_turn_plan_prompt` / `generate_turn_body` 注入当前节拍 intent 与主角轴约束。
2. **大纲 MVP-2**：CLI 展示章/节拍进度；作者在环确认后更新 `progress.yaml` / 节拍状态。
3. **并行**：任务 E（新小说 E2E）、小说级路径收口、成长状态机 MVP、`GrowthGuard`、LLM 连续超时降级（见 `docs/planning/next-iteration.md`）。

---

## 2026-02-11（方案讨论记录：新小说初始化与按书名目录隔离）

### 一、需求确认（仅新项目视角）

- 当启动检测到**无设定、无正文**时，判定为“新小说”，系统应**主动进入完整设定交互**，而不是要求先手工填基础运行配置。
- 设定完成后，系统需基于设定生成书名候选，由作者确认；随后按书名创建独立目录，设定/正文/会话均写入该目录。
- 范围约束：**不考虑老项目迁移兼容**；仅保留并兼容全局系统配置（如 `config/system_config.yaml`）。

### 二、目标架构（拟定）

- **全局配置（保留）**：`config/system_config.yaml`（LLM、debug、dev_agent 等系统级参数）。
- **小说级目录（新增）**：`data/novels/<novel_slug>/`
  - `meta.yaml`（title、slug、状态、创建时间）
  - `config/runtime.yaml`、`config/world.yaml`、`config/characters.yaml`
  - `book/`（content/setting/events/characters/memory）
- 启动流程改为“状态判定路由”：新小说 -> 完整设定交互 -> 书名确认 -> 创建目录 -> 写入小说级配置 -> 进入正文。

### 三、实现分层（先方案后编码）

- **阶段 1（MVP）**
  - 新小说判定器：无设定产出 + 无正文事件。
  - 设定完成后书名生成（多候选）+ 作者确认。
  - 创建 `data/novels/<slug>` 并落盘小说级 config/book。
- **阶段 2（增强）**
  - 多小说索引与切换（`data/novels/index.yaml`）。
  - 启动时可选“继续某本/新建一本”。
  - 启动路由提示与状态可视化。

### 三点五、MVP 任务拆分（可直接开工）

- **任务 A（启动路由）**：新增 `bootstrap_or_resume_novel()` + `detect_novel_state()`，在 `run_novel_with_author` 启动最前执行；空项目不再直接走 `load_all_config` 报错。
- **任务 B（书名确认）**：设定阶段完成后追加“书名候选生成与确认”交互，产出 `meta.yaml`。
- **任务 C（目录隔离）**：新增 `data/novels/<slug>/` 目录规范与初始化器；把 `config/world/characters/runtime` 写到小说目录。
- **任务 D（配置加载）**：`src/config` 新增小说目录参数版本加载函数；与 `system_config.yaml` 合并，保持系统级兼容。
- **任务 E（验收）**：新增“空项目首次启动”集成测试，断言会创建小说目录并进入设定交互链路。

### 四、当前结论

- `example_runtime.yaml` 中 `runtime` 基础段（设定研究、作者在环、turn、storage 等）在目标形态下不应要求人工先填；应由初始化交互生成并写入小说级配置。
- 该方案已与作者确认“先写入日志与计划，再进入实现”。

### 五、本轮落地进展（A~D）

- **任务 A 已完成**：`novel_bootstrap.py` 接入启动前检查；无设定+无正文触发新小说引导，自动准备最小配置并强制 `design_only`。
- **任务 B 已完成**：`novel_identity.py` 实现书名候选/确认；写入 `data/.../novels/<slug>/meta.yaml`、`index.yaml` 与 `config/current_novel.yaml`。
- **重试策略收口**：新增 `src/llm/call.py`（`call_with_user_retry`），将“是否继续重试”从业务层迁移到 LLM 调用统一层。
- **任务 C + D 已完成核心**：`persist_novel_identity` 写入小说级 `config/runtime/world/characters`；`src/config` 优先加载当前小说目录；命名后同轮重建编排器并切换目录。

### 六、下一步计划（执行版）

- **任务 E（集成验收）**：补“空项目首次启动 -> 设定 -> 命名 -> 同轮切换小说目录”集成测试，覆盖关键日志与路径断言。
- **路径收口**：继续把 `design_session_persistence`、`file_sync` 的边缘分支统一到小说目录，减少全局路径散写。
- **稳定性**：完成“连续超时 N 次自动降级”策略并接入作者在环主流程。
- **关系图谱**：`graph.yaml`、查询 API 与回合写回同步、角色 prompt 注入已落地；后续接成长状态机与副线证据写入。
- **大纲与节拍**：按 `docs/design/outline-and-beats.md` 分阶段实现（`outline.yaml`、TurnPlan/正文主角轴、桥接摘要、同文导出）。

### 七、关键角色成长状态机设计（已产出文档）

- **文档链接**：`docs/design/character-growth-state-machine.md`
- **方案摘要**：
  - 关键角色引入五维状态：`power/mind/social/goal/resource`；
  - 定义事件驱动迁移：`状态 + 事件 + 条件 -> 叙事变化 + 代价 + 冷却`（语义优先）；
  - 记忆分层为 L1 事实 / L2 解释 / L3 策略，并统一标签；
  - 在 `apply_event_and_state_write` 后执行迁移并持久化 `growth_state.yaml`；
  - 增加 `GrowthGuard` 约束（跨级上限、无代价收益、关系变化幅度、目标切换频率）；
  - 增加题材模式：`narrative_only`（默认）/ `hybrid` / `numeric`，避免非游戏题材过度数据化。
  - 引入轻量关系知识图谱（Relationship Knowledge Graph）：角色关系边、证据事件、关系演化查询，支撑关系线长期一致性。
  - 给出分阶段实施与测试验收标准，可直接进入实现。

---

## 2026-02-11

### 一、作者在环记忆：目录持久化、动态分类、启动进展、渐进检索

**目标**

- 作者自由补充的写作要求可 **LLM 体系化归类**、**按目录持久化**，并在 **写作前分析** 中 **渐进式检索** 注入，而非仅靠当回合原文。
- 「最近一章」粒度：启动时展示 **最近约 2～3 回合**（可配置为 N）的正文摘要与预览。
- 分类 **随小说类型可扩展**：通过配置追加维度或完全自定义，避免写死五类。

**实现要点**

| 模块/配置 | 说明 |
|-----------|------|
| **author_classified_memory.py** | `AuthorClassifiedSpec`、`get_author_classified_spec`；`classify_author_input` / `append_classified_entries`；`build_category_index_snippet` → `select_categories_for_context` → `load_author_memory_snippet`；`print_startup_resume` / `format_design_session_resume` / `format_recent_turns_for_display`。 |
| **runtime.author_classified_memory** | `include_defaults`（默认 true）、`categories: [{ id, label_zh, hint }]`、`fallback_id`；id 须安全目录名 `^[a-z][a-z0-9_]{0,63}$`。 |
| **turn_planning.py** | `generate_turn_plan_for_turn(..., project_root)` 拉取渐进片段；prompt 增加「作者持久记忆」区块。 |
| **run_novel_with_author.py** | 启动与重载后打印进展；补充要求时归类写盘并传 `runtime_config`。 |
| **file_sync / MEMORY 文档** | `book/README.md` 提及 memory/author_classified；`docs/design/memory-storage-and-retrieval.md` 补充布局与动态分类说明。 |
| **example_runtime.yaml** | 注释示例（如言情向 `romance` 扩展）。 |

**单测**：`tests/unit/test_author_classified_memory.py`（归一化、追加、动态合并/替换、`progressive` 空目录）。

### 二、下一步计划（接续）

- 将 **作者归类记忆** 在 **generate_turn_body**、驳回后 **修订正文** 等路径中 **可选注入**（与写作前分析对齐）。
- 设定深挖 **两段式** 方案确认后实现（见 `docs/planning/next-iteration.md`）。
- **LLM 联网/深度思考** 等预处理层（仍属待办）。

### 三、本轮修改文件汇总（2026-02-11）

| 文件 | 修改摘要 |
|------|----------|
| **src/author_loop/author_classified_memory.py** | 新建后迭代：动态分类 spec、目录布局、归类/检索/启动摘要。 |
| **src/author_loop/turn_planning.py** | `project_root`、作者记忆注入 `build_turn_plan_prompt`。 |
| **run_novel_with_author.py** | 启动进展、`append_classified_entries(..., runtime_config)`、环境变量说明。 |
| **src/runtime/file_sync.py** | `book/README.md` 含 memory/author_classified。 |
| **config/example_runtime.yaml** | `author_classified_memory` 注释示例。 |
| **docs/design/memory-storage-and-retrieval.md** | 布局与动态分类约定。 |
| **tests/unit/test_author_classified_memory.py** | 单测。 |
| **docs/planning/next-iteration.md** | 已完成条目更新。 |

### 四、配置拆分：system_config（系统）、example_runtime（本书入口）、novel_writing（写作基础）

- **动机**：LLM、`debug`、`dev_agent` 与小说无关；**开局 + 启用哪些 Agent** 与 **写作流程、设定研究、落盘** 再分开，便于换书时只改 `example_runtime` + world/characters，或只调 `novel_writing`。
- **加载**：`load_runtime_config`：① **system_config.yaml**（可选）② **example_runtime.yaml**（必填）③ **novel_writing.yaml**（可选）— 将③中键 **深度合并进 `runtime`**（覆盖②里 `runtime` 同名键）。
- **文件**：**system_config** = 框架与调试；**example_runtime** = `novel_run` + `agents`；**novel_writing** = `world_coordinator` / `setting_research` / `turn_*` / `storage` / `author_classified_memory` 等。

### 五、防卡死基础防护（测试超时 + 请求超时）

- **测试侧**：新增 `pytest.ini`（`--timeout=60 --timeout_method=thread`）与依赖 `pytest-timeout`，避免单测长时间挂住无反馈。
- **LLM 请求侧**：
  - `OpenAICompatibleLLM` 支持并默认读取 `llm_options.timeout=30`、`max_retries=1`；
  - `WenxinLLM` 增加 `timeout/max_retries` 与有限重试回退，避免长时间阻塞。
- **默认配置**：`config/system_config.yaml` 增加 `framework.llm_options.timeout/max_retries`（30s / 1）。

### 六、下一步计划（更新）

- 在 `run_novel_with_author` 增加“**连续超时 N 次自动降级**（或提示切 dummy）”策略，并在 CLI 给出明确提示，减少交互等待不确定性。
- 将作者归类记忆继续透传到 `generate_turn_body` 与“驳回后修订正文”路径，保持硬约束一致性。
- 继续推进设定深挖两段式（先决策、再注入细节）落地方案。

---

## 2026-03-19

### 一、LLM 额度/配额用尽：提醒 + 明确回退（避免卡住式失败）

- 在真实 LLM Provider 外增加 `QuotaAwareLLMProvider`（`src/llm/base.py`），识别“insufficient_quota/配额用尽/余额不足/硬限制”等错误；
- 第一次触发会在控制台打印明确提醒（API Key/充值/或切 `framework.llm: dummy`），并置为全局耗尽状态；
- 随后在写作前分析/正文生成/摘要生成/正文修订等路径中捕获 `LLMQuotaExhaustedError`，直接走现有占位回退逻辑，减少重复 warning 与不确定的交互体验。

### 二、阶段一驳回也可修改写作前分析并重试生成正文

- 当阶段一输入 `n`（作者驳回，不写回事件簿/状态）时，主流程额外询问：是否在本回合内修改写作前分析（plan）并重新生成正文；
- 若选择重试，则允许补充分析要求 → 调用 `revise_turn_plan_with_author_requirements` 修订 → 再次 `generate_turn_body` 并回到阶段一审阅；
- 该分支仍保持“未通过审阅/驳回则跳过写回”的安全边界，避免破坏作者在环节的控制权。

### 三、写作前分析设定概览仅为概要，按触发决定是否深挖

- 在 `turn_planning.build_turn_plan_prompt` 中将“设定描述”注入改为截断的基础设定概览；
- prompt 明确要求：只有当最近事件/最近剧情/次要角色信息触发“需要设定细节来解释行动/因果/规则”的判断时，才允许在分析中简要点出需深挖的设定维度；否则只沿用概览，不要提前展开完整设定体系。

### 四、本轮修改文件汇总

| 文件 | 修改摘要 |
|------|----------|
| **src/llm/base.py** | 增加 `QuotaAwareLLMProvider` 与 `LLMQuotaExhaustedError`，识别额度用尽并提示/回退。 |
| **src/author_loop/turn_planning.py** | 生成写作前分析/正文/修订/摘要处捕获 `LLMQuotaExhaustedError`；并限制“设定概览”为概要且按触发决定是否深挖。 |
| **run_novel_with_author.py** | 阶段一驳回后可选择修改写作前分析并重试生成正文。 |
| **tests/unit/test_llm.py** | 更新 get_llm_provider 的类型断言，并补充额度用尽触发逻辑用例。 |

---

## 2026-03-04

### 一、逻辑校准后设定被重置问题修复

**现象**

- 讨论中「满意」→ 归纳写入 `setting_research_output.yaml` 与 `book/setting/*.md` → 询问保存、逻辑校准 → 返回主菜单后，界面展示的设定（以及 config 内内容）被「重置」为仅含默认战力/境界的版本，讨论中新增方向（如「上古修行体系」）及细化内容丢失。

**根因**

- 主循环**每次迭代开头**都执行 `agent.run()`，用 theme/genre/reference 重新生成 YAML 并**整份覆盖** `config/setting_research_output.yaml`。从讨论子流程 `continue` 回来后，下一轮循环立刻再次执行 `agent.run()`，导致刚由 `_write_special_settings` 写回的归纳结果被覆盖。

**修复**

- 引入标志 `skip_next_agent_run`。从讨论子流程返回（选 c 继续上次讨论返回、或选 c 首次进入多轮讨论后返回）时，在 `continue` 前置 `skip_next_agent_run = True`。主循环开头若该标志为 True，则**本轮回合跳过 `agent.run()`**，仅从 config 加载 special，保留归纳后的设定，然后清除标志。

### 二、本轮修改文件（2026-03-04）

| 文件 | 修改摘要 |
|------|----------|
| **src/author_loop/design_phase.py** | 主循环前增加 `skip_next_agent_run`；从 _run_freestyle_discussion 返回的两处 `continue` 前设 True；循环内根据标志跳过 agent.run() 并打 DEBUG 日志。 |

---

## 近期（叙事节奏、写作前分析、重启覆盖确认）

### 一、玄幻开篇节奏与写作前分析

**叙事节奏（画卷徐徐展开）**

- **范围 Agent**（world/agent.py）：prompt 增加【叙事节奏】说明——开篇宜如画卷徐徐展开，本回合只推进一小步（氛围、环境细节、人物一个反应或微小变化），避免一次性爆发重大冲突或塞入过多情节。
- **角色 Agent**（character/agent.py）：prompt 增加【叙事节奏】——剧情如画卷缓缓打开，本回合宜克制、具体；内心独白写一瞬感受或观察，言行写一句短对话或细微动作，不必本回合达成重大行动或冲突。

**写作前分析（落笔前结构化思考）**

- **范围 Agent**：增加【写作前分析】——落笔前完成 ① 场景分析 ② 相关角色分析 ③ 受害者/冲突方分析（若有）④ 相关其他人员与生物 ⑤ 本段目标分析 ⑥ 结合前文与设定确定基调与风格 ⑦ 分场景构思；再输出约束与本回合事件摘要。
- **角色 Agent**：增加【写作前分析】——① 场景分析 ② 相关角色分析 ③ 受害者/冲突方分析（若涉及）④ 相关其他人员与生物 ⑤ 本段目标分析 ⑥ 基调与风格 ⑦ 分场景/分镜构思；再输出内心独白与言行。

### 二、重启后覆盖已有设定的危险操作确认

**现象**

- 重新启动程序进入设定阶段后，已有设定与之前保存内容被覆盖丢失。主循环首次迭代会无条件执行 `agent.run()`，重写 `setting_research_output.yaml`，导致此前讨论归纳与保存的设定被清空。

**修复**

- **检测已有设定**：新增 `_has_existing_setting_output(config_dir)`，判断 `setting_research_output.yaml` 是否存在且含实质内容（除 world_id/version 外有 power_system、level_system 等带 name/description/levels 的项）。
- **首次进入主循环时询问作者**：若本次启动已加载会话（`loaded`）或磁盘上已有设定文件且非空（`_has_existing_setting_output`），在即将执行 `agent.run()` 前提示「检测到已有设定或会话。重新生成将覆盖现有设定（危险操作）。」并询问「是否保留现有设定？(y=保留并继续, n=重新生成并覆盖, 默认 y)」。选 y 则本轮回合跳过 `agent.run()`，直接加载磁盘设定；选 n 才执行覆盖。仅首次迭代询问（`first_iteration`），避免重复打扰。

### 三、本轮修改文件汇总

| 文件 | 修改摘要 |
|------|----------|
| **src/agents/world/agent.py** | 【写作前分析】七步（场景/角色/受害者与冲突方/其他人员与生物/本段目标/基调风格/分场景构思）；【叙事节奏】画卷徐徐展开、本回合只推进一小步。 |
| **src/agents/character/agent.py** | 【写作前分析】七步（同上，含分镜构思）；【叙事节奏】克制具体、一瞬感受与细微言行。 |
| **src/author_loop/design_phase.py** | `_has_existing_setting_output()`；主循环首次迭代且存在已有设定/会话时询问是否保留，y 则跳过 agent.run()，避免危险覆盖。 |

**下一步计划（已写入 docs/planning/next-iteration.md 待办）**

- **LLM 调用层支持可选「联网」「深度思考」等模式**：设定讨论、剧情推动等环节可先联网搜索相关/类似材料作为参考再调 API 输出。方案：底层接口支持「先联网检索 → 注入 prompt → 再请求 API」及可选深度思考；按场景或配置开关控制；实现时做生成前预处理抽象、检索结果上限与缓存。

---

## 近期（每回合写作前分析先行、正文生成与作者补充要求）

### 一、每回合两阶段：先分析后正文

- **流程**：每回合先调用 `generate_turn_plan_for_turn` 生成本回合写作前分析及预计字数 → 呈报作者 → 询问「同意按此分析生成本回合正文？」；同意后执行 `run_one_turn`（Scope + 角色）→ `generate_turn_body` 基于分析与本回合结果生成本回合小说正文（≤ 配置/临时字数）→ 写入 `result.body_narrative` → 阶段一审阅（可编辑正文）→ 写回时优先使用 `body_narrative`。
- **TurnResult**：新增可选字段 `body_narrative`；`apply_event_and_state_write` 有则用其作为本回合事件摘要写回。
- **模块**：`src/author_loop/turn_planning.py`（TurnPlan、generate_turn_plan_for_turn、generate_turn_body、build_turn_body_prompt）；CLI 阶段一有 body 时展示「本回合正文（≤2000字）」；编辑回合结果支持 `## body_narrative` 段解析与回写。

### 二、字数限制可配置、可临时调整

- **配置**：`config/example_runtime.yaml` 下 `runtime.turn_body_max_chars: 2000`，作为每回合正文默认字数上限。
- **临时调整**：呈现写作前分析后，提示「本回合正文上限（字，直接回车使用 {default}）：」；作者输入数字则本回合使用该值（限制 100～10000），回车则用配置默认值。

### 三、作者可自由补充本回合正文要求

- **输入**：在「正文上限」之后提示「可在此补充对本回合正文的要求（如视角、语气、禁止出现的内容等，直接回车跳过）：」，作者可输入任意本回合要求（不限于预设设定）。
- **注入**：`generate_turn_body` 增加参数 `author_requirements`；`build_turn_body_prompt` 在 prompt 中增加【作者补充要求】（必须满足）段，供 LLM 在生成正文时遵守。

### 四、作者补充要求后由大模型修订写作前分析

- **流程**：作者输入补充要求后，若输入非空，则调用 `revise_turn_plan_with_author_requirements(plan, author_requirements, runtime)`，由大模型在原有写作前分析基础上修订/补充（如更新相关角色分析、本段目标、分场景构思等），使修订后的分析充分体现作者要求；解析返回为新的 TurnPlan 并再次呈报「修订后本回合写作前分析」及预计字数，再询问「同意按此分析生成本回合正文？」。
- **实现**：`turn_planning.revise_turn_plan_with_author_requirements`：拼 prompt（当前分析 + 作者补充要求），LLM 输出修订后分析 + 本回合预计字数，用 `_parse_turn_plan_response` 解析；无 LLM 或失败时在原分析末尾追加【作者补充要求】段并沿用原预计字数。主流程在收集到 author_requirements 后若非空则先修订 plan 再展示修订结果。

### 五、本轮修改文件汇总

| 文件 | 修改摘要 |
|------|----------|
| **config/example_runtime.yaml** | 新增 `turn_body_max_chars: 2000`。 |
| **src/author_loop/turn_planning.py** | TurnPlan、写作前分析生成、正文生成（author_requirements、max_chars）；generate_turn_plan_for_turn；revise_turn_plan_with_author_requirements（作者补充后由 LLM 修订分析）。 |
| **run_novel_with_author.py** | 每回合先规划→展示分析→字数上限与作者补充要求→若已补充要求则修订写作前分析并再展示→同意后 run_one_turn→generate_turn_body→审阅；从配置读默认字数。 |
| **src/author_loop/cli.py** | 阶段一有 body_narrative 时优先展示；编辑文件支持 ## body_narrative 段读写。 |
| **src/orchestrator/orchestrator.py** | TurnResult.body_narrative；apply_event_and_state_write 有 body 时用其写回。 |

---

## 近期（正文展示后自由交流、摘要写入、正文单一数据源、审阅提示）

### 一、正文展示后作者自由交流与按反馈修订

- **意图理解**：`turn_planning.understand_author_review_intent` 判断作者输入为 confirm（y/没问题/满意等）、reject、edit、supplement 或 revise（对本回合正文的修改意见）。
- **修订循环**：阶段一审阅时，作者可输入 y/e/s/n，也可**直接输入对本回合正文的修改意见**；若为 revise，则调用 `revise_body_by_feedback` 由大模型根据反馈修订正文，更新 `result.body_narrative` 后再次展示，直到作者表示满意并确认。
- **主流程**：`review_turn_result` 增加 `runtime_config`，提示中说明可输入修改意见或「y/没问题」确认；CLI 中意图为 revise 时调用修订并继续审阅循环。

### 二、作者「没问题」时摘要写入主线记忆

- **摘要生成**：作者确认（没问题/y/满意）后，`apply_event_and_state_write` 在存在 `body_narrative` 时调用 `generate_turn_summary_from_body(body, runtime_config)` 从正文生成一到三句话摘要。
- **写回**：事件条目写入 `storage` 时同时包含 `summary` 与 `body`，摘要与正文一一对应；后续检索到摘要时可从同一条 event 取 `body` 查看完整正文。
- **file_sync**：若配置 data_root，`sync_scope_turn` 将回合文件写成「摘要 + 正文」两段，便于磁盘上与记忆一致。

### 三、正文单一数据源与持久化一致

- **唯一存储**：正文仅存在于「范围事件」中（storage 的 event 含 summary + body）；展示时从 storage 取（当前回合审阅用 result.body_narrative，已写回回合用 event["body"]）。
- **持久化**：若配置 data_root，启动时 `load_scope_events_from_disk` 从 `book/events/<scope_id>/events/turn_*.md` 加载事件到 storage；写回时 `apply_event_and_state_write` 先 append_events 再 `sync_scope_turn` 同步到磁盘，避免多处存正文导致不一致或修改遗漏。
- **实现**：`file_sync` 新增 `_parse_turn_md_content`、`load_scope_events_from_disk`；`MemoryStorage.set_scope_events` 用于加载后覆盖；`Orchestrator.from_config` 在 data_root 存在时对各 scope 加载事件；`apply_event_and_state_write` 在 data_root 存在时调用 `sync_scope_turn`；`retrieval.get_turn_body_from_storage` 从记忆取某回合正文。

### 四、审阅提示：直接回复什么表示满意

- **CONFIRM_HINT**：`turn_planning.CONFIRM_HINT = "直接回复「y」或「没问题」表示满意，将写入本回合摘要到主线记忆并进入下一回合。"`
- **阶段一提示**：`review_turn_result` 的输入提示中增加该句，明确告知作者输入 y 或 没问题 会触发摘要写入并进入下一回合。

### 五、本轮修改文件汇总

| 文件 | 修改摘要 |
|------|----------|
| **src/author_loop/turn_planning.py** | understand_author_review_intent、revise_body_by_feedback、generate_turn_summary_from_body；CONFIRM_HINT。 |
| **src/author_loop/cli.py** | review_turn_result 支持自由输入与 revise 循环、runtime_config、CONFIRM_HINT 提示。 |
| **src/orchestrator/orchestrator.py** | apply_event_and_state_write 有 body 时生成摘要并写 summary+body；data_root 时 sync_scope_turn；from_config 加载 scope 事件、_data_root/_project_root。 |
| **src/runtime/file_sync.py** | sync_scope_turn 写入 time/place；_parse_turn_md_content、load_scope_events_from_disk。 |
| **src/runtime/storage.py** | set_scope_events。 |
| **src/retrieval/memory.py** | format_scope_events_snippet 注释；get_turn_body_from_storage。 |
| **run_novel_with_author.py** | review_turn_result 传入 runtime_config。 |

**下一步计划**：见 docs/planning/next-iteration.md（设定研究 Agent 优化、世界配置为空引导、LLM 联网/深度思考等）。

---

## 近期（设定讨论满意后归档、写作前分析补充追问）

### 一、设定讨论满意后：提醒查看设定文件、确认后再保存/校准、会话归档

- **融合与写回**：满意后 `summarize_and_extract_by_directions` 将当前设定与本轮讨论融合，写回 `setting_research_output.yaml` 与 `book/setting/<key>.md`。
- **提醒查看**：归纳写回后列出本轮更新的设定文件路径（config/setting_research_output.yaml 与各方向 .md），提示「请查看上述设定文件，确认无误后输入 y 继续（将询问是否保存与逻辑校准）」；未输入 y 前循环提示「请查看上述文件后输入 y 确认继续」。
- **确认后再保存/校准**：仅当作者输入 y/没问题 后才进入「是否保存」「是否逻辑校准」。
- **会话归档**：本轮回合结束（返回主菜单前）再次 `save_session`，`state_snapshot` 中显式写入 `current_discussion: None`，表示已归档；加载时 `_backfill_current_discussion` 改为仅当 `"current_discussion" not in state_snapshot` 时才从 events 回填，避免归档后重启仍提示「未完成讨论」。

### 二、写作前分析：补充要求后继续追问，直接回车才生成正文

- **循环追问**：呈现写作前分析与预计字数后，循环询问「可在此补充对本回合正文的要求（如视角、语气、禁止出现的内容等，直接回车跳过）」；若作者输入内容则调用 `revise_turn_plan_with_author_requirements` 修订分析并展示「修订后本回合写作前分析」，然后再次询问同一句；**仅当作者直接回车（不再补充）时**跳出循环，再询问「同意按此分析生成本回合正文？」后生成正文。
- **多轮要求合并**：多轮补充的要求按顺序拼接为 `author_requirements` 传入 `generate_turn_body`。

### 三、本轮修改文件汇总

| 文件 | 修改摘要 |
|------|----------|
| **src/author_loop/design_phase.py** | 满意后列出设定文件路径、确认循环；本轮回合结束 save_session 写 current_discussion=None；归档说明。 |
| **src/author_loop/design_session_persistence.py** | _backfill_current_discussion 仅当 "current_discussion" not in state_snapshot 时回填。 |
| **run_novel_with_author.py** | 写作前分析阶段：while True 追问「可在此补充…」，直接回车跳出后询问同意并生成正文；author_requirements_parts 累加。 |

---

## 2026-02-11

### 一、世界配置动态化与设定文档登记

**example_world.yaml 作为动态清单**

- **可空与说明**：各段（world、time、scopes、locations）均可为空；文件头注释说明从空配置启动时需将 `runtime.agents.scopes.enabled_ids` 与 `characters.enabled_ids` 设为 `[]`，待设定阶段填写后再启用。
- **brief**：封面简介字段，选主菜单 **p 保存进度** 时根据当前审阅摘要（世界/范围/角色/特殊设定）自动生成并写回 `example_world.yaml`，类似小说封面介绍。
- **setting_documents**：列表项，登记 `data/book/setting/` 下各设定详细 .md；在设定交流中**新增方向**时（作者确认增加后）动态追加一项（key、path、title），保证配置与落盘设定一致。

**config 与 design_phase 联动**

- **src/config**：新增 `update_world_brief(config_dir, brief_text)` 写回 brief；`add_setting_document_to_world_config(config_dir, key, path_rel, title)` 向 setting_documents 追加一项（已存在 key 则跳过）；`is_world_config_empty(world_config)` 判断 world.name 是否为空。
- **design_phase**：满意后归纳并询问新方向时，若作者确认增加，则 `add_setting_direction` + `add_setting_document_to_world_config` 同步到世界配置；主菜单选 **p** 时用 `_build_cover_brief` 生成简介并 `update_world_brief`；每轮主循环开始若 `is_world_config_empty(world_config)` 则打 DEBUG 提示可通过 **c** 交流填写世界设定。

### 二、本轮修改文件（2026-02-11）

| 文件 | 修改摘要 |
|------|----------|
| **config/example_world.yaml** | 可空说明、brief、setting_documents 注释与结构；各段注释标明可空与动态填写方式。 |
| **src/config/__init__.py** | `update_world_brief`、`add_setting_document_to_world_config`、`is_world_config_empty`；启动加载 debug 已有。 |
| **src/author_loop/design_phase.py** | 新增方向时调用 `add_setting_document_to_world_config`；主菜单 p 时 `_build_cover_brief` + `update_world_brief`；启动时 `is_world_config_empty` 提示；backfill setting_documents 与 allowed_directions 逻辑。 |

---

## 2026-02-19

### 一、设定讨论与目录/配置（近期完成）

**book/setting 目录与会话分离**

- **会话统一入 sessions/**：会话文件写入 `book/setting/sessions/session_<ts>.md` 与 `.yaml`，与各方向 .md 分离；加载时先试 sessions 再兼容旧路径。
- **设定方向配置驱动**：`book/setting/setting_config.yaml` 列出 `directions`；仅配置中的方向会写入独立 .md；讨论归纳出新方向时**询问作者是否增加**，确认后 `add_setting_direction` 并建对应 .md。
- **主菜单 p 与加载回填**：主菜单选 p 时若最近一条为 discussion，将 `current_discussion` 写入 state_snapshot；`load_session_full` 时若 state_snapshot 无 current_discussion 但 events 中有 discussion，从最后一条 discussion 回填，便于「继续上次对话」。

**归纳与满意后流程**

- **归纳 prompt**：各方向 .md 与「讨论与设定边界」明确要求：针对该方向展开，**只能比讨论多、不能少**，须涵盖讨论要点（summarize_and_extract_by_directions、extract_discussion_boundaries_by_direction）。
- **满意后**：归纳写 .md 后询问「是否保存」「是否进行本迭代逻辑校准」；保存后可回到主菜单选 c 继续讨论；逻辑校准调用 `run_discussion_logic_calibration` 检查矛盾/遗漏。

**DEBUG 日志（可配置）**

- **配置项**：`config/example_runtime.yaml` 下 `debug.startup`、`debug.design_phase`；为 true 时对应阶段打 DEBUG。
- **生效方式**：`apply_design_phase_debug(runtime)` 将对应 logger 与**根 handler 级别**设为 DEBUG（否则 DEBUG 被 handler 过滤）；启动时**先**`load_runtime_config` 再 `apply_design_phase_debug`，再 `Orchestrator.from_config`，以便从首次加载就有 DEBUG。
- **范围**：startup → src.config、src.orchestrator.orchestrator、min_autobook（加载 runtime/world/characters/special、编排器）；design_phase → design_phase、design_session_persistence、setting_research/agent（设定讨论每步）。

### 二、待重新梳理与下一步计划

**当前状况**

- 实际使用中发现**多处需重新修改**：设定配置与内容文件的**承载内容与配置形式**有待重新设计；设定研究 Agent 与整体设定的**迭代完成方式**需优化。

**下一步计划**

- **设定研究 Agent 优化**：方向为**迭代完成整体设定**；对**不同设定配置与内容文件**重新设计其承载内容与配置关系，使设定阶段更清晰、可维护。
- **提交 GIT**：将本轮工作日志更新与上述规划整理后提交版本。

（具体重构方案与文件职责划分待后续迭代细化。）

### 三、本轮修改文件清单（供提交 GIT）

| 文件 | 修改摘要 |
|------|----------|
| **config/example_runtime.yaml** | 新增 `debug.startup`、`debug.design_phase` 开关。 |
| **run_novel_with_author.py** | 启动时先 `load_runtime_config` 再 `apply_design_phase_debug`，再 `Orchestrator.from_config`；增加 `[启动]` debug 打印。 |
| **scripts/migrate_design_session.py** | 迁移目标改为 `book/setting/sessions/`，session_file 路径同步。 |
| **src/agents/setting_research/agent.py** | 归纳/边界 prompt 增加「只能多不能少」；新增 `run_discussion_logic_calibration`；各步 `[设定讨论]` debug 日志。 |
| **src/author_loop/design_phase.py** | 设定方向配置驱动（allowed_directions、询问新方向）；满意后询问保存与逻辑校准；_sync 仅写配置内方向；各步 `[设定讨论]` debug。 |
| **src/author_loop/design_session_persistence.py** | 会话写入 `sessions/`；`setting_config.yaml` 与 load/ensure/add_setting_direction；load 时 current_discussion 回填；各步 debug。 |
| **src/config/__init__.py** | 各配置加载与 get_initial_scene 增加 `[启动]` debug 日志。 |
| **src/log_config.py** | `apply_design_phase_debug` 支持 debug.startup、读取顶层 debug、根 handler 设为 DEBUG。 |
| **src/orchestrator/orchestrator.py** | `from_config` 内增加 `[启动]` debug 日志。 |
| **WORKLOG.md** | 2026-02-19 纪要（目录/配置/归纳/DEBUG/下一步与修改文件清单）。 |
| **docs/planning/next-iteration.md** | 进行中「设定研究 Agent 优化与设定文件重新设计」；待办补充。 |

---

## 2026-02-18

### 一、方案讨论与文档更新（简要）

**新增/更新设计与方案文档**

- **记忆分类、存储与检索**：新增 `docs/design/memory-storage-and-retrieval.md`。约定小说主体按回合存 `content/turns/turn_NNNN.md`；记忆统一用 Markdown、按类型分子目录（`memory/characters`、`scopes`、`secondary_characters`、`setting`），采用**渐进式目录**（每层 README 索引，类 Skills 方案），大模型可沿目录按需查找、无需向量库。TECH_IMPLEMENTATION §7 增加对该文档的引用。
- **设定作为共享基础规则与检索式注入**：DESIGN §6.5、`docs/design/llm-and-agents.md` 明确设定与记忆体量可能很大，Agent 必须按需检索、不得全量注入上下文。
- **设定阶段按方向讨论流程**：DESIGN 新增 §6.6。作者可选择具体方向（战力体系、境界体系、世界规则等）讨论；设定 Agent 每次答复仅针对该方向，多轮直至作者满意 → 再提炼进整体设定并呈现 → 询问修改/继续讨论/设定完成；**仅当作者明确「设定完成」**时才结束设定阶段。`src/author_loop/design_phase.py` 模块与 run_design_phase 的 docstring 已注明上述目标，当前实现仍为 y/e/s 简化版。

**下一步规划更新**

- NEXT_ITERATION、next_plan 已更新：新增待办 **第 16 项**（设定阶段按方向讨论流程实现）、**第 17 项**（记忆与内容目录存储与检索实现）。

---

### 二、关键任务进展（2026-02-18）

**本次为方案与规划整理，无代码实现。**

| 任务 | 内容 |
|------|------|
| 记忆存储与检索方案文档 | `docs/design/memory-storage-and-retrieval.md`：分类、content/turns、memory/ 渐进式目录、README 索引、检索流程、与现有 retrieval 对应、FileStorage/双写选项。 |
| 设定阶段交互设计 | DESIGN §6.6：按方向讨论 → 满意后提炼 → 整体呈现与询问 → 明确完成才结束；design_phase 目标说明。 |
| 下一步规划 | 第 16 项（设定阶段按方向讨论）、第 17 项（记忆/内容目录存储与检索）；NEXT_ITERATION、next_plan 已同步。 |

**待办**

- （无；第 17 项已完成。）

---

## 2026-02-18（第 17 项实现）

### 第 17 项 记忆与内容目录存储与检索

- **file_sync**（`src/runtime/file_sync.py`）：get_data_root(project_root, runtime_config)、next_turn_index(data_root)、write_turn_content（content/turns/turn_NNNN.md）、sync_scope_turn（memory/scopes/<id>/events、state.md）、sync_character_turn（memory/characters/<id>/events）、ensure_memory_root_readmes（README 索引）；渐进式目录与 README 维护。
- **编排器**：from_config 解析 runtime.storage.data_root，设置 _data_root；apply_event_and_state_write 时双写回合内容与 scope 事件/状态、_last_turn_index；apply_memory_write 时双写角色 events。
- **配置**：example_runtime.yaml 注释增加 storage.data_root 说明；单测 test_file_sync 共 7 个；单元 105 通过。

---

## 近期（设定阶段 s/d 合并为 c、集成测试修复）

### 设定阶段：s 与 d 合并为 c 输入想法

- **主菜单**：原「s 补充说明」「d 讨论某一方向」合并为 **c 输入想法**。选 c 后提示输入想法或补充（一句补充将用于重新生成整体设定，或说出想讨论/新增的设定内容进入多轮对话，满意后归纳到各方向）。
- **流程**：输入后询问「是否进入多轮讨论继续细化？」选 n 则仅将输入记为 reference，下一轮审阅时 agent.run(reference=...) 重新生成整体；选 y 则先 agent.run(reference=...) 再进入 _run_freestyle_discussion，满意后归纳到各方向并写回。
- **单测**：test_design_phase 改为 c/n/y、c/y/满意/y，mock discuss_freely、summarize_and_extract_by_directions；4 个用例通过。

### 集成测试：scope_id/角色从配置动态取

- **问题**：test_orchestrator 中 6 个用例写死 scope_id="capital"、角色 ["a","b"]，与当前 config（enabled_ids: 怪物来袭/村庄、张凡/李墨/王石头）不一致，导致 ValueError: scope_id 未配置或不存在。
- **修复**：新增 _first_scope_id(orch)、_present_characters(orch)，从编排器取第一个已配置 scope 与在场角色；所有依赖 scope/角色的用例改用上述辅助，随 config 自动适配。**全量 113 用例通过**（.venv 下 pytest tests/ -v）。

---

## 2026-02-18（book 统一目录、设计会话新方案与恢复）

### 一、book 统一目录（file_sync）

- **布局**：所有小说相关输出统一到 `data_root/book/` 下：`content`（回合内容）、`setting`（设定与会话）、`characters`（人物）、`events`（事件）。新增 `get_book_root(project_root, runtime_config)`。
- **写回**：`write_turn_content`、`sync_scope_turn`、`sync_character_turn`、`ensure_memory_root_readmes` 均改为写入 `data_root/book/` 对应子目录；单测已按新路径更新，全量 115 通过。
- **配置默认**：`config/example_runtime.yaml` 中 **storage.data_root** 默认启用为 `"data"`，开箱即用将回合内容与设定会话落盘到 `data/book/`；不需要时可注释或删除该段。

### 二、设计会话持久化新方案

- **config 仅存索引**：`config/design_session.yaml` 只保留 version、last_updated、theme、genre、summary、**session_file**（指向 book/setting 下 MD）。
- **完整内容落盘**：有 book_root 时，`save_session()` 将完整会话写入 **book/setting/session_&lt;timestamp&gt;.md** 与 **.yaml**；config 仅写摘要与 session_file。**补丁**：未配置 runtime.storage.data_root 时，book_root 退化为 `project_root / "data" / "book"`，保证讨论中「保存」与主菜单「p」始终走新方案（摘要进 config、完整进 md+yaml）。
- **设定研究产出**：各设定方向（战力、境界等）同步到 **book/setting/&lt;key&gt;.md**；config 内 setting_research_output.yaml 仍保留完整 YAML 供程序读取。**讨论与设定边界**：讨论结束归纳后，按方向提炼「设定边界与讨论要点」并写入各 .md 的 **## 讨论与设定边界** 节，便于后续查找、校准与边界确定（见下）。
- **文档**：docs/design/memory-storage-and-retrieval.md 增加 §3.1，说明 data_root/book/ 布局与 config 只存路径、内容用 MD。

### 三、旧版会话迁移与恢复

- **迁移脚本**：`scripts/migrate_design_session.py` 对 config 中**仍含 events** 的会话（version 1 或 version 2 均可）迁移到新方案：完整内容写 **data/book/setting/session_&lt;ts&gt;.md** 与 **.yaml**，config 重写为 version 2 仅路径与摘要。可用 `.venv\Scripts\python.exe scripts\migrate_design_session.py` 执行。
- **加载与恢复**：`load_session_full(config_dir, project_root, runtime_config)` 返回 `{ events, state_snapshot }`。version 2 时优先读同名的 .yaml；若无 .yaml 仅有 .md（如已迁移但未写 yaml 的会话），则从 **.md 解析 current_discussion**（`_parse_session_md_for_state_snapshot`）以恢复讨论。
- **设定阶段恢复**：`run_design_phase` 启动时调用 `load_session_full`，用返回的 events 初始化 session_events、state_snapshot 用于恢复；若有 `current_discussion` 则菜单提示「检测到未完成讨论，选 c 可继续上次对话」，选 c 时带历史轮次进入 `_run_freestyle_discussion(..., conversation_resume=...)`，不再执行首轮 discuss_freely，直接进入多轮输入。
- **验证**：针对当前 config/design_session.yaml（version 2）与 data/book/setting/session_20260218_050204.md（无 .yaml）验证：load_session_full 返回 OK，从 .md 解析出 11 轮讨论与 initial_message，选 c 可继续上次讨论。

### 四、开篇后确认环节可临时补充设定（已实现）

- **场景**：小说已开篇、回合制进行中，在阶段一（本回合结果审阅）或阶段二（角色记忆写回确认）增加 **s 补充设定** 选项；选 s 后进入一次「完善设定」流程，完成后再回到当前审阅。
- **约束与实现**：SettingResearchAgent 新增 **run_supplement(theme, genre, current_special, context_snippet, author_input, ...)**，prompt 明确「仅可补充与完善、不得与既有设定冲突、逻辑自洽」；LLM 产出与既有设定 **合并**（_merge_supplement_into_special）后写回 setting_research_output.yaml，并同步到 book/setting/。
- **入口**：design_phase.run_supplement_setting_during_turn(config_dir, runtime_config, world_config, scope_id, time_str, place, turn_summary_snippet) 提示作者输入补充意向，调用 agent.run_supplement，写回并 _sync_special_to_book_setting。
- **CLI**：review_turn_result、review_memory_plan 增加可选 **supplement_callback(scope_id, time, place, turn_summary)**；主流程传入 make_supplement_callback，选 s 时调用后继续审阅。单测 test_review_turn_result_supplement_then_accept 覆盖 s→y 流程。

### 五、讨论与设定边界写入 book/setting/*.md（已实现）

- **问题**：book/setting/ 下 level_system.md、power_system.md 等仅含结构化层级，未整合作者与 Agent 讨论的细节，不利于后续查找、分析与边界确定。
- **实现**：SettingResearchAgent 新增 **extract_discussion_boundaries_by_direction(discussion_text, direction_keys, theme, genre, runtime_config)**，按方向用 LLM 提炼「设定边界与讨论要点」（约 200 字/方向）。**_sync_special_to_book_setting(..., discussion_boundaries=None)** 与 **_write_special_settings(..., discussion_boundaries=None)** 支持可选 discussion_boundaries；写各 .md 时在结构化内容后追加 **## 讨论与设定边界** 段落。讨论结束（「满意」且归纳出方向）后调用提炼，将 boundaries 传入 _write_special_settings，同步到 book/setting/。无 data_root 时 _sync 退化为 project_root/data/book。

### 六、下一步计划（见 next_plan.md）

- 可选：设定研究联网检索；search_ideas 联网扩展。

---

## 2026-02-18（设定阶段增强：自由讨论 + 归纳 + 持久化）

### 设定讨论方式与分类动态化

- **作者直接说想法、不写死方向**：选 d 后不再出现「1 战力 2 境界」菜单；提示作者直接输入想讨论的内容（可交叉多维度），由 LLM 在**讨论结束后**归纳到各方向。
- **自由讨论 + 归纳到多方向**：`discuss_freely` 与作者自由讨论；作者「满意」后 `summarize_and_extract_by_directions` 归纳到多方向并写回；设定维度动态扩展（炼丹、制符等）。设定 Agent 回复完整呈现，不截断。
- **持久化**：`design_session_persistence` 记录摘要、菜单、完整讨论与状态；主菜单 **p 保存进度**、讨论中输入 **保存** 写入 `config/design_session.yaml`，便于后续增量续写。DESIGN §6.6、NEXT_ITERATION 已同步更新。

---

## 2026-02-18（第 16 项实现）

### 第 16 项 设定阶段按方向讨论流程（初版）

- **SettingResearchAgent**（`src/agents/setting_research/agent.py`）：新增 `discuss_direction(...)`、`extract_direction_yaml(...)`、`DIRECTION_LABELS`。
- **design_phase**：主菜单 d 讨论；选方向（1 战力 / 2 境界）→ `_run_direction_discussion` 子循环 → 满意后提炼写回；仅 y 设定完成才结束。新增 `_direction_snippet`、`_write_special_settings`。
- **单测**：`test_design_phase_direction_then_confirm_returns_false`；单元 98 通过。*后续*：已改为自由讨论 + 归纳 + 持久化（见上节）。

---

## 2026-02-11

### 一、风险与进展（简要）

**进展**
- **第 14 项 设定研究 Agent 充实**：SettingResearchAgent.run() 在传入 runtime_config 且非 DummyLLM 时，用 _build_setting_prompt(theme, genre, reference) 生成 prompt、调 get_llm_provider().generate()、_extract_yaml_block 抽取 YAML 并 safe_load，与 world_id/version/genre/theme 等拼成完整结构写入 setting_research_output.yaml（power_system、level_system 等）；design_phase 调用时传入 runtime_config。单测 test_run_with_mock_llm_produces_power_and_level_system（patch src.llm.get_llm_provider）通过；设定研究单测 4 个全过。联网检索留作后续扩展。

**风险**
- 与前期相同；集成测试 test_orchestrator 中 6 个用例仍使用 scope_id=capital，若配置已改为其他 scope 需在测试中使用独立配置或恢复示例 scope。

---

### 二、关键任务进展（2026-02-11）

**本次修改**

| 任务 | 内容 | 测试 |
|------|------|------|
| 第 14 项 设定研究 Agent 充实 | run(..., runtime_config=None)：有 LLM 时 _build_setting_prompt → provider.generate → _extract_yaml_block + yaml.safe_load → 拼 world_id/version/genre/theme/power_system/level_system 等 → _dict_to_yaml 写入 setting_research_output.yaml；design_phase 传入 runtime_config。无 LLM 或异常时仍写占位 YAML。 | test_setting_research 新增 test_run_with_mock_llm_produces_power_and_level_system（patch src.llm.get_llm_provider）；4 个单测通过。 |
| 第 15 项 DevAgent search_ideas 充实 | run_search_ideas：setting_research_output_path 读已有 YAML 或 theme + runtime_config_path 调用设定研究 Agent，产出 power_system.md、level_system.md；无配置时占位。新增 _ideas_from_setting_yaml、_run_setting_research_and_get_yaml_path 等。 | test_run_search_ideas_from_setting_yaml_produces_real_entries；单元 97 通过。 |

**待办**
- （无；第 14～15 项已完成。）

---

## 2026-02-17

### 一、风险与进展（简要）

**进展**
- **开书前设定阶段**已实现：当 `runtime.setting_research.enabled=true` 且 `trigger=design_only` 时，在进入回合循环前先运行设定研究 Agent，展示世界模型与设定，与作者交互（y 确认 / e 编辑 / s 补充说明并重新生成）；编辑后可重载配置与编排器。单元测试 test_design_phase（3 个）通过。
- 配置层新增 `load_special_settings_config()`（优先 setting_research_output.yaml，否则 example_special_settings.yaml）。
- **关键角色与次要角色**：配置仅列关键角色（拥有 CharacterAgent）；其余角色由剧情动态产生，写入存储的「次要角色列表」供 Agent 查阅。Storage 新增 get_secondary_characters/append_secondary_character；Retrieval 新增 format_secondary_characters_snippet；TurnContext 新增 secondary_characters_snippet，build_turn_context_from_storage 自动注入。配置与 USAGE、TECH_IMPLEMENTATION 已说明。示例角色名改为张凡/李墨/王石头。
- **第 13 项 角色/范围 Agent 接 LLM**：CharacterAgent/ScopeAgent 在 turn() 中若有 LLM（非 DummyLLM）则拼 prompt（角色用 retrieve_character_memory + characters_config，范围用 format_scope_events_snippet + world_config）、调 get_llm_provider、解析「内心独白：」「言行：」与「约束：」「本回合事件摘要：」；Orchestrator.from_config 注入 storage、runtime_config、characters_config/world_config。单元测试 mock LLM 覆盖解析分支；全量单元 95 通过。

**风险**
- 与 2026-02-16 相同；集成测试 test_orchestrator 中 6 个用例仍使用 scope_id=capital，若配置已改为其他 scope 需在测试中使用独立配置或恢复示例 scope。

---

### 二、关键任务进展（2026-02-17）

**本次修改**

| 任务 | 内容 | 测试 |
|------|------|------|
| 开书前设定阶段 | `src/author_loop/design_phase.py`：run_design_phase()；当 setting_research.trigger=design_only 时在 run_novel_with_author 回合前执行：运行设定研究 Agent → 展示世界/范围/角色/特殊设定摘要 → 作者 y/e/s（e 编辑后重载 world/characters 并再展示，曾选 e 则返回后主程序重载编排器）；config 新增 load_special_settings_config。 | test_design_phase（3 个），全量 93 通过（含本项；集成 test_orchestrator 6 失败为配置 scope 与用例不一致）。 |
| 关键角色与次要角色列表 | 配置仅列关键角色；Storage 新增 _secondary_characters、get_secondary_characters(scope_id, limit)、append_secondary_character；Retrieval 新增 format_secondary_characters_snippet；TurnContext.secondary_characters_snippet，build_turn_context_from_storage 注入；example_characters 注释、USAGE、TECH §7.2 更新。示例角色名改为张凡/李墨/王石头。 | test_storage（+4）、test_retrieval（+3）、test_context（+1），相关单元测试通过。 |
| 第 13 项 角色/范围 Agent 接 LLM | CharacterAgent：turn() 内拼 prompt（身份、记忆、场景）、调 get_llm_provider、解析内心独白/言行；ScopeAgent：拼 prompt（范围、最近事件、场景）、解析约束/事件摘要。Orchestrator 创建 Agent 时注入 storage、runtime_config、characters_config/world_config。无 LLM 或异常时回退壳输出。 | test_agent_shells 新增 TestCharacterAgentWithMockLLM、TestScopeAgentWithMockLLM；单元 95 通过。 |

---

## 2026-02-16

### 一、风险与进展（简要）

**进展**
- 单回合与多回合主流程已打通；**作者在环**（两阶段审阅、可先修改再确认）；全量测试 **90** 个用例通过。
- 第 1～**12** 项已完成：第 12 项 **LLM 接入** 已实现——OpenAI 兼容（openai 包）、**通义千问预设**（llm: tongyi/qwen，DashScope 默认 base_url/model）、文心一言 HTTP 直连（wenxin_provider）；配置与方案见 docs/design/llm-and-agents.md、docs/guides/usage.md。
- 设计文档（DESIGN.md、TECH_IMPLEMENTATION.md）、配置示例（world/characters/runtime/special_settings）、目录与工作日程已就绪。

**风险**

| 维度 | 风险 / 不足 |
|------|-------------|
| 设计验证 | 尚未经过实际写戏验证，回合粒度、作者交互频率是否合适需在实现后观察。 |
| 配置契约 | 配置与代码的契约（Schema）尚未用校验工具或类型约束，易出现配置错误。 |
| 记忆与存储 | 事件提炼的“时间线”与范围多对多关系、情感与关系的联动规则尚未细化，实现时需补。 |
| 作者在环 | CLI 已实现两阶段「可先修改再确认」（y/e/n，e 写入 author_edits 编辑后读回）；每回合都确认可能影响节奏，可考虑“批量确认”或后续 Web/API。 |
| 技术选型 | 尚未选定具体 LLM、向量库与持久化实现，依赖与性能未验证。 |
| 智能度 | 当前无任何 Agent 框架或大模型调用，角色/范围 Agent 均为壳（固定输出），智能度 0%。 |

---

### 二、关键任务进展

**已完成（2026-02-16）**

| 任务 | 内容 | 测试 |
|------|------|------|
| 第 1 项 配置与存储 | `src/config/`（load_yaml、三份配置加载、validate_runtime_and_ids、load_all_config）、`src/runtime/storage.py`（MemoryStorage，键结构 §7）。 | test_config、test_storage，全量 36 通过。 |
| 第 2 项 Context | `src/context/`（TurnContext、build_turn_context、build_turn_context_from_storage）。 | test_context（8 个），全量 44 通过。 |
| 第 3 项 单 Agent 壳 | `src/agents/character/`（CharacterTurnOutput、CharacterAgent.turn(ctx)）、`src/agents/world/`（ScopeTurnOutput、ScopeAgent.turn(ctx)）；固定输出，不接 LLM。 | test_agent_shells（4 个），全量 48 通过。 |
| 第 4 项 Orchestrator | `src/orchestrator/orchestrator.py`（Orchestrator.from_config()、run_one_turn：构建 Context → 并行调用 Agent → 写回事件簿/状态，返回 TurnResult；记忆留作者确认后写回）。 | test_orchestrator（3 个），全量 51 通过。 |
| 第 5 项 回合循环 | `run_n_turns(n, scope_id, time, place, present_character_ids, ...)` 多回合循环，同一 Storage 持久化；主流程入口 `run_novel.py`（默认 2 回合，MIN_AUTOBOOK_TURNS 可调）。 | test_orchestrator 多回合用例（2 个），全量 53 通过。 |
| 第 6 项 冲突裁决 | `resolve_turn_conflict(scope_output, character_outputs)` 简单规则合并 scope 摘要与各角色 dialogue_action（按 character_id 序，用 " \| " 连接）；run_one_turn 写回裁决后摘要。 | test_conflict_resolve（3 个），全量 56 通过。 |
| 第 7 项 作者在环 | run_one_turn(..., auto_write=False)；apply_event_and_state_write / apply_memory_write；src/author_loop（review_turn_result、review_memory_plan，返回 (bool, TurnResult)）；run_novel_with_author.py。**增强**：两阶段均提示「可先修改再确认」，支持 e 将内容写入 dev_agent/output/author_edits 编辑后读回；**开书前设定阶段**（design_only 时先与设定研究 Agent 沟通完善世界模型，y/e/s 交互，编辑后重载编排器）。 | test_author_loop（8）、test_design_phase（3）、集成 test_run_novel_with_author，全量 93 通过（集成 test_orchestrator 6 失败为配置与用例 scope 不一致）。 |
| 第 8 项 配套测试 | 全量回归 67 通过；新增 tests/integration/test_run_novel_with_author.py（作者在环主流程一回合、作者全同意）。 | 全量 68 通过。 |
| 第 9 项 DevAgent | 自我迭代机制：cursor_tasks 强化「测试未通过则修复/回滚」；搜索与联想扩展点 search_ideas（run_search_ideas 占位、search_ideas_enabled 配置）；单元测试 test_dev_agent_search_ideas。 | 全量 70 通过。 |
| 第 10 项 LLM 与检索 | 记忆与事件检索 `src/retrieval/`（已实现）；**LLM 层仅为空实现**（`src/llm/` 仅接口 + DummyLLM 占位，未接任何大模型 API 或 Agent 框架）；单元测试 test_retrieval、test_llm。 | 全量 81 通过。 |
| 第 11 项 设定研究 Agent | `src/agents/setting_research/agent.py`：SettingResearchAgent.run(theme, genre, reference, output_dir) 占位写 YAML 到 setting_research_output.yaml，返回 Path；未设 output_dir 抛 ValueError。单元测试 test_setting_research（3 个）。 | 全量 84 通过。 |
| 第 12 项 LLM 接入 | `src/llm/openai_provider.py`（OpenAI 兼容）、`src/llm/wenxin_provider.py`（文心 HTTP 直连）；`get_llm_provider` 支持 dummy / openai / tongyi / qwen / wenxin；**通义千问** 预设（llm: tongyi，DASHSCOPE_API_KEY、DashScope base_url、qwen-turbo）。配置示例与文档（`docs/design/llm-and-agents.md`、`docs/guides/usage.md`）更新；单测 test_llm 含 tongyi/wenxin。 | 全量 90 通过。 |
| 文档与计划 | next_plan.md、`docs/planning/next-iteration.md`、WORKLOG 已更新至第 12 项完成与下一步 13～15。 | — |

**本次修改（第 12 项完成 + 工作日志与下一步计划）**

- **第 12 项**：LLM 层真实 Provider（OpenAI 兼容、通义 tongyi 预设、文心直连）；配置 framework.llm / llm_options；方案与使用说明（`docs/design/llm-and-agents.md`、`docs/guides/usage.md`）以通义为首选；全量 90 通过。
- **工作日志与下一步**：WORKLOG 进展/任务表/代码现状/待办、NEXT_ITERATION 待办、next_plan 下一步均更新；第 12 项勾选完成，下一步为第 13～15 项。

**此前修改（第 11 项收尾、作者在环增强等）**

- **作者确认环节支持「先修改再确认」**：两阶段审阅不再仅“通过/驳回”，作者可先修改内容再确认。
- **CLI 行为**：阶段一、阶段二均增加提示「可先修改再确认」；选项改为 **y** 直接确认 / **e** 先修改（将内容写入 `dev_agent/output/author_edits/` 下文件，编辑后保存、回到 CLI 按回车读回）/ **n** 驳回或不写回。
- **返回值**：`review_turn_result`、`review_memory_plan` 改为返回 `(bool, TurnResult | None)`，写回事件簿/状态与角色记忆时使用作者确认或编辑后的 `TurnResult`。
- **实现**：`src/author_loop/cli.py` 增加回合结果与记忆计划的序列化/解析、`edit_output_dir` 参数；`run_novel_with_author.py` 传入 `edit_output_dir` 并使用两阶段返回的 result 做写回；`.gitignore` 增加 `dev_agent/output/author_edits/*`。
- **测试**：单元测试与集成测试适配新返回值；新增 `test_review_turn_result_edit_path_returns_modified_result`。全量 71 通过。

**待办（按 NEXT_ITERATION 顺序）**

- **第 14 项** 设定研究 Agent 充实：联网 + LLM 抽取，产出真实设定 YAML。
- **第 15 项** DevAgent search_ideas 充实：联网或调用设定研究，产出真实条目。

**可选 / 后续**

- 配置 Schema 校验（如 Pydantic 或 JSON Schema）与文档化。
- 细化“事件提炼”的时间线/范围维度及情感-关系联动规则（DESIGN 或 TECH 补充一节）。

---

### 三、代码实现与方案对比

**当前状态（第 1～17 项已完成）**

- **角色/范围 Agent**：turn() 已接 LLM（get_llm_provider、拼 prompt、解析输出）；无 LLM 或异常时回退壳输出。
- **设定研究 Agent**：run() 已接 LLM 产出 power_system/level_system；**按方向讨论** discuss_direction、extract_direction_yaml；design_phase 主菜单支持 **d 讨论某一方向**，仅 **y 设定完成** 才结束。
- **记忆与内容双写**：runtime.storage.data_root 配置时，编排器在 apply_event_and_state_write/apply_memory_write 中调用 file_sync，写入 content/turns、memory/scopes、memory/characters 及 README 索引（见 docs/design/memory-storage-and-retrieval.md）。
- **DevAgent**：纯脚本 + search_ideas（可读设定研究 YAML 或调设定研究产出真实条目）；改代码由 Cursor 协同完成。

**1. 代码现状（按模块）**

| 模块 | 路径 | 实现程度 | 说明 |
|------|------|----------|------|
| 配置 | `src/config/__init__.py` | ✅ 已实现 | load_yaml、三份配置加载、validate_runtime_and_ids、load_all_config、load_special_settings_config；Orchestrator.from_config() 已调用。 |
| 存储 | `src/runtime/storage.py` | ✅ 已实现 | MemoryStorage（键结构 §7）；编排器写回事件簿/状态/记忆已使用。 |
| 记忆与内容双写 | `src/runtime/file_sync.py` | ✅ 已实现 | get_data_root、next_turn_index、write_turn_content、sync_scope_turn、sync_character_turn、ensure_memory_root_readmes；编排器在 data_root 配置时于 apply_* 中调用。 |
| 上下文 | `src/context/__init__.py` | ✅ 已实现 | TurnContext、build_turn_context、build_turn_context_from_storage；编排器单回合已使用。 |
| 编排器 | `src/orchestrator/orchestrator.py` | ✅ 已实现 | run_one_turn(..., auto_write)、apply_event_and_state_write、apply_memory_write；from_config 解析 data_root；冲突裁决 → 写回；可选 file_sync 双写。 |
| 作者在环 | `src/author_loop/` | ✅ 已实现 | review_turn_result、review_memory_plan（阶段一/二）；y/e/n；**开书前设定阶段** run_design_phase（y/e/s/**d 按方向讨论**，仅 y 设定完成才结束）；CLI input_fn 可注入测试。 |
| 检索 | `src/retrieval/` | ✅ 已实现 | retrieve_character_memory、format_scope_events_snippet、format_secondary_characters_snippet；从 Storage 按角色/范围取记忆与事件，格式化为 prompt 片段。 |
| LLM 抽象 | `src/llm/` | ✅ 已实现 | LLMProvider + DummyLLM；OpenAI 兼容、通义（tongyi/qwen）、文心（wenxin）；get_llm_provider 按 framework.llm 返回；密钥仅环境变量。 |
| 角色 Agent | `src/agents/character/` | ✅ 已接 LLM | turn(ctx) 有 LLM 时拼 prompt（检索+角色设定）、调用 get_llm_provider、解析内心独白/言行；否则壳输出。 |
| 范围 Agent | `src/agents/world/` | ✅ 已接 LLM | turn(ctx) 有 LLM 时拼 prompt（事件摘要+范围设定）、调用 LLM、解析约束/事件摘要；否则壳输出。 |
| 设定研究 Agent | `src/agents/setting_research/` | ✅ 已接 LLM + 按方向讨论 | run() 接 LLM 写 power_system/level_system；discuss_direction、extract_direction_yaml；design_phase 主菜单 d → 满意后提炼进整体。联网检索留作后续。 |
| DevAgent | `src/agents/dev/` | ✅ 已实现 | 纯脚本：跑测试、写 cursor_tasks/next_plan；search_ideas 可读设定研究 YAML 或调设定研究产出 power_system.md、level_system.md。入口 `run_dev_agent.py`。 |

**2. 与方案对比（NEXT_ITERATION + TECH_IMPLEMENTATION）**

| 方案项 | 方案约定 | 当前实现 | 是否偏离 |
|--------|----------|----------|----------|
| 第 1 项 配置与存储 | 配置加载（YAML）、enabled_ids 校验；Storage 抽象（键结构 §7）。 | 已实现（config/、runtime/storage.py）。 | **否**。 |
| 第 2 项 Context | TurnContext 及构建方式（scope_id, time, place, present_character_ids, last_turn_summary 等）。 | 已实现（context/）。 | **否**。 |
| 第 3 项 单 Agent 壳 | CharacterAgent、ScopeAgent 壳，固定或规则输出，不接 LLM。 | 已实现（agents/character/、agents/world/），固定输出。 | **否**。 |
| 第 4 项 Orchestrator | 单回合流程，写回事件簿/状态，记忆留作者确认。 | 已实现；事件/状态可 auto_write 或作者同意后 apply_event_and_state_write；记忆由 apply_memory_write 在阶段二确认后写回。 | **否**。 |
| 第 7 项 作者在环 | 两阶段审阅与确认；作者可修改后确认（CLI 或 Web/API）。 | 已实现（author_loop/ CLI、run_novel_with_author.py）；支持可先修改再确认、e 写入文件编辑后读回。 | **否**。 |
| 第 9 项 DevAgent | 自我迭代机制，保持与主程序耦合。 | dev/ 已提前实现，纯脚本 + Cursor 协同。 | **否**。 |
| 第 10 项 LLM 与检索 | 记忆/事件检索、LLM 接入。 | 检索已实现；LLM 层已接入；角色/范围/设定研究 Agent 已在 turn() 或 run() 中调用 LLM。 | **否**。 |

**3. 入口与主流程**

- **run_novel_with_author.py**（作者在环主流程）：设定阶段（design_only 时 run_design_phase：y/e/s/**d 按方向讨论**，仅 y 才结束）→ n 回合循环（run_one_turn auto_write=False → review_turn_result → apply_event_and_state_write【含 file_sync 若 data_root】→ review_memory_plan → apply_memory_write【含 file_sync】）。详见本纪要「当前主程序分析」。
- **run_novel.py**（自动写回）：Orchestrator.from_config → run_n_turns(n, ...)，每回合 auto_write=True，仅写回事件/状态（若 data_root 则双写 content/turns、memory/scopes）；不写角色记忆。
- **run_dev_agent.py**：DevAgent 自我迭代（跑测试、写 cursor_tasks；search_ideas_enabled 时产出 search_ideas 真实条目）。

**4. 小结**

- **主流程打通度**：单回合与多回合 100%；作者在环已实现（两阶段审阅 + y/e/n + apply_event_and_state_write + apply_memory_write）；设定阶段支持按方向讨论（d）与仅 y 设定完成才结束；可选 data_root 双写 content/turns、memory/。
- **智能度**：LLM 层已接入；角色/范围/设定研究 Agent 均已接 LLM；检索与限长约定已用。
- **结论**：第 1～17 项已按顺序完成；当前无待办充实项（见 NEXT_ITERATION、docs/design/memory-storage-and-retrieval.md）。

**5. 壳功能清单与充实计划**

以下模块在代码中为**壳/占位**，接口与流程已就绪，待接入真实能力后才有“智能”产出。充实顺序建议按依赖与价值排序。

| 壳模块 | 代码路径 | 当前行为 | 充实方向（建议） |
|--------|----------|----------|------------------|
| **LLM 抽象** | `src/llm/` | 已实现：OpenAI 兼容、通义（tongyi）、文心（wenxin）；get_llm_provider 按 framework.llm 返回；默认 dummy。 | 第 13 项在 Agent turn() 中调用 get_llm_provider().generate()。 |
| **角色 Agent** | `src/agents/character/agent.py` | turn() 有 LLM 时拼 prompt、检索、调用 LLM、解析「内心独白：」「言行：」。 | 已实现；可再优化 prompt 模板与解析鲁棒性。 |
| **范围 Agent** | `src/agents/world/agent.py` | turn() 有 LLM 时拼 prompt、检索事件、调用 LLM、解析「约束：」「本回合事件摘要：」。 | 已实现；可再优化 prompt 与解析。 |
| **设定研究 Agent** | `src/agents/setting_research/agent.py` | `run()` 有 runtime_config 且非 DummyLLM 时调 get_llm_provider、拼 prompt、解析 YAML 写入 power_system/level_system 等；无 LLM 或异常时写占位 YAML。 | 联网检索留作后续扩展。 |
| **DevAgent search_ideas** | `src/agents/dev/search_ideas.py` | `run_search_ideas()` 可读 setting_research_output_path 或调设定研究 Agent，产出 power_system.md、level_system.md 等真实条目；无配置时占位。 | 可选：联网检索扩展条目类型。 |

**充实计划（第 12～17 项）**

- **第 12 项 LLM 接入**：已完成。真实 Provider（OpenAI 兼容、通义 tongyi 预设、文心直连）；framework.llm 支持 dummy | openai | tongyi | qwen | wenxin；单测覆盖。
- **第 13 项 角色/范围 Agent 接 LLM**：已完成。turn() 内拼 prompt（角色：身份+记忆+场景；范围：事件+场景）、调 get_llm_provider、解析为 CharacterTurnOutput/ScopeTurnOutput；Orchestrator 注入 storage/runtime_config/characters_config/world_config；mock LLM 单测通过。
- **第 14 项 设定研究 Agent 充实**：已完成。run() 接 LLM（_build_setting_prompt、_extract_yaml_block、_dict_to_yaml）、design_phase 传入 runtime_config；单测 mock get_llm_provider 通过；联网检索留作后续。
- **第 15 项 DevAgent search_ideas 充实**：已完成。run_search_ideas 支持 setting_research_output_path 或 theme + runtime_config_path 调用设定研究，产出 power_system.md、level_system.md 等真实条目；单测通过；单元 97。
- **第 16 项 设定阶段按方向讨论流程**：已完成。主菜单 d、按方向子循环、discuss_direction/extract_direction_yaml、仅 y 结束；单测通过，单元 98。
- **第 17 项 记忆与内容目录存储与检索**：已完成。file_sync 双写 content/turns、memory/scopes、memory/characters，README 索引；编排器在 data_root 配置时调用；单测 7 个，单元 105。

完成任一项后即在 `docs/planning/next-iteration.md` 勾选并更新本表。

---

*（本纪要每日在下方追加新日期条目，格式可沿用：日期 → 一、风险与进展 → 二、关键任务进展 → 三、代码实现与方案对比。）*
