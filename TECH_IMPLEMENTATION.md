# 技术实现文档（写代码前参考）

本文档面向**纯技术实现**：框架选型、架构边界、配置与数据模型、初始化与回合制流程、存储与并发模型、代码结构。产品与设计理念见 [DESIGN.md](./DESIGN.md)。**建议在开始写代码前通读本文档并作为实现依据。**

---

## 一、文档定位与阅读顺序

- **DESIGN.md**：产品与多 Agent 协作设计（角色/世界/设定研究、回合制理念）。
- **TECH_IMPLEMENTATION.md**（本文）：技术实现框架与方案，写代码前的参考。
- **docs 文档中心**：[docs/README.md](./docs/README.md)（专题 SDD、迭代清单、操作手册索引）。
- **规约体系与 SDD 流程**（分层 L0–L4、登记表、变更门禁）：[docs/framework/SPEC_SDD.md](./docs/framework/SPEC_SDD.md)。
- 建议顺序：先 DESIGN.md 理解整体，再本文确定技术方案与接口；跨模块或新横切能力前浏览 **SPEC_SDD**，最后按模块实现。

---

## 二、技术栈与基础框架选型

### 2.1 选型总表

| 类别 | 推荐/可选技术 | 用途说明 |
|------|----------------|----------|
| **多 Agent 编排** | **LangGraph**（推荐） | 图编排、多节点并行、状态在回合间传递，与“回合内并行、回合结束同步”匹配。 |
| | AutoGen | 多 Agent 对话与角色配置，可作角色/世界 Agent 抽象。 |
| | CrewAI | 角色化 Agent + Task 顺序/并行执行。 |
| **LLM 与工具** | **LangChain** / **LlamaIndex** | 统一 LLM 调用、Prompt 模板、Tool（如联网搜索）；LlamaIndex 侧重检索与记忆。 |
| **记忆与检索** | 向量库（Chroma / Milvus / pgvector / 内存） | 角色记忆、世界事件按范围分片，按场景/范围检索后注入 LLM 上下文。 |
| **状态与持久化** | JSON/YAML 文件 或 SQLite | 角色状态、世界设定、各范围事件簿分键存储，便于版本与回放。 |
| **设定研究** | 搜索 API / Playwright 等 | 联网检索；小说分析 = 本地/爬取文本 + LLM 抽取，产出设定 YAML/JSON。 |

### 2.2 推荐组合

- **编排与回合**：LangGraph（图 + 状态机）。
- **LLM 与检索**：LangChain 或 LlamaIndex（调用、Prompt、检索）。
- **多 Agent 数量与类型**：由配置文件驱动，动态创建角色 Agent、范围 Agent 等。

### 2.3 依赖示例（Python）

实现时可按选型引入，例如：

```
# 多 Agent / 编排
langgraph
langchain-core
langchain-openai   # 或 langchain-anthropic、本地模型适配

# 检索（可选）
chromadb
# 或 llama-index

# 配置与存储
pyyaml
# 可选：sqlalchemy + sqlite
```

---

## 三、系统架构与组件边界

### 3.1 组件一览

| 组件 | 职责 | 与其它组件接口 |
|------|------|----------------|
| **Orchestrator** | 加载配置、创建并持有各 Agent、驱动回合、收集输出、冲突裁决、写回状态。 | 读配置 → 创建 Agent；每回合：下发 Context → 收 Agent 输出 → 写回存储。 |
| **CharacterAgent** | 按角色设定 + 当前上下文产出内心独白与言行；不直接访问它人状态。 | 输入：TurnContext；输出：CharacterTurnOutput。 |
| **ScopeAgent**（范围 Agent） | 按本范围事件簿与状态产出场景约束与建议；可选接收协调者下发的跨范围摘要。 | 输入：TurnContext + scope_id；输出：ScopeTurnOutput。 |
| **WorldCoordinator**（可选） | 全局时间、跨范围事件登记与摘要下发。 | 输入：本回合涉及范围与事件；输出：给各范围的跨范围摘要。 |
| **SettingResearchAgent** | 设计期/按需：联网与文本分析，产出战力/等级等设定文件。 | 输入：题材、类型、参照；输出：写入 config 或 world 设定目录的 YAML/JSON。 |
| **DevAgent（开发程序 Agent）** | **专为小说主程序自我迭代**：与主程序保持耦合，持续优化并完善小说主程序及自身。保证运行成功与测试通过的前提下，结合对“小说可能涉及的内容”的搜索与联想，驱动主程序功能与自身能力的迭代（见 §3.6）。 | 输入：本仓代码、测试结果、可选搜索/联想产出；输出：补丁或修改建议；触发方式见配置。 |
| **Context / State** | 当前场景、共享信息、回合号、时间；由 Orchestrator 构建并只读下发给 Agent。 | 只读数据结构，由编排器填充。 |
| **Storage** | **每个 Agent 独立记忆库、分开存储**：角色 Agent 各自一套记忆（社交关系、人物设定、事件提炼、情感等），范围 Agent 各自事件簿与状态；按 character_id、scope_id 分键，互不共享。 | 编排器与各 Agent 通过统一 Storage 接口读写，Agent 仅能访问**自身**记忆库，不跨 Agent 直接访问。 |

### 3.2 调用关系（回合内）

- 仅 **Orchestrator** 调用 Agent，Agent 之间**不直接调用**。
- 回合内：Orchestrator 并行调用「当前 ScopeAgent + 在场 CharacterAgent」，传入同一份 TurnContext。
- 回合结束：Orchestrator 写回 Storage（事件簿、记忆、世界状态），下一回合 Agent 只通过 Context 与 Storage 间接获得“同步后”状态。

### 3.3 与代码目录的对应· 

| 文档组件 | 建议代码位置 |
|----------|--------------|
| Orchestrator | `src/orchestrator/` |
| CharacterAgent | `src/agents/character/` |
| ScopeAgent / WorldCoordinator | `src/agents/world/` |
| SettingResearchAgent | `src/agents/setting_research/` |
| **DevAgent** | `src/agents/dev/` |
| Context、TurnContext 数据结构 | `src/context/` |
| Storage、事件簿、记忆读写 | `src/runtime/` |
| 配置加载、配置 Schema | `config/` + 可选 `src/config/` |
| **配套测试程序** | `tests/`（见 §3.4），供 DevAgent 自我迭代与 CI 使用；默认同仓一体时主程序仓含 `src/agents/dev/` 与 `tests/`。 |

### 3.4 开发程序 Agent 与配套测试

- **DevAgent（开发程序 Agent）**：**专为小说主程序的自我迭代**而存在，与主程序**保持耦合**（同仓一体）。负责在保证运行成功与测试通过的前提下，持续完善**小说主程序**与**DevAgent 自身**；可结合对“小说可能涉及的内容”的搜索与联想驱动迭代方向（见 §3.6）。触发方式可为：定时、按需、或主流程跑完 N 回合后触发。
- **配套测试程序**：与 DevAgent 配套，用于在优化前后验证行为正确性。仓库根目录下 **`tests/`** 包含：**单元测试**（各模块接口与核心逻辑）、**集成测试**（配置 → 创建 Agent → 单回合/多回合）、**回归与契约**（TurnContext、Storage 键结构等）。DevAgent 每次修改后必须跑通测试，未通过则回滚或重试，形成“测试 → 优化 → 再测试”闭环。

### 3.5 开发程序 Agent 与小说主程序：保持耦合

**结论**：**采用同仓一体、保持耦合**。DevAgent 专为小说主程序的自我迭代服务，与主程序同属一个仓库，通过单独入口或定时/按需触发运行，不参与写戏回合；仅在确有部署隔离或多项目共用一套“开发 Agent”的需求时，再考虑拆成独立两套体系（见下）。

- **同仓一体（默认）**：小说主程序与 DevAgent 同仓。主程序入口（如 `run_novel`）只加载编排器 + 角色/世界/设定研究 Agent；DevAgent 通过**单独入口**（如 `run_dev_agent`）或 CI/定时任务运行，操作本仓 `src/` 与 `tests/`，**只优化本仓库**，与主程序共享配置与依赖。
- **独立两套（可选）**：仅在需要“部署体不含改代码能力”或“一套 Dev 优化多个小说仓库”时，可将主程序与 DevAgent 拆成两套；接口约定见原 §3.5 方案 B，此处不赘。

### 3.6 开发程序 Agent 的自我迭代机制

DevAgent 的职责是**在保证运行成功与测试通过的前提下，持续完善小说主程序与自身**。自我迭代包含以下方面。

**（1）保证运行成功与测试通过**

- **准入门槛**：每次对主程序或对自身（DevAgent 代码/配置）的修改，**必须先通过**：主程序可正常启动、配置加载与 Agent 创建无报错、**配套测试全部通过**（单元 + 集成 + 关键契约）。未通过则**不保留本次修改**：回滚到上一可用状态，或由 DevAgent 根据失败信息重试（如修正补丁后再次运行测试）。
- **可选**：在主程序侧增加**冒烟/主流程检查**（如“加载配置 → 跑 1 回合 → 无异常退出”），作为测试套件的一部分，确保“能跑起来”与“行为契约”同时满足。
- 这样形成硬约束：**只有运行成功、测试通过的改动才会被保留**，避免自我迭代引入不可用状态。

**（2）持续搜索与联想：小说可能涉及的内容**

- DevAgent 可**定期或按需**对“小说创作与阅读中可能涉及的内容”进行**搜索与联想**（联网检索、分析既有小说与设定、类型惯例等），用于拓展主程序能力与自身策略。可覆盖的维度示例：
  - **类型与套路**：言情、悬疑、修仙、历史等类型的常见情节模式、读者预期、节奏习惯。
  - **设定要素**：世界观、战力/等级、势力关系、时间线、地理与势力分布等如何在不同类型中呈现。
  - **文风与表达**：叙述视角、对话风格、描写密度、伏笔与回收等。
  - **角色与关系**：人设弧光、关系演进、信息不对称、多视角交织等。
- 搜索与联想的结果可用于：**完善主程序**（如为设定研究 Agent 增加类型模板、为角色/世界 Agent 增加约束或提示模板、新增配置项）；**完善 DevAgent 自身**（如增加“主程序应支持的设定维度”的检查、补充测试用例或回归场景、更新对 DESIGN/TECH 文档的解读与落地清单）。  
- 实现上可与**设定研究 Agent** 共享部分能力（如联网、文本分析），但 DevAgent 的侧重点是“**为程序与自身迭代提供输入**”，而非直接产出小说用设定文件；二者可协作（例如设定研究产出设定 YAML，DevAgent 据此检查主程序是否支持相应字段并补充测试）。

**（3）完善小说主程序**

- 在运行成功与测试通过的前提下，根据以下输入持续改进主程序：
  - **测试与运行反馈**：失败用例、覆盖率缺口、性能或可维护性问题。
  - **搜索与联想结论**：小说可能涉及的内容（类型、设定、文风、角色关系等），反推主程序缺失的能力（如某类设定未在配置或 Storage 中支持、某类情节模式未被回合/范围覆盖）。
  - **DESIGN/TECH 文档**：主程序与文档不一致时，以文档为准进行修正或补全实现。
- 改进形式包括：修 bug、补全缺失功能、优化性能与可读性、扩展配置与 Storage 结构、增强角色/世界/设定研究 Agent 的提示或约束，使主程序**更贴合“写小说”所需**。

**（4）完善 DevAgent 自身**

- DevAgent 在迭代过程中也可**改进自身**，使后续迭代更高效、更少引入回归：
  - **策略与规则**：根据“哪些改动容易导致测试失败”“哪些模块变更需优先跑哪些测试”等经验，更新自身的分析策略、修改建议的优先级或回滚策略。
  - **测试与契约**：针对主程序新增能力或新发现的边界情况，**补充或更新 tests/** 中的用例与契约，使回归更全面。
  - **对文档的运用**：根据 DESIGN/TECH 的更新或对文档的更深理解，更新自身对“主程序应满足的契约”的检查清单，或生成更贴合的测试与修改建议。
- 对自身的修改同样遵守**运行成功、测试通过才保留**的规则（例如修改 DevAgent 后需重新跑 full test suite，确认主程序与测试均正常）。

**（5）迭代循环小结**

- 典型单次循环：**(1) 运行主程序与测试，确认当前状态绿色；(2) 可选：执行搜索与联想，更新“小说可能涉及的内容”与改进清单；(3) 选定改进目标（主程序或自身），产出修改；(4) 应用修改后再次运行主程序与测试；(5) 若全部通过则保留，否则回滚并可选重试。**  
- 长期看：主程序在“运行成功 + 测试通过”的约束下持续获得功能与质量改进；DevAgent 在同样约束下持续完善自身策略与测试，二者**共同自我迭代**，且始终以小说主程序的可用性与设计文档为基准。

---

## 四、配置与数据模型

### 4.1 配置文件清单

| 文件 | 用途 |
|------|------|
| `config/example_world.yaml` | 世界元信息、范围列表（scopes）、地点；每 scope 可有 `enabled`。 |
| `config/example_characters.yaml` | 角色列表；每角色可有 `enabled`、id、name、traits、goals 等。 |
| `config/example_runtime.yaml` | **本书运行时入口**：`runtime.novel_run`、启用的 character/scope id（`agents`）。 |
| `config/novel_writing.yaml` | **小说写作基础**（并入 `runtime`）：世界协调者、设定研究、作者在环、`storage`、可选 `author_classified_memory` 等。 |
| `config/system_config.yaml` | **系统向**：`framework`（LLM）、`debug`、`dev_agent` 等；与上项合并加载。**同仓一体（A）** 时 dev_agent 在此；**独立两套（B）** 时主程序库可省略 dev_agent。 |
| `config/example_special_settings.yaml` | 战力/等级等特殊设定（可由设定研究 Agent 产出）。 |

### 4.2 运行时配置 Schema（核心）

以下为建议的运行时配置结构，实现时可按需增删字段：

```yaml
runtime:
  world_coordinator_enabled: true
  turn_based: true
  author_in_the_loop: true   # 作者在环：回合结果审阅/同意 → 同步 → 确认后再写回记忆；false 则自动执行

setting_research:
  enabled: true
  trigger: design_only   # design_only | on_demand | off

agents:
  characters:
    enabled_ids: [a, b]   # 与 characters 配置中的 id 对应
  scopes:
    enabled_ids: [capital, jianghu]

framework:
  orchestrator: langgraph
  llm: langchain

# 开发程序 Agent：持续/按需优化代码，依赖配套测试做回归
dev_agent:
  enabled: true
  trigger: on_demand    # continuous | on_demand | off
  test_command: "pytest tests/ -v"   # 配套测试执行命令，DevAgent 据此运行并解析结果
  scope: ["src/", "tests/"]          # 可读取与修改的目录范围（可选）
```

### 4.3 配置与 Agent 实例的映射

- **角色 Agent**：只为 `enabled_ids` 中的 `character_id` 创建实例；每个实例绑定一份角色设定与私有记忆存储键（如 `memory:{character_id}`）。
- **范围 Agent**：只为 `enabled_ids` 中的 `scope_id` 创建实例；每个实例绑定该范围事件簿与状态存储键（如 `events:{scope_id}`、`state:{scope_id}`）。
- **世界协调者**：单例，仅当 `world_coordinator_enabled: true` 时创建。
- **设定研究 Agent**：单例，按需或设计期调用，不参与每回合并行。
- **DevAgent**：单例，仅当 `dev_agent.enabled: true` 时创建；按 `trigger`（continuous / on_demand / off）在后台或按需执行，不参与写戏回合。依赖 `test_command` 运行配套测试并解析输出。

---

## 五、初始化流程

1. **加载配置**  
   读取 `config/` 下世界、角色、运行时、特殊设定等 YAML；校验必填字段与 `enabled_ids` 在对应列表中存在。

2. **创建 Storage 与 Context 工厂**  
   初始化存储后端（文件或 SQLite）；准备 TurnContext 的构建逻辑（依赖当前场景、时间、范围、在场角色等）。

3. **按配置创建 Agent 实例**  
   - 为 `agents.characters.enabled_ids` 中每个 id 创建一个 CharacterAgent。  
   - 为 `agents.scopes.enabled_ids` 中每个 id 创建一个 ScopeAgent。  
   - 若 `world_coordinator_enabled`，创建一个 WorldCoordinator。  
   - 若需要，创建 SettingResearchAgent（单例）。

4. **并行初始化（同时启动）**  
   各 Agent 的 `start()` / `load_state()` 可并行执行（如 `asyncio.gather` 或线程池）：每个角色 Agent 加载自身记忆索引，每个范围 Agent 加载本范围事件簿与状态。不依赖启动顺序。

5. **就绪**  
   Orchestrator 持有所有 Agent 引用，进入“等待第一回合”状态。

---

## 六、回合制运行模型

### 6.0 作者在环：Spec 与 SDD 索引

- **L1 行为规约（Spec）**：[docs/specs/author-in-loop-spec.md](./docs/specs/author-in-loop-spec.md) — MUST/SHOULD/不承诺项（检索义务、统一入口目标态、百万字全自动边界等）。  
- **L2 软件设计（SDD）**：[docs/design/author-agent-harness.md](./docs/design/author-agent-harness.md)（Harness 组件与迁移切片）、[docs/design/author-interaction.md](./docs/design/author-interaction.md)（状态机、M1–M6、`last_round_digest`）、[docs/design/context-compression-adaptive-layered.md](./docs/design/context-compression-adaptive-layered.md)（**D8** 组装后上下文压缩；实现分阶段见该文 §8）。  
- **实现包（迁移中）**：`src/author_harness/`（R1+：`prompt_assembler`、`retrieval_registry`、**R6** `author_harness.py` 主菜单 ingress；与 `author_loop.retrieve_for_intent` 并存）。**导入注意**：`src.author_loop` 包对 **`run_design_phase`** 采用 **`__getattr__` 懒加载**，避免与 `author_harness` 形成环状 import。细节见 **author-agent-harness.md** §6.1。  
- **正篇审阅 Harness（R7，R7a–R7e ✅；R8 ✅）**：规约 **author-in-loop-spec §3.4**；设计与分步 **author-agent-harness.md §6.3**。**R7b–R7d**：**`apply_main_writing_review_ingress`**（`review_turn_result` 内懒加载）、`revise_body_by_feedback(assembled_context=...)`、主流程 **storage**。**R7e**：阶段二 **`MEMORY_PLAN_REVIEW`** 可观测日志。**R8**：阶段一 Harness 行日志 + 单测检索链断言。**勿**在 R7 中合并 TECH 本节所述**两阶段审阅**。  
- **L0 产品摘要**：[DESIGN.md](./DESIGN.md) §6.7。

作者在环的 **统一交互架构（目标态）**见 **author-agent-harness.md**（每轮分类→检索/工具→阶段策略→Handler）与 **author-interaction.md**；与 §6.2 两阶段审阅互补，长期将主循环迁入该架构。

**开书前设定阶段**（`runtime.setting_research.enabled` 且 `trigger=design_only`）：主程序在调用 `run_design_phase` 之前须解析有效作品根目录（`ensure_current_novel_for_design_phase`，失败则交互 `interactive_resolve_novel_for_design_phase`）。设定研究产出落在 `<novel_root>/config/setting_research_output.yaml`。当 `world.yaml` 尚未填写世界名而已有设定研究文件时，**审阅日志中的世界/范围/角色摘要**可展示题材、类型与 `reference` 预览，**不替代** `world.name` 非空方可结束设定阶段的规约；细节见 **author-interaction.md §11.1**。

### 6.1 回合内（独立演进、并行）

- **输入**：Orchestrator 构建本回合 **TurnContext**（当前 scope_id、时间、地点、在场 character_ids、上一回合摘要、共享情节摘要等），保证所有本回合被调用的 Agent 收到**同一份只读上下文**。
- **执行**：对「当前 ScopeAgent + 在场 CharacterAgent」做**并行调用**（如 `asyncio.gather` 或线程池），每个 Agent 仅根据 TurnContext 与自身从 Storage 读取的私有状态（记忆/事件）计算输出，**回合内不接收其它 Agent 的中间结果**。
- **输出**：每个 Agent 返回结构化结果（如 CharacterTurnOutput：内心独白 + 言行文本；ScopeTurnOutput：约束列表 + 本回合事件摘要）。

### 6.2 回合结束（作者在环 + 同步 + 写回记忆）

- **收集**：Orchestrator 汇总本回合所有 Agent 的输出（各角色言行、范围事件摘要等）。
- **冲突裁决**：对角色言行做规则或简单模型驱动的冲突检测，必要时标记重写或选主版本。
- **作者交互（第一次）**：将本回合各 Agent 的运行结果提交给**作者**审阅；作者可**直接确认**、**编辑文件**或**用自然语言提出修改意见**（系统理解作者意图后对“本回合正文”进行修订并再次展示），直到作者表示满意并确认。实现上需提供作者审阅/编辑界面或 API，以及“同意/驳回/补充设定”操作。
- **同步写回（事件簿与世界状态）**：作者同意后执行——  
  - 当前 scope 的事件簿追加本回合事件条目，条目建议同时含 `summary` 与 `body`（正文），保证**摘要与正文一一对应**，后续检索摘要时可直接回看正文。  
  - 更新该 scope 的状态（若有）；若有跨范围影响，由 WorldCoordinator 登记并写入目标 scope 的摘要。  
  - **此时尚未写回各 Agent 的私有记忆**。
- **作者确认（第二次）**：同步结束后，将“即将写回各 Agent 记忆的内容”呈现给作者（可选：摘要或逐条）；**作者确认后**，系统才执行写回各 Agent 的私有记忆、关系、目标或性格演进。
- **写回记忆**：作者确认后，根据本回合事件与作者可能修改过的结果，写入各角色新记忆条目、更新关系网与目标/性格（若有演进规则）。
- **波及下一回合**：下一回合开始时，所有 Agent 通过 TurnContext 与 Storage 读到的已是**上述写回后的新状态**。

### 6.3 下一回合

- Orchestrator 在**同步后状态**上决定下一场景（可切换 scope、时间、在场角色），再次构建 TurnContext，再次并行调用对应 ScopeAgent 与 CharacterAgent，循环。

### 6.4 数据流简图

```
[ 配置 ] → [ 初始化：创建 Agent、并行 load_state、就绪 ]
                ↓
[ 回合 N 开始 ] → 构建 TurnContext（当前范围、时间、在场角色、共享摘要）
                ↓
[ 并行 ] ScopeAgent(TurnContext) ──┐
          CharacterAgent_a(...) ───┼→ 收集 TurnOutputs → 冲突裁决
          CharacterAgent_b(...) ──┘
                ↓
[ 作者交互① ] 审阅/修改各 Agent 结果 → 作者同意
                ↓
[ 同步 ] 写回 events / state（事件簿、范围状态、跨范围摘要）；不写记忆
                ↓
[ 作者确认② ] 确认后再写回各 Agent 的 memory / 关系 / 目标
                ↓
[ 回合 N 结束 ] 写回记忆与演进 → 波及下一回合
                ↓
[ 回合 N+1 ] 在更新后状态上重复
```

### 6.5 接口约定（建议）

- **TurnContext**（只读）：`scope_id`, `time`, `place`, `present_character_ids`, `last_turn_summary`, `shared_story_snippet`, `world_constraints`（由 ScopeAgent 上回合或本回合预跑填充，可选）。
- **CharacterTurnOutput**：`inner_monologue?: string`, `dialogue_action: string`, `metadata?: object`。
- **ScopeTurnOutput**：`constraints: string[]`, `event_summary: string`, `state_delta?: object`（说明：`event_summary` 在最新实现中可承载“本回合正文（多行）或事件摘要”）。
- **Storage 读写**：**每个 Agent 独立记忆库、分开存储**。角色 Agent 按 `character_id` 与子类读写：如 `get_relations(character_id)`、`append_relation(character_id, ...)`、`get_events(character_id, timeline?, limit)`、`append_event_refinement(character_id, ...)`、`get_emotions(character_id, target_id?)`、`append_emotion(character_id, ...)`、`get_profile(character_id)`、`update_profile(character_id, delta)`（profile 须符合总设定）。范围侧：`append_events(scope_id, events)`、`get_recent_events(scope_id, k)`、`get_state(scope_id)` 等。**范围 events 的单条事件建议含 `summary`（摘要）与可选 `body`（正文）**，正文展示与持久化以该事件为单一数据源，避免多处存储不一致。Agent 仅能访问自身 `character_id`/`scope_id` 对应键空间。
- **作者交互**：需支持两处阻断点——(1) 回合结果审阅/编辑与“同意”后进入同步；(2) 同步完成后“即将写回记忆”的确认，确认后再执行 `append_memory` 等。可由 CLI 确认、Web 审阅页或 API（如 `POST /turn/review`、`POST /turn/confirm-memory`）实现。

---

## 七、存储与持久化布局

**记忆分类、目录存储与检索的详细方案**（小说主体按回合存储、记忆用 Markdown、渐进式目录、免向量库检索）见单独文档：  
→ **[docs/design/memory-storage-and-retrieval.md](docs/design/memory-storage-and-retrieval.md)**（记忆分类、存储、检索方案）

### 7.1 原则：每个 Agent 独立记忆库、分开存储

- **角色 Agent** 与 **范围 Agent**（及世界协调者）各自拥有**独立存储**，互不共享；同一角色在不同回合只读写自己的记忆库，不访问其它角色或范围的内部存储。
- 编排器/同步逻辑在写回时按 `character_id`、`scope_id` 写入对应键，检索时每个 Agent 只查询**自身**键空间。

### 7.2 建议键结构（示例）

**角色 Agent 记忆库**（按角色分库，每个角色一套键，子类分开存储）：

- `memory:{character_id}:profile` — **人物设定**（姓名、背景、性格、口头禅等）；须与**总设定要求**一致（世界设定、类型、战力/等级等），初始化或设定研究产出后写入，演进时可微调。
- `memory:{character_id}:relations` — **社交关系**（与其它角色的关系、信任/敌对、亲疏、变化历史）；可结构化（如 `{ target_id, type, intensity, updated_at }`）或文本摘要。
- `memory:{character_id}:events` — **不同时间线上发生的事件提炼**（该角色所知事件的摘要，可按 timeline/scope_id 或时间戳组织）；列表或向量库，按时间/范围/重要性检索。
- `memory:{character_id}:emotions` — **情感变化**（对某人某事的情绪、重大事件带来的情感转折）；可按对象、时间或类型存储，供“当前对谁是什么情绪”类检索。

可选：`memory:{character_id}:secrets`、`memory:{character_id}:goals` 等，与上面并列或归入 profile。  
实现时可为每个子库单独建向量索引或时间索引，检索时按需查 relations / events / emotions 等。

**范围 Agent / 世界层**（与角色记忆库分离）：

- **范围事件簿**：`events:{scope_id}`；追加写入，支持按时间范围或条数查询最近 N 条。
- **范围状态**：`state:{scope_id}`；当前范围的世界状态快照（如势力、地点状态），可 JSON 序列化。
- **全局世界设定**：`world:global` 或直接读 `config/` 下 YAML；特殊设定（战力/等级）单独文件或 `world:special_settings`。人物设定须**依据**此类总设定。
- **跨范围摘要**：可由协调者写入 `cross_scope:{scope_id}:inbox` 或等价结构，供目标 scope 的 Agent 读取。
- **次要角色列表**：配置中仅列**关键角色**（拥有 CharacterAgent）；小说中其余角色可动态追加（如 `secondary_characters` 列表，每项含 name、brief、scope_id 等），供编排器格式化为 `TurnContext.secondary_characters_snippet`，ScopeAgent/CharacterAgent 可查阅。

### 7.3 版本与回放

- 事件簿与关键状态变更建议带 `turn_id` 或 `timestamp`，便于按回合回放与调试。
- 角色记忆库各子类（relations、events、emotions）写回时建议带 `turn_id`/`timestamp`，便于追溯与回放。
- 可选：每回合写一份快照（如 `snapshots:turn_{n}`）用于回放与回溯。

---

## 八、并发与执行模型

- **初始化**：各 Agent 的加载可并行（异步或线程池），避免顺序依赖。
- **回合内**：对 ScopeAgent 与在场 CharacterAgent 的调用**并行**（推荐 asyncio + 单进程，便于共享 Storage；若需多进程则需共享存储或消息队列）。
- **回合结束**：写回为**顺序或加锁**，保证同一 scope / 同一 character 的写不并发冲突；跨 scope 的协调者写回可与各 scope 写回并行，但需与 Orchestrator 的“收集→裁决→写回”顺序一致。
- **设定研究 Agent**：与回合解耦，设计期或按需同步/异步调用均可。
- **DevAgent**：与写戏回合完全解耦，可在后台定时或按需运行；按 §3.6 自我迭代机制执行：保证运行成功与测试通过才保留修改，结合搜索与联想完善主程序与自身，形成“测试 → 优化 → 再测试”及“搜索联想 → 完善主程序/自身”的闭环。

---

## 九、代码模块与目录结构

```
min-autobook/
├── DESIGN.md
├── TECH_IMPLEMENTATION.md   # 本文档
├── README.md
├── config/
│   ├── system_config.yaml       # LLM、debug、dev_agent（与小说配置分离）
│   ├── novel_writing.yaml       # 写作流程、设定研究、storage 等（并入 runtime）
│   ├── example_world.yaml
│   ├── example_characters.yaml
│   ├── example_runtime.yaml     # novel_run + agents
│   └── example_special_settings.yaml
├── src/
│   ├── orchestrator/        # 编排器：配置加载、Agent 创建、回合驱动、裁决、写回
│   ├── agents/
│   │   ├── character/      # 角色 Agent 实现
│   │   ├── world/          # 范围 Agent + 世界协调者
│   │   ├── setting_research/# 设定研究 Agent
│   │   └── dev/            # 开发程序 Agent：专为主程序自我迭代，保证运行与测试通过，搜索联想完善主程序与自身（§3.6）
│   ├── context/            # TurnContext 及共享上下文数据结构
│   └── runtime/            # Storage、事件簿、记忆的读写与持久化
├── tests/                   # 配套测试程序（单元 + 集成 + 回归），供 DevAgent 与 CI 使用
│   ├── unit/               # 单元测试（配置、Storage、Context、单 Agent 壳等）
│   ├── integration/        # 集成测试（编排器 + 多回合流程）
│   └── conftest.py         # 可选：pytest fixtures、共享 mock
└── requirements.txt        # 或 pyproject.toml
```

- **入口**：建议在 `src/` 根或 `orchestrator/` 下提供 `run.py` 或 `main.py`，完成“加载配置 → 初始化 → 回合循环（或单回合测试）”。
- **配置解析**：可集中在 `orchestrator` 或单独 `src/config/`，输出结构化对象供创建 Agent 与构建 Context 使用。
- **测试**：`tests/` 下测试可由 `pytest tests/ -v` 或配置中的 `dev_agent.test_command` 执行；DevAgent 读取测试输出以判断优化是否引入回归。

---

## 十、实现顺序建议（写代码前参考）

1. **配置与存储**：实现配置加载（YAML）与 Storage 抽象（内存或文件版），键结构符合 §7。  
2. **Context**：定义 TurnContext 及构建方式（可由编排器根据“当前场景”生成）。  
3. **单 Agent 形态**：先实现一个 CharacterAgent、一个 ScopeAgent 的“壳”（固定返回或简单规则），不接 LLM。  
4. **Orchestrator**：按配置创建 Agent、单回合流程（下发 Context → 并行调用 → 收集），写回拆为“先写事件簿/状态、再写记忆”两段，中间留作者确认点。  
5. **回合循环**：多回合、状态在回合间通过 Storage 持久化并影响下一回合。  
6. **冲突裁决**：简单规则或启发式。  
7. **作者在环**：实现两阶段作者交互——(1) 回合结果审阅/编辑与“同意”后进入同步；(2) 同步完成后“确认”再写回各 Agent 记忆（CLI 确认或 Web/API）。  
8. **配套测试程序**：在 `tests/` 下建立单元测试（配置、Storage、Context、单 Agent 壳）、集成测试（编排器 + 单回合/多回合），以及关键接口的契约或快照测试；保证主流程与 Storage/Context 契约可回归。  
9. **开发程序 Agent（DevAgent）**：实现 DevAgent 及自我迭代机制（§3.6）：(1) 执行 `test_command`、解析测试结果，**仅当运行成功与测试通过才保留修改**，否则回滚或重试；(2) 可选：对“小说可能涉及的内容”做搜索与联想，驱动主程序与自身改进；(3) 完善主程序（修 bug、补功能、对齐 DESIGN/TECH）；(4) 完善自身（策略、测试用例、对文档的运用）；可配置 `trigger`（on_demand / continuous / off）。  
10. **接入 LLM 与检索**：为各 Agent 接入 LangChain/LlamaIndex、记忆/事件检索。  
11. **设定研究 Agent**：联网与文本分析、产出设定文件，与 world 设定目录集成。

---

本文档与 `config/example_*.yaml` 及 [DESIGN.md](./DESIGN.md) 保持一致，作为**开始写代码前的技术参考**。实现时若调整框架或接口，建议同步更新本文档。
