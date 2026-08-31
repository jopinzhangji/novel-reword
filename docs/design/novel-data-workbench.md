# G4 SDD：Novel-Data 工作台（多小说进度 ⇄ 数据图谱 ⇄ 作者控制台）

**代号**：**G4**（承接 G1/G2/G3 已建的六类确定性数据面，把 D9 工作台从「草案」升级为可直接实现的整体前端）。
**类型**：SDD（L2，延展 **D9 novel-reader-ui.md**）。**登记**：**[SPEC_SDD.md](../framework/SPEC_SDD.md) D13**。**状态**：**文档闸 ✅**；编码 ⏳（首切片：后端确定性 Read API）。

> **一句话**：一个前端，三条主线——**多小说进度总览**（跨作品一眼），**单小说数据图谱**（关系/成长/视野/记忆/屏外/节拍六类可剖），**作者控制台**（作者在环交互 + 定制调整，复用 G3 能力表面与 D9 Session）。

---

## 1. 背景与目标

### 1.1 现状（代码落地事实）

- **数据已实建，前端未落**：G1/G2/G3 建好了六类**确定性、无 LLM、可测试**的数据面，D9（`novel-reader-ui.md`）只开了壳、并把 `角色成长` 等标为「远期」：
  | 数据面 | 落盘 / 计算 | 模块 |
  |--------|-----------|------|
  | 成长五维 + 迁移日志 | `book/characters/<id>/growth_state.yaml`（power/mind/social/goal/resource + transition_log） | `character_growth` |
  | 关系语义边 | `book/relationships/graph.yaml`（节点 + `co_presence/rival/hate/trust/debt/ally/mentor/love` 边 + status/intensity/evidence/change_log） | `relationship_graph`（`get_relation`/`get_neighbors`/`get_relation_change_log`） |
  | 信息视野 | `build_character_event_view`（已知 vs 未知计数） | `info_view` |
  | 大纲进度 + 节拍 | `book/outline/outline.yaml`（章/拍 intent/pace/tags/status）、`progress.yaml`（chapter/beat/turns_in_beat） | `outline_store` |
  | 记忆分层 | `book/characters/<id>/memories`（L1 事实 / L2 解释 / L3 策略+expires_turn） | `memory_layers` |
  | 屏外线/并列主线 | `book/characters/<id>/threads/{off_screen,parallel}_thread.yaml`（含 consumed 标记） | G1 `file_sync`/`character_growth` |
  | 能力开关 / 运行时镜头 / 备选稿 | `config/features.yaml`、`state/protagonist_runtime.yaml`、`state/drafts/` | `capabilities`/`protagonist_switch`/`alt_draft`（G3） |

- **D9 已定壳与栈**：多小说索引 `data/novels/index.yaml` + `config.current_novel_root`；IA（§5）；图组件（§9.1 `@xyflow/react`/`vis-network`）；前端目录与路由预留（§9.2）；API 面（§8）；W1–W6 排期。
- **缺口**：没有把「六类数据 → 可视图谱 → 作者可交互定制」串成同一前端；多小说「进度总览」未成页；作者控制台（定制调整）未接 G3 表面；后端 Read API 未建。

### 1.2 目标

1. **多小说进度总览**：顶部「作品索引」页，逐一列出 `data/novels/*` 的进度摘要（章节/节拍/回合、成长爆发计数、关系边数、最近写回回合），一眼对比所有小说。
2. **单小说数据图谱**：在该小说下，用六类数据面可剖的视图——关系全书谱/角色心图/角色对；人物情况（五维雷达 + 迁移日志时间线）；信息视野开关；记忆 L1/L2/L3 分层时间线；屏外线/并列主线；章节节拍情志条。
3. **作者控制台（定制调整 + 作者在环）**：复用 G3 表面——能力开关（`features.yaml`）、运行时镜头切换、候选备选稿生成/提升；叠加 D9 W3–W4 作者自由输入与单回合 plan→审阅→写回；`/system` 系统设置。
4. **可观测 / 不破船**：预览全部只读、确定性（无 LLM）；写回仅经 G3 `save_features`/`save_protagonist_context`/`alt_draft`/D9 白名单。

### 1.3 非目标

- 不在本 SDD 内实现平行整树多镜头成文（沿 G3「单导出镜头 + 单章备选稿替稿」）。
- 不重建领域模型；所有视图**只委托既有确定性模块**（`outline_store`/`relationship_graph`/`character_growth`/`info_view`/`memory_layers`/`file_sync`/G3 三件套）。
- 不把 Web Session 当回合引擎重写；作者在环驱动仍走 `run_novel_with_author`/`run_design_phase` 的既有回环（D9 §10 互斥模式）。

---

## 2. 术语

| 术语 | 含义 |
|------|------|
| **作品索引（novels index）** | `data/novels/index.yaml` + `config/current_novel_root`：列出全部小说与其当前目录，多小说切换的依据。 |
| **数据图谱（data graph）** | 把某类确定性数据剖面为可交互视图（力导向图、雷达、时间线、节拍条、信息视野开关），只读、无 LLM。 |
| **作者控制台（author console）** | 与作者双向的车台：自由输入 / 回合审阅（D9 Session）+ 定制调整（G3 能力开关、镜头切换、备选稿）。 |
| **回环（loop）幂同** | Web 端不重写引擎；`AWAIT_AUTHOR` 时由 Session 通知前端，作者输入回写同一 `pending_prompt` 通道（D9 §8.4 `WebInputAdapter`）。 |

---

## 3. 信息架构（多小说 → 单小说 → 控制台）

```
App Shell（D9 §5.1）
├─ /novels                 作品索引：全部小说进度卡片（多小说总览）★G4新增
└─ /novels/:slug           单小说工作台
   ├─ /:slug/dashboard     首页：进度 + 各图谱摘要卡
   ├─ /:slug/graph         关系图谱：全书力导 / 角色心图(dfocus) / 角色对(pair)
   ├─ /:slug/characters   人物情况：五维雷达 + 迁移日志 + 信息视野 + 记忆L1/L2/L3 + 屏外线
   ├─ /:slug/rhythm        章节节拍情志条（章/拍 intent/pace/tags + 进度指针）
   ├─ /:slug/console       作者控制台★G4：作者在环自由输入 + 定制调整（能力/镜头/备选稿）
   └─ /system              系统设置（D9 §5.6：LLM/工作台/联网）
```

**跨页联动（D9 §5.3 之上）**：在 `graph` 选中角色 → 跳 `characters/:id` 同角色；在 `rhythm` 选节拍 → `dashboard` 进度指针联动；在 `console` 开关某能力 → `dashboard` 相应摘要卡实时更新（`resolve_features` 重算）。

---

## 4. 数据 → 视图映射（六类数据面 × 可视化组件）

| 视图 | 数据源（模块委托） | 可视化 |
|------|-------------------|--------|
| **多小说进度卡片** | `index.yaml`×各 novel `progress.yaml`+`growth`+`graph` | 卡片：slug/当前章·拍·回合/成长爆发计数/关系边数/最近回合 |
| **关系·全书谱** | `relationship_graph.load_graph`（全量 nodes/edges） | `@xyflow` 力导向；边按 `type` 着色、`intensity` 粗细、`status=inactive` 虚线 |
| **关系·角色心图** | `get_neighbors(graph, id, 1~2跳)` | ego 图（中心突出，1~2 跳限制，防爆炸） |
| **关系·角色对** | `get_relation` + `get_relation_change_log` | 对卡：当前 type/status + 时间线 `change_log`（回合+原因） |
| **人物·成长五维** | `growth_state.yaml`（五维 dict + transition_log） | 雷达（五维计数封顶）+ 条形 + 迁移规则时间线 |
| **人物·信息视野** | `info_view.build_character_event_view` | 每角色「已知 vs 未知」开关（全局事件×该角色视野） |
| **人物·记忆分层** | `book/characters/<id>/memories`（L1/L2/L3） | 分层时间线；L3 标 `expires_turn` 期效 |
| **人物·屏外线** | `threads/{off_screen,parallel}_thread.yaml`（含 consumed） | 并列线程列表：未消费/已消费、桥接来源标记 |
| **章节·情志节拍** | `outline.yaml` beats（intent/pace/tags/status）+ `progress.yaml` 指针 | 章/拍情志条：`pace` 颜色带 + `tags` 徽章 + 进度指针 |

> 所有视图 **只读 + 确定性**：后端 Read API 委托既有模块，无 LLM，可单测（不破船）。
>
> **落盘现实（G4a 已核实）**：盘上持久化的是 **L1 事实**（`book/characters/<id>/events/turn_*.md` 与 scope 事件）与**屏外线**（`threads/off_screen.yaml`）；**L2 解释 / L3 策略 与 平行主线线程为运行期内存态（`MemoryStorage`），未落盘**。工作台镜像此现实：记忆视图给盘上 L1 分层时间线，并标 `runtime_only_layers: true`（前端刻意展示「会话内可见」，不虚构跨重启记忆）；平行主线同此前端报运行期态。**不做**为此新增 L2/L3 持久化（超出 G4 只读视野范围，留后续）。

---

## 5. 后端 Read Api 面（首切片，纯确定性，可直接实现）

> **G4a 落地位置（2026-08-31）**：确定性服务层实作在 **`src/workbench/`**（纯 Python、无 LLM 无 Web 依赖、可单测）；下表各 Router 由 G4b 的 FastAPI router **对 `src/workbench/` 同名模块做薄包装**即可，不再重复实现聚合逻辑。

`web/api/routers/` 下（沿用 D9 §9.2 目录）：

| Router | 端点 | 委托 |
|--------|------|------|
| `novels.py` | `GET /novels`（索引+各进度摘要）；`GET /novels/:slug/summary` | `index.yaml`、`outline_store`、`relationship_graph`、`character_growth` 聚合 |
| `graph.py` | `GET /novels/:slug/graph`（全量）；`?center=id&hops=2`（心图）；`/pair?a=&b=`（对+change_log） | `relationship_graph` |
| `characters.py` | `GET /novels/:slug/characters/:id`（成长五维+transition_log）；`/view`（信息视野）；`/memories`（L1/L2/L3）；`/threads`（屏外线） | `character_growth`/`info_view`/`memory_layers`/`file_sync` |
| `outline.py` | `GET /novels/:slug/outline` + `/progress`（情志节拍条+指针） | `outline_store` |
| `console.py`（★G4） | `GET /novels/:slug/console`（当前镜头/能力面/待提升备选稿）；`PATCH /features`（写 `save_features`）；`PUT /protagonist`（切换镜头）；`GET/POST /drafts`（列/生成）、`POST /drafts/:lens/promote` | G3 `capabilities`/`protagonist_switch`/`alt_draft` |
| `session.py` | 沿用 D9 §8.3（`pending_prompt`/`submit`/`events` 作者在环） | 既有回环壳 |

**单测（首切片验收）**：每 Read 端点对临时 novel 数据仓库（写 `growth_state.yaml`/`graph.yaml`/`progress.yaml`/L1–L3/threads）断言返回结构；`console` 写口断言 `features.yaml`/`protagonist_runtime.yaml`/`drafts` 落盘与 `resolve_features`/`effective_protagonist` 读到。无 LLM，全部绿。

---

## 6. 作者控制台（定制调整 + 作者在环）

> **G4c 落地位置（2026-08-31）**：作者在环会话与互斥门已编码——`src/author_harness/workbench_ingress.py`（`WebInputAdapter` 阻塞式 pending→reply 桥 + `LogOnlyAuthorIngress` 仅日志入口）、`web/api/session_runner.py`（`WorkbenchSession` 后台线程跑 `run_novel_with_author.main(input_fn=adapter.read)` + `SessionRegistry` data_root 一地对一新会话锁）、`web/api/routers/session.py`（建/pending/reply/abort/delete；已活跃 data_root 建会 409）。互斥门 `author_workbench.enabled`（默认 `false`）在 `config/novel_writing.yaml`，CLI 直跑且 `enabled=true` 时经 `LogOnlyAuthorIngress` 不读 stdin、仅打印 `[作者在环] AWAIT_AUTHOR` 日志（见 `run_novel_with_author.main` 顶部互斥门）。写口仍走 G3 白名单。

### 6.1 单交互通道（互斥：前端打开 ⇒ 终端对作者交互静默）

**作者控制台是当前作者交互的**唯一入口（D9 §5.5「互斥模式」）：`author_workbench.enabled=true` 时，
**作者的一切交互只在前端进行，终端不再参与作者交互**：

| `enabled` | 作者控制交互在哪 | 终端表现 |
|-----------|-----------------|---------|
| **`false`**（默认） | CLI（`AuthorSession.read_line`） | 完整菜单，照常输出 |
| **`true`** | **仅前端**（`WebInputAdapter` → Session `pending_prompt`） | **不弹作者菜单、不读 stdin、不阻塞等待**；仅 `INFO/WARN` 日志与 `[作者在环] AWAIT_AUTHOR`（正文），避免「双入口混乱」 |

落地要点（**MUST**）：
1. **路由到前端的作者交互全清单**：CLI 里所有 `read_line` 作者交互点——设定讨论、作者自由输入、回合审阅（`review_turn_result`/`review_memory_plan`）、**大纲推进菜单**、以及 **G3 镜头/开关/备选稿菜单**、G1 桥接/批处理确认、重试驳回——在 `enabled=true` 时一律经 `WebInputAdapter` 输入，`pending_prompt` 推给前端，前端作答回写同通道；终端不打印这些菜单文案、不等待。
2. **终端仅日志**：阶段/写回/Harness 字段/`[大纲进度]` 仍打终端（可观测），但**任何作者交互 prompt 不出现**；CLI 走 `LogOnlyAuthorIngress`（不抢 stdin）。
3. **至多一个活跃 Session 绑一本 data_root**（文件锁 / 409），防双写（D9 §5.5 MUST 2）。

### 6.2 定制调整（复用 G3）

| 前端动作 | G3 表面 | 写点 |
|---------|--------|------|
| 开/关某能力 | `resolve_features`+`save_features` | `config/features.yaml`（下一回合 `resolve_features` 生效） |
| 切换导出镜头 | `switch_protagonist`+`save_protagonist_context` | `state/protagonist_runtime.yaml`（前向；演进不动） |
| 生成/提升备选稿 | `write_alt_draft`/`promote_alt_draft` | `state/drafts/` +（提升）替稿并切镜头 |

### 6.3 作者在环（沿用 D9 W3–W4）

Session `pending_prompt` → 前端输入 → `WebInputAdapter` → 既有回环执行 plan→审阅→写回；`/system` 管理 LLM/工作台/联网。**若目标约束**：Web 不重写引擎；所有写口仍走 G3 白名单与 D9 白名单键，S2 行为（超时重试/检索/写回门闩）与 CLI 时代完全一致。

---

## 7. 分阶段落地

| 阶段 | 内容 | 验收 |
|------|------|------|
| **G4 文档闸** | 本 SDD + D13 登记 + next-iteration 标注 + WORKLOG | ✅（2026-08-31） |
| **G4a 后端 Read Api**（首选可交付） | `novels`/`graph`/`characters`/`outline`/`console` Read 与写口（全委托既有模块） | 单测全绿；无 LLM；多小说/单小说/控制台三类断言 ✅（2026-08-31：`src/workbench/` 服务层 20 单测 + 全量 **395 通过 + 1 跳过**；FastAPI router 留 G4b 薄包装） |
| **G4b 前端壳 + 图谱页** | 承接 D9 W1–W2；顶置作品索引 + 各数据图谱组件（力导/雷达/时间线/节拍条/信息视野） | 浏览器可查看多小说进度与单小说六类图谱（读 G4a） ✅（2026-08-31：`web/api/app.py` FastAPI 工厂 + 五 router 薄包装 `src/workbench/` + `web/static/index.html` 无构建静态仪表盘；10 条 TestClient 单测，全量 **405 通过 + 1 跳过**；React/Vite 前端仍留 W 系列替换静态页） |
| **G4c 作者控制台** | 定制调整（能力/镜头/备选稿）写口 + Session 作者在环（W3–W4） | 浏览器内改能力/切镜头/升备选稿生效；作者自由输入回合审阅；**互斥：`author_workbench.enabled=true` 时终端不弹作者菜单、不读 stdin，交互只在前端**（G3/大纲推进/审阅 prompt 全走前端） ✅（2026-08-31：`WebInputAdapter`/`LogOnlyAuthorIngress` + `WorkbenchSession`/`SessionRegistry` + `session.py` router（409 互斥 + pending/reply/abort/delete）；11 条单测，全量 **416 通过 + 1 跳过**） |

---

## 8. 与既有设计 / 代码接线

- [novel-reader-ui.md](./novel-reader-ui.md)（D9）：**IA 壳 + 栈 + 目录 + Session/`/system`** 本 SDD 直接沿用；D9 §4 中标注「远期」的「角色成长/关系」现因 G1/G2 已成，全部可落；**D9 §5.5/§8.4/§10「互斥：`author_workbench.enabled=true` 时前端为唯一作者交互入口、终端静默」为本设计 §6.1 的 SSOT**。
- [user-adjustable-and-runtime-lens.md](./user-adjustable-and-runtime-lens.md)（D12）：**G3 能力表面/镜头/备选稿 = 作者控制台三写点**，本 SDD 只做前端调用方。
- [parallel-thread-bridging.md](./parallel-thread-bridging.md)（D10）：屏外线/并列主线视图数据源。
- [character-growth-state-machine.md](./character-growth-state-machine.md)：成长五维 + 迁移规则（雷达/时间线数据源）。
- [SPEC_SDD.md](../framework/SPEC_SDD.md)：**D13**；[next-iteration.md](../planning/next-iteration.md)：「小说作者在环工作台（D9）」承接主线。

---

## 9. 不做（留后续）

- Web 叠代整树多镜头成文（仍 G3「单导出镜头 + 单章备选稿」）。
- 六类数据之外的实时流式/冲突检测等新领域模型（本 SDD 只读既有数据）。
- 前端以外的桌面/移动双端（先从 Web 单端 W1–W4）。

---

## 10. 修订记录

- **2026-08-31**：G4 SDD 初稿；登记 **D13**；承接 D9 壳与 G1/G2/G3 六类数据面；明确「多小说进度 ⇄ 数据图谱 ⇄ 作者控制台」三主线。