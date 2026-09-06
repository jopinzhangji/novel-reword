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

### 6.4 `/system` 系统设置面板（W3 可写，GG5，2026-08-31）

承接 D9 §5.6「`/system` 管理 LLM/工作台/联网」。**读写契约**：

| 键 | 路径（effective） | 读 | 写 |
|----|------------------|----|----|
| **工作台互斥** | `runtime.runtime.author_workbench.enabled` | ✔ | ✔ 布尔开关（`author_workbench_enabled`） |
| **联网检索** | `runtime.runtime.author_harness.internet_search`（enabled/provider/max_chars/trust_level） | ✔ | ✔ 白名单四键 |
| **LLM 提供方（工作参数）** | `framework.llm` + `framework.llm_options`（openai_compatible/火山方舟） | ✔ 读写 | ✔ **白名单五子键**（v2）：`model` / `base_url` / `timeout` / `max_retries` / `api_key_env`（见下 ⚠） |
| **LLM 提供方（provider 类型）** | `framework.llm`（`dummy`/`openai_compatible`/…） | ✔ 只读展示 | ✘ **只读**——真实提供方由环境 `.env`/密钥驱动（见 [LLM_AND_AGENT_DESIGN.md](../../docs/LLM_AND_AGENT_DESIGN.md)），运行时中途改 provider 类型易断链，故类型本身仍只读不改写 |

**持久化写口**：与 G3 features.yaml 同构——写 **per-novel** `data/novels/<slug>/config/runtime.yaml`，`load_runtime_config` 的 per-novel `deep_merge` 覆盖即可生效。**只写白名单键、合并保留既有键**（如 e2e 的 `runtime.novel_run`），**不动 `config/*.yaml` canonical 文件**；删除该 override 键即回默认。
- **运行时组**（`author_workbench` / `author_harness.internet_search`）写 **顶层 `runtime:`** 下（沿用 G3/G4c）。
- **LLM 工作参数组**（`framework.llm_options`）写 **顶层 `framework:`** 下——**区别于运行时组的 `runtime:` 包装**，因为 `_framework_info`/`load_runtime_config` 读的是 **top-level `framework`**（e2e per-novel `runtime.yaml` 顶层为 `setting_research/agents/runtime`，本就无 `runtime:` 外层 wrapper）。merge：`model`/`base_url`/`timeout`/`max_retries`/`api_key_env` 逐个深合并进 `framework.llm_options`，**保留既有 `framework.llm` 与其它 llm_options**。

**生效边界**：设置由 `load_runtime_config` 在 `run_novel_with_author.main` 启动时快照 → 改后**下一会话/重启生效**，不逐回合热改（诚实标注，不假装即时生效）。⚠ `api_key_env` 写的是**环境变量名**（非密钥明文，key 本身仍只读展示）；改后须确保该环境变量在 `.env`/shell 中已提供，否则下一会话真实 LLM 会断链——文档如实提示，不静默兜底。

**前端**：静态面板 `web/static/index.html`「系统」分区——按钮切换显示，GET `/api/system` 渲染（当前书/LLM 只读卡/workbench 开关/internet 开关+provider+max_chars+trust_level），任一改动作 PATCH 后 GET 刷新。

### 6.5 远程访问与鉴权（GG6，2026-08-31）

工作台默认 `uvicorn` **loopback（127.0.0.1）仅本机**；要局域网/公网访问，host/port 与密码登录**可配置**（独立于小说运行时配置）。

**新增 `config/web_api.yaml`（web 服务层专用）：**

```yaml
# web/api 服务层配置（独立于小说运行时配置；控制监听与远程鉴权）
server:
  host: "127.0.0.1"   # 默认仅本机；改 "0.0.0.0" 允许局域网/公网监听（见下方⚠）
  port: 8000
auth:
  enabled: false      # 默认关（本地直访/现有单测不破）；true 则全站 HTTP Basic Auth
  username: ""        # enabled=true 时必填
  password: ""        # enabled=true 时必填；明文存（本地/局域网自用），公网建议反代/OAuth（见⚠）
  realm: "Novel-Data Workbench"
```

- **生效**：`web/api/app.py::create_app(project_root)` 启动时读本项目 `config/web_api.yaml`，`auth.enabled=true` 时挂全站 Basic Auth **中间件**（`WWW-Authenticate: Basic`，浏览器原生弹「密码登录」）——`/api/*` 与静态页一并保护；`verify_credentials` 用 `hmac.compare_digest` 常量时间比较。`auth.enabled=true` 但 username/password 为空 → **启动即报错**（`web/api/server.py` fail-fast），绝不静默无鉴权裸奔。
- **可配监听**：`python -m web.api.server` 读 `server.host/port` 直接 `uvicorn.run`（免手敲 `--host`）。默认仍 127.0.0.1；本机自用无需改。
- **⚠ 暴露边界（诚实标注）**：app **无 OAuth/CORS 层**，若 `auth.enabled=false` 且 `host=0.0.0.0` = 全写口裸奔。`enabled=true` 的 Basic Auth 密码为**服务器明文共享口令**，只适合单作者局域网/反代后自用，**不建议直接对公网**；公网暴露请前置 nginx/caddy 反代 + 更强认证，或用 ssh 隧道（`ssh -L 8000:127.0.0.1:8000 用户@主机`）零暴露写口。

### 6.6 工作台面板补全（GG-W，2026-08-31 起，逐项 #2-#5）

数据源全部复用 §4/§6 既有确定性模块，纯前端渲染 + 必要薄读口，**default 不破**（船身不破）。**#2 五维成长雷达图 ✅（2026-08-31）**，继续 #3。

**#2 五维成长雷达图**：
- **数据源**：`character_detail.growth` 五维 `power/mind/social/goal/resource` 均为 `dict[str,int]`（子状态计数，cap≈3–5）。
- **确定性打分口径（新增后端 `growth_radar`，进 `character_detail`）**：对每维 `intensity = Σ(子状态值)`，`level = min(1.0, intensity / 6)`（**成长深度 0..1**，四舍五入 3 位）。语义为「成长深度」**非绝对特质分**（诚实标注：无状态=0、多个成熟子状态=1）；`GROWTH_DEPTH_SCALE=6` 为可调常量。返回 5 项 `{dim,label,level,intensity,attributes}`。
- **前端**：人物卡内嵌迷你 SVG 雷达（5 顶点多边形 + 网格 + 维度标签 + level 数值），依据 `d.growth_radar`。
- **验收**：`GET /api/novels/{slug}/characters/{id}` 返回 `growth_radar` 5 项、每项 `0≤level≤1`；空成长全 0；无 LLM；全量回归保持绿。

**#3 迁移日志时间线 ✅（2026-08-31，纯前端）**：
- **数据源**：`character_detail.growth.transition_log`（`apply_growth_transition`/`apply_growth_transition_guarded` 写入，cap 100 条）——两类条目：
  - **成长命中**：`{rule, turn, scope_id, reason(≤120字), deltas:[{rule,dim,key,value,note}]}`；
  - **guard 审计**：`{rule:"guard.clamp"/"guard.skip", turn, scope_id, reason, guard, action, guard_reason}`。
- **渲染**：人物卡内按 `turn` 升序时间线展开（章节/回合 + 规则名 → 维度 label + key ±value + reason；guard 条目加「钳制/跳过」徽标 + guard_reason）。纯前端，无新读口。
- **验收**：`GET /api/.../characters/{id}` 返回 `growth.transition_log`，卡片按 turn 顺序渲染两类条目；空日志显示「无迁移记录」；无 LLM；全量回归保持绿。

**#4 L1记忆·屏外线时间线 ✅（2026-08-31，纯前端）**：
- **数据源**：`character_detail.memories_l1`（`character_events_on_disk`：`[{turn_file, summary, layer}]`，L1 事实已落盘）+ `character_detail.off_screen_threads`（`load_off_screen_threads`：屏外线程条目 `[{summary, thread?, turn_index?, scope_id?, consumed?}]`）。
- **渲染**：人物卡内分两节——**L1 记忆**（按 turn_file 序，条目 summary + layer 徽标）+ **屏外线**（每条 summary + thread 标签 + turn_index + 已消费/待消费徽标）。纯前端，无新读口；`runtime_only_layers` 标注保留。
- **验收**：`GET /api/.../characters/{id}` 返回 `memories_l1`/`off_screen_threads`，卡片两节时间线渲染；空列表显示「无…」；无 LLM；全量回归保持绿。

**#5 跨卡联动 ✅（2026-08-31，纯前端）**：
- **动机**：人物卡（成长·记忆·视野·屏外、雷达、迁移时间线）与关系图谱各卡独立加载，缺少「点谁看谁」的焦点联动。
- **方案**：共享焦点 `focusChar`（全局）：点**人物卡标题**或**关系图节点** → `focusPerson(id)`——①高亮/聚焦该人物卡（`.focus` 边框、其余 `.dim` 降强调度、滚入视野）；②把图表 `egoCenter` 设为该角色并重绘 ego 一跳心图（关系图谱联动）。「全部角色」按钮 `clearFocus()` 复位全grid + 全书谱。
- **边界（诚实）**：**节拍/情志条为章节级场景数据**（outline beat 无按角色在场指针），故不走人物焦点过滤；跨卡联动作用域为**人物卡(成长/记忆/视野/屏外/雷达/时间线) ⇄ 关系图谱**，皆数据就绪的确定性 pane。角色级节拍过滤需新增 beat→characters 读口，留后续。
- **验收**：单小说内点人物卡/关系节点 → 对应卡高亮聚焦 + 心图跳到该角色；「全部角色」复位；全量回归保持绿。

**#6 两栏布局 + 控制台终端输出 / 小说正文 ✅（2026-09-01，前端布局 + 确定性读口）**：
- **动机**：工作台原先在选中一本小说后把 `进度/关系/人物/节拍/控制台/系统` **全部纵向堆叠**同时显示，靠整页滚动查看；用户要求改为**左导航栏列各维度、右侧呈现所选维度数据**的两栏布局，且**切到「控制台」时右侧同时呈现整体终端输出**与**小说正文情况**。
- **前端布局（纯前端，无构建）**：`<main>` 改两栏 CSS grid——左**维度导航**（总览 / 进度 / 关系 / 人物 / 章节节拍 / **控制台** / 系统），右**内容区**仅渲染激活维度（`showDim` 切换、其余隐藏），**懒加载**（切维度才拉对应数据），默认激活「总览」。header 保留小说下拉与系统。
- **控制台维度右侧三区**：① 作者在环 `sessionBox`（G4c 既有）② **终端输出**——渲染会话 `state().stream`（会话期缓冲的引擎日志尾部，见下）③ **小说正文情况**——`GET /api/novels/{slug}/story`，按 turn 陈列摘要 + 正文 body，顶部当前章/拍指针。
- **后端（确定性、只读、无 LLM）**：
  - **终端输出 tail（`session_runner.py`）**：`WorkbenchSession` 在 `start()` 时给**根 logger** 挂 `_StreamTailHandler`（定长 deque≈300 行，内存态），`_run_guard` finally / `abort()` 移除（防泄漏）；`state()` 增 `stream` 字段。**只读观测、不改变在环/互斥语义**——无会话时不挂、挂上也仅多一个 stream 字段。
  - **小说正文 read port（`workbench/novels.py::story_events` + `routers/novels.py`）**：复用 `file_sync.load_scope_events_from_disk`，按 turn 倒序取 `summary + body`（`## 正文` 段），配 `outline_pointer` 作当前位置；不动正文磁盘。
- **诚实标注**：**正文以 scope 事件 `## 正文` 段为准**；测试/样例小说多只有摘要（body 空），真小说才有正文章节。实时 LLM 流式/彩色终端不在本切片（会话期日志尾部概览已足）。
- **验收**：`node --check` 抽 JS 通过；两栏布局切维度只显示对应 pane；控制台含终端输出（会话期日志尾部）+ 正文区（事件体/中文摘要）；`GET /api/novels/{slug}/story` 返回 body；无 LLM；全量回归保持绿。

### 6.8 在线书名编辑 + LLM 工作参数可写（2026-09-06）

用户要求：**「（初稿）待命名」的小说可以在工作台在线命名**；**对应系统配置（LLM 工作参数）也可以在线修改**。承 §6.4（LLM 白名单）+ §4 作品索引。

**① 在线书名编辑（rename，确定性写口）**：

- `src/workbench/novels.py::rename_novel(project_root, slug, title)`——校验书名非空；`slugify_title(title)` 生成新 slug，目录名冲突递增后缀；目录重命名（`novel_root.rename`）后同步写三处：
  - `meta.yaml`：`title` + `slug`（status 不变，draft 仍是 draft）；
  - `data/novels/index.yaml`：按**旧 slug** 移除旧行、按新 slug 追加 `{slug,title,status,updated_at}`；
  - `config/current_novel.yaml`（仓库级）：若指针指向该 slug/root 则更新 `slug/title/root`（`provisional=False`）。
- 复用 `novel_identity.slugify_title`，与主流程命名口径一致；**只改身份元数据，不触碰 `book/`/`config/*.yaml` 写作产物**。
- `web/api/routers/novels.py`：新增 `PATCH /api/novels/{slug}/rename`（body `{title}`），校验后返回新 `{slug, title, root}`。
- **前端**：总览/进度页当前书名词条内嵌可编辑输入 + 保存；保存后提示并重载作品索引（slug 可能因命名变化）。

**② LLM 工作参数可写（白名单，v2 取代 v1 只读）**：见 §6.4 表 + 写口。仍**保持 `framework.readonly=false`**，但**提供方类型（`framework.llm`）与密钥值本身仍只读**——Web 层返回 `options` 中 `model/base_url/timeout/max_retries/api_key_env` 可写字段，PATCH `/api/system` 传 `{"framework": {...}}` 落 top-level `framework.llm_options`。

- **验收**：`PATCH /api/novels/{slug}/rename` 改书名真实落盘 meta/index/current_novel，slug 变化时目录改名；`system_status` 的 `framework.readonly=false`；`PATCH /api/system`（`framework`）落 per-novel `runtime.yaml` 顶层 `framework.llm_options` 且保留既有 `framework.llm`；无 LLM、无真实密钥写盘；全量回归保持绿。

### 6.9 简介种子 + 控制台「设定讨论 / 设定情况」面板（2026-09-06）

用户要求：**新小说命名后应引导填写简介，设定讨论由该简介先初始化一个设定**；**界面上应显示本阶段讨论/设定情况（已生成设定），而非让作者看终端输出**（终端输出降级为出错时详查）。承 §4 作品索引 + §6.7 控制台。

**① 简介（synopsis）作设定种子（顺序微调不重排阶段）**：
- **持久化**：`meta.yaml` 增 `synopsis` 字段（空串默认）。`novel_identity.py` 三处写 meta（`_ensure_provisional_novel_directory` / `_finalize_draft_novel_identity` / `persist_novel_identity`）均带 `synopsis`；**`_finalize_draft_novel_identity` 整表重建 meta 时保留既有 synopsis**；`rename_novel` 用 `{**meta,...}` 天然保留。新增 `read_synopsis`/`write_synopsis`（非空截断 500 字）。`workbench/common.novel_meta` 透出 `synopsis`。
- **采集时机**：`run_novel_with_author.main` 在设定讨论前，若本小说 `synopsis` 为空**且尚无 `config/design_session.yaml`**（避免续跑/讨论中打扰），用 `input_fn` 引导「请填写小说简介（一句话设定，可回车跳过）」，非空则持久化并作种子（本轮内不重复问）。
- **种子接入**：`design_phase.run_design_phase(..., synopsis=None)` 初始化 `reference = synopsis`；`_prompt_author_intent_for_setting_research` 增 `seed` 参——作者给 intent → `seed+"\n"+idea`；回车 → `seed`；无 seed → 原占位。正式命名仍「设定完成后」由设定生成书名候选（作者亦可随时在线改名）。

**② 设定讨论 / 设定情况面板（确定性读口，无 LLM）**：
- `src/workbench/discussion.py::discussion_snapshot(novel_root)` 返回：`phase`（`config/author_interaction_state.yaml` 的 `phase_state.phase/subphase`）、`synopsis`（meta）、`world`（复用 `load_world_config` 的 world.name/era/rules + scopes）、`settings`（`setting_research_output.yaml` 每 direction → `{name,description,levels_count,chapters_count}`）、`discussion_summary`（`design_session.yaml` 的 summary/last_updated/session_file）、**`suggestion`（确定性当前建议**：据 阶段/简介/世界/设定方向 推导下一步，无 LLM）、**`status`（紧凑情况摘要**：`has_synopsis`/`world_filled`/`direction_count`/`directions_with_detail`/`design_session_present`，供面板顶部「当前设定情况」）。全缺安全空。
- `web/api/routers/novels.py`：`GET /api/novels/{slug}/discussion`；`GET /api/novels/{slug}/discussion/archive`；`PATCH /api/novels/{slug}/synopsis`（body `{text}`，写 meta.yaml）。
- **归档讨论下钻（独立分区 + 可点进完整对话）**：`discussion.py::archived_discussion_detail(novel_root)`——索引 `design_session.yaml` 只存摘要+`session_file`，完整对话落盘 `book/setting/sessions/session_<ts>.md`（及同名 `.yaml`）。读口优先读结构化 `.yaml` 的 `events` 规整为 `blocks`（`discussion` 发起+逐轮 author/agent+归纳方向 / `summary` world/scopes/characters/special / menu/supplement）；仅存 `.md` 回退原文 `raw_markdown`；全缺只回索引摘要。`session_file` 相对 data_root 解析并校验落在 novel_root 内（防越权）。前端把**最近归档讨论单独成区**（总结常驻）+「查看归档详情 ▾/收起 ▴」点击下钻展开完整对话（首次拉取、缓存跨轮询、切小说重置）。
- **前端**（`web/static/index.html` 无构建）：控制台 `sessionBox` 之后、终端之前插入「设定讨论 / 设定情况」`#discussionBox`。面板顶部渲染**阶段徽标 + 当前设定情况（`status` 紧凑摘要） + 当前建议（`suggestion`）**；下方 `<details open>`「查看详细情况（下转）」内含简介(可编辑保存) + world + 设定方向卡 + 最近归档讨论摘要。`runDim("console")` 与每次 session 轮询后轻刷（best-effort，读盘确定性）。**终端输出降级**：`termBox` 外包 `<details><summary>终端输出（出错时展开详查）</summary>`，默认收起，`renderSession` 照常写内容。
- **诚实标注**：面板呈现的是**已落盘的设定/已归档讨论**（`setting_research_output.yaml`/`world.yaml`/`design_session.yaml`），进行中的单轮原文仍以 `pending_prompt` 呈现，不即时回传引擎线内 conversation（Option-1 已足，实时原文留后续）。

- **验收**：新小说进作者在环先被引导填简介→`meta.yaml.synopsis` 落盘→`run_design_phase` 首轮 reference 含该简介；`GET /api/novels/{slug}/discussion` 返回 phase/synopsis/world/settings/discussion_summary；`PATCH /api/novels/{slug}/synopsis` 落盘；控制台面板展示设定情况、终端默认收起、可展开详查；无 LLM；全量回归保持绿。

---

## 7. 分阶段落地

| 阶段 | 内容 | 验收 |
|------|------|------|
| **G4 文档闸** | 本 SDD + D13 登记 + next-iteration 标注 + WORKLOG | ✅（2026-08-31） |
| **G4a 后端 Read Api**（首选可交付） | `novels`/`graph`/`characters`/`outline`/`console` Read 与写口（全委托既有模块） | 单测全绿；无 LLM；多小说/单小说/控制台三类断言 ✅（2026-08-31：`src/workbench/` 服务层 20 单测 + 全量 **395 通过 + 1 跳过**；FastAPI router 留 G4b 薄包装） |
| **G4b 前端壳 + 图谱页** | 承接 D9 W1–W2；顶置作品索引 + 各数据图谱组件（力导/雷达/时间线/节拍条/信息视野） | 浏览器可查看多小说进度与单小说六类图谱（读 G4a） ✅（2026-08-31：`web/api/app.py` FastAPI 工厂 + 五 router 薄包装 `src/workbench/` + `web/static/index.html` 无构建静态仪表盘；10 条 TestClient 单测，全量 **405 通过 + 1 跳过**；React/Vite 前端仍留 W 系列替换静态页） |
| **G4c 作者控制台** | 定制调整（能力/镜头/备选稿）写口 + Session 作者在环（W3–W4） | 浏览器内改能力/切镜头/升备选稿生效；作者自由输入回合审阅；**互斥：`author_workbench.enabled=true` 时终端不弹作者菜单、不读 stdin，交互只在前端**（G3/大纲推进/审阅 prompt 全走前端） ✅（2026-08-31：`WebInputAdapter`/`LogOnlyAuthorIngress` + `WorkbenchSession`/`SessionRegistry` + `session.py` router（409 互斥 + pending/reply/abort/delete）；11 条单测，全量 **416 通过 + 1 跳过**） |
| **GG5 `/system` 系统设置** | D9 §5.6 LLM/工作台互斥/联网面板 | 浏览器内读 effective 设置、改 `author_workbench.enabled` + `internet_search.*` + **LLM 工作参数白名单五子键（v2）** 落 per-novel `config/runtime.yaml`；get_post_set_state；provider 类型/密钥值仍只读不破启动链；全量回归保持绿 ✅（2026-08-31 §6.4；**2026-09-06 §6.8：LLM model/base_url/timeout/max_retries/api_key_env 可写，落 top-level `framework`**） |
| **GG6 远程访问与鉴权** | 可配监听（`config/web_api.yaml` server.host/port）+ 密码登录（Basic Auth，可开关） | `python -m web.api.server` 按配置监听；`auth.enabled=true` 全站 Basic Auth（默认关不破本地/单测）；空口令启动报错不裸奔；口令恒等比较；全量回归保持绿 ✅（2026-08-31：详见 §6.5） |
| **GG-W 工作台面板补全** | #2 五维成长雷达（`growth_radar` 确定性打分 + 前端 SVG 雷达）→ #3 迁移日志时间线 → #4 L1记忆·屏外线时间线 → #5 跨卡联动 → #6 两栏布局 + 控制台终端输出 / 小说正文 | 数据源复用 §4 确定性模块、纯前端渲染；default 不破；全量回归保持绿。**#2 ✅（2026-08-31：`character_detail` 增 `growth_radar`，`_GROWTH_DEPTH_SCALE=6` 截断，前端人物卡内嵌雷达）· #3 ✅（2026-08-31：人物卡增 `transition_log` turn 时间线）· #4 ✅（2026-08-31：人物卡增 L1 记忆 + 屏外线两节时间线）· #5 ✅（2026-08-31：`focusPerson` 跨卡联动——点人物卡/关系节点 → 人物卡高亮聚焦 + 心图跳该角色；详见 §6.6）· #6 ✅（2026-09-01：左导航维度 + 右内容两栏；控制台并入终端输出 tail（会话期根 logger 缓冲）+ 小说正文事件体 read port；详见 §6.7）** |
| **简介种子 + 设定讨论/设定情况面板** | meta.yaml `synopsis` 字段 + 新小说进作者在环引导填简介作设定讨论种子；`discussion_snapshot` 确定性读口 + 控制台面板展示阶段/简介/world/设定方向/最近归档讨论，终端降级为出错详查 | 新小说先填简介→落盘 meta→`run_design_phase` 首轮 reference 含简介；`GET /api/novels/{slug}/discussion` 返回快照；`PATCH .../synopsis` 落盘；无 LLM；全量回归保持绿 ✅（2026-09-06：详见 §6.9） |

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
- **2026-09-01**：增 **§6.7 #6**——两栏布局（左导航维度 + 右内容、懒加载）+ 控制台右侧并入**终端输出 tail**（`session_runner` 会话期根 logger 缓冲，内存态、只读）与**小说正文 read port**（`story_events` 复用 scope 事件 body）；§7 增 #6 行。
- **2026-09-06**：§6.4 LLM 行升 **v2 工作参数白名单可写**（`model`/`base_url`/`timeout`/`max_retries`/`api_key_env`，写 top-level `framework.llm_options`；provider 类型与密钥值仍只读）；增 **§6.8 在线书名编辑**（`rename_novel` 落 meta/index/current_novel，slug 变化时目录改名）；§7 GG5 行补可写项。
- **2026-09-06**：增 **§6.9 简介种子 + 设定讨论/设定情况面板**——meta.yaml `synopsis` 字段持久化 + 新小说进作者在环引导填简介作 `run_design_phase` 设定讨论种子；`src/workbench/discussion.py::discussion_snapshot` 确定性读口 + `GET /api/novels/{slug}/discussion` + `PATCH .../synopsis`；控制台面板展示阶段/简介/world/设定方向/最近归档讨论，终端 `<details>` 降级为出错详查。**续**：最近归档讨论独立成区，`archived_discussion_detail` + `GET .../discussion/archive` 支持点击下钻进完整对话（读 `book/setting/sessions/session_<ts>` 的 `.yaml` 轮次 / `.md` 原文）。