# 关键角色成长状态机设计方案

本文定义关键角色在多回合小说生成中的“可验证成长”机制：状态机、记忆分层、写回校验、与现有主流程接入点。目标是让角色成长具备因果性、边界约束与可审计性，而不是仅依赖 prompt 文本描述。

---

## 1. 目标与范围

### 1.1 目标

- 让关键角色成长具备**状态、迁移规则、代价和冷却**，避免“突然变强/性格突变”。
- 把角色记忆从“单一摘要”升级为“事实层 + 解释层 + 策略层”。
- 在现有作者在环流程中，以最小侵入方式接入。
- 提供可测试、可回放、可审计的数据结构。

### 1.2 关联：大纲与多线叙事

全书 / 章 / 节拍结构见 [outline-and-beats.md](./outline-and-beats.md)。节拍与章仅作**主线指导**；角色成长仍以本文所述**事件驱动语义迁移**为主，节拍 `tags` 可作为可选提示，不做硬编码数值跳变。

### 1.2a 定位：多视角内部模拟 + 单一主角导出（硬边界）

本文采用两层模型，**内部模拟是多视角、导出是单主角镜头**——二者不冲突，且都成立：

- **内部模拟层（世界，多视角）**：每个关键角色（含主角）都作为一条**完整平行的独立视角**，拥有自己的经历、记忆、知情视野（§4.6）、成长状态（§2）。系统模拟的是一个类似真实世界的多视角世界——每个角色的经历与记忆独立落盘、互不合并、无"主角特权"。这正是角色**独立演进**的机制本体。

- **导出层（主书，单一主角镜头）**：在成稿导出的叙事层面，由**用户从关键角色中选择其一**作为本小说的叙事主角（`protagonist_id` / `characters[].is_protagonist`）。主书正文以该主角为镜头主轴导出，主角姓名/身份唯一（复用 `src/runtime/protagonist.py` 的 `resolve_protagonist_id` / `format_main_characters_snippet` 的姓名不虚构约束）。**这只是渲染/导出视角，不限制内部模拟中哪些角色演进，也不赋予主角额外知情权**。

- **主角在内部也是多视角之一**：主角不过是被用户选定为主书导出镜头的那一个关键角色。内部模拟中主角与其他关键角色地位对等，同样仅见其份内信息、独立演进。

分层对应：**多视角（内部模拟、各关键角色视角/记忆/成长）⊕ 单主角镜头（导出、主书叙述跟随用户选定主角）**。这与 [outline-and-beats.md](./outline-and-beats.md) 既有原则完全一致——**正文以主角为主线，每角色在系统内为并行主线**。本文聚焦后者的"在系统内独立演进"如何落地为可验证状态，并提供导出层把其中任一视角收敛为主书主角。

### 1.3 非目标

- 不在本阶段实现完整战斗数值系统。
- 不引入外部数据库；继续使用 YAML/MD 文件与现有存储机制。
- 不实现复杂可视化 UI，仅提供日志与文件可读性。

---

## 2. 角色成长状态模型

每个关键角色（**含主角**，§1.2a）各维护一份 `CharacterGrowthState`，多视角对等、互不合并、无"主角特权"。该状态是该角色独立演进的事实基座，分为五个子状态：

1. `power_state`
   - 境界、子阶段、技能熟练度、突破压力
2. `mind_state`
   - 稳定度、恐惧、执念、创伤标签、信念偏置
3. `social_state`
   - 对关键角色的信任/依赖/敌意、关系阶段
4. `goal_state`
   - 长期目标、阶段目标、里程碑、受阻项
5. `resource_state`
   - 关键资源（体力/法器/线索/名望/资金等）

### 2.1 状态文件建议

路径（小说级），**沿用既有 `book/characters/<id>/` 落盘布局**（`src/runtime/file_sync.sync_character_turn` 已在该目录写每回合事件）：

- `data/novels/<slug>/book/characters/<character_id>/growth_state.yaml`

字段建议：

- `version`
- `updated_at`
- `power_state`
- `mind_state`
- `social_state`
- `goal_state`
- `resource_state`
- `transition_log`（最近 N 条）

落地注（与现有存储对账）：

- **`mind_state`（主观心理层）** 可落盘到 `MemoryStorage` 已有的每角色 `emotions[]` 槽位（`src/runtime/storage.py`），该槽位当前**已定义但无人写入**，作为主观心理的进程内承载；`growth_state.yaml` 作为可审计归档。
- `social_state`（主观关系感受）与各角色**客观关系图谱**（§4.5）互补：以 `graph.yaml` 的语义边为客观依据，以 `social_state` 为角色个体解读，两者不强制完全一致。

---

## 3. 状态机迁移机制

### 3.1 迁移形式

`当前状态 + 事件类型 + 触发条件 -> 叙事变化 + 代价/后果 + 冷却`

示例（概念）：

- `near_death_escape`（死里逃生）
  - **能力线**：出现“突破契机”或“技能理解加深”的迹象（不强制立即升级）
  - **心理线**：短期更敏感/更警惕，可能出现应激反应
  - **资源线**：明显消耗（伤势、器物损耗、人情债）

- `trusted_betrayal`（信任背叛）
  - **关系线**：对目标角色关系从“信任”转为“怀疑/对抗”
  - **心理线**：执念或防御倾向上升
  - **目标线**：触发阶段目标重评估（是否转向复仇、避险、求证）

> 注：这里优先使用“叙事语义状态”而非硬数值。数值仅作为可选辅助，不应主导角色表现。

### 3.2 迁移规则组织

建议新增规则文件：

- `data/novels/<slug>/config/growth_rules.yaml`

规则字段建议（语义优先）：

- `event_type`
- `preconditions`
- `effects`（对能力/心理/关系/目标/资源的语义影响）
- `costs_or_consequences`（代价与后果）
- `cooldown_turns`
- `priority`

### 3.3 “轻量量化”作为可选层（非必需）

为兼容不同题材，定义三种模式：

- `narrative_only`：纯语义状态（默认，适合大多数非游戏小说）
- `hybrid`：语义状态 + 少量等级/强度标签（如 low/medium/high）
- `numeric`：显式数值（仅推荐游戏/系统流/面板流小说）

推荐默认使用 `narrative_only`，由小说配置按题材切换。

---

## 4. 记忆分层设计

本文的记忆分层是**成长专用**定义，独立于 [memory-storage-and-retrieval.md](./memory-storage-and-retrieval.md)（该文档暂无 L1/L2/L3 分层，已核实）。后续可合并统一，但本篇先行定义角色成长视角的分层。

### 4.1 三层记忆

1. **事实层（L1）**
   - 不可篡改：发生了什么（事件、地点、参与者、结果）
2. **解释层（L2）**
   - 角色理解与立场，可随认知更新
3. **策略层（L3）**
   - 短期计划、预案、下一步动作（可过期）

### 4.2 统一标签

每条记忆建议带：

- `scope_id`
- `turn_index`
- `impact_level`（low/med/high）
- `ttl`
- `affects_state_fields`

### 4.3 落地实现（三层记忆落库 + 写入校验 + 检索消费；确定性、无 LLM）

§9 阶段 2 承诺「接入记忆分层标签的写入校验（事实不动/解释可更新/策略可过期）」。本方案落地为**确定性关键词分类 + 分层槽位 + 可开关检索**：

- **存储槽位**（`src/runtime/storage.py::MemoryStorage`）：
  - **L1**：`_char_events`（`append_event_refinement`，append-only，不可篡改）——事实层。
  - **L2**：`_char_interpretations`（`upsert_interpretation`，按 `subject` **原地替换**）——解释可更新。
  - **L3**：`_char_strategies`（`append_strategy`，带 `expires_turn`；`get_active_strategies` 按当前回合过滤过期项）——策略可过期。
- **确定性分类**（`src/runtime/memory_layers.py`，无 LLM）：
  - `classify_memory_layer(summary)`：命中 L3 关键词（计划/打算/准备/下一步/决意/部署/安排/暂定/提防/预备…）→ **L3**；命中 L2 关键词（觉得/认为/怀疑/判断/理解/明白/意识到/警惕/信任/敌意/好感…）→ **L2**；否则 → **L1**。
  - `interpretation_subject(summary)`：取简短主体作 L2 的 upsert 键（去「我觉得/认为/意识到」前缀，截前 12 字，空给 `general`）。
  - `strategy_expires_turn(turn_index, ttl=5)`：L3 过期回合 = `turn_index + ttl`。
  - `build_layer_entry(summary, layer, *, scope_id, turn_index, time, place)`：构造带 §4.2 统一标签的条目。
- **落库写回**（`src/orchestrator/orchestrator.py::apply_memory_write`）：每角色先落 L1；当 `agents.characters.memory_layers` **开启**时，再按 `classify_memory_layer` 分类，L2→`upsert_interpretation`、L3→`append_strategy`（带 `expires_turn`）。**默认关** → 只写 L1，行为与先前一致（船身不破）。
- **检索消费**（`src/retrieval/memory.py::retrieve_character_memory(include_layers=False)`）：开启时追加 `[解释（L2）]` 与 `[短期计划（L3）]` 两段（角色**自身** L2/L3，无跨角色泄露，与 §4.6 信息视野一致）。`CharacterAgent.turn()` 传 `include_layers=bool(memory_layers)`。
- **写入校验语义即槽位语义**：事实 append-only 不动（L1）、解释 upsert 可更新（L2）、策略 ttl 可过期（L3）。

---

## 4.5 关系知识图谱（Relationship Knowledge Graph）

承载“角色之间关系结构”与客观演化轨迹。**基础图谱已在代码中实现**（`src/runtime/relationship_graph.py` + `src/retrieval/relationship.py`），本方案是对其**扩展为语义关系**，而非从零新增。

### 4.5.1 定位

- **状态机**：描述“角色内部成长”与主观状态变化（本文 §2/§3）；
- **关系图谱**：描述“角色之间关系结构”与客观演化轨迹（本节）；
- 两者互补，避免仅靠回合摘要导致关系线丢失或跳变。

### 4.5.2 现状（已实现）与扩展目标

现状（`src/runtime/relationship_graph.py`）：

- 节点/边/YAML 持久化（`book/relationships/graph.yaml`）已实现；
- 边仅有 `co_presence`（同场共现）一种，由 `sync_relationship_graph_after_scope_turn` 在每回合写回后落地；`get_relation` / `get_neighbors` / `get_relation_change_log` 与 `format_relation_snippet`（`src/retrieval/relationship.py`）已实现。
- 边数据结构中 `status`、`intensity`、`change_log` 字段**已定义**，但当前**无人写入语义值**（仅 `co_presence` + evidence 供共现使用）。

扩展目标（本次落地的增量）：

- 补充 **语义关系抽取**：每回合由 LLM（或规则）判定在场角色对之间的 `relation_type`（trust/rival/ally/debt/mentor/love/hate…）、`intensity`（low/med/high）、`status`（active/fragile/broken）、以及**方向**（单向感受，可刻画"单相思/单方警惕"）。
- 复用既有字段 `evidence_events` / `change_log` 记录每一次语义变化的事件证据；仅 `co_presence` 时维持现状，不强制每位角色对都有语义边。

### 4.5.3 数据结构（与现有代码一致）

- **节点（node）**：关键角色（后续可扩展势力/地点/物件）
- **边（edge）**：
  - `source_id` / `target_id`
  - `type`（`co_presence` 或 `relation_type` 语义值）
  - `intensity`（语义档位：low/med/high）
  - `status`（active/fragile/broken）
  - `evidence_events`（支撑该关系变化的事件 id 列表）
  - `change_log`（关系演化轨迹）
  - `last_updated_turn`

### 4.5.4 查询能力（已实现，直接复用）

- `get_relation(a, b)`：查当前关系
- `get_neighbors(a, types=None)`：查角色一跳关系网
- `get_relation_change_log(a, b, last_k)`：查关系演化轨迹
- `format_relation_snippet(graph, character_id)`：注入 prompt 用的关系摘要

### 4.5.5 与主流程接入点

- 在 `apply_event_and_state_write` 后，基于本回合事件**更新语义关系边**（在既有 `sync_relationship_graph_after_scope_turn` 的共现基础上叠加语义判定）；
- 在角色生成前注入“关系图谱摘要”（近邻 + 最近变化）；
- 与 `social_state` 联动：图谱作为客观关系，`social_state` 作为角色主观感受，不强制完全一致。

### 4.5.6 约束原则

- 默认语义档位，不做重数值化（非游戏题材保持叙事温度）；
- 关系反转必须有事件证据（`evidence_events`）；
- 单回合关系跃迁受 `GrowthGuard` 约束（避免无铺垫突变）。

---

## 4.6 信息视野 / 感知不对称（关键角色独立演进的前提）

**问题**：当前所有角色（含关键角色）在构建 `TurnContext` 时共享同一份 `shared_story_snippet`（scope 事件公开流，`src/context.build_turn_context_from_storage`），是"上帝视角"——每个角色对同一事件得到完全相同的事实，无法产生**差异化解读、隐瞒、猜测、情报差**，也就谈不上真正的"独立演进"（各角色只是换了个名字的同一个 narrator）。

**定义**：为每个关键角色提供**按知情的过滤视图**，而非全量公开流：

- 角色只应看到其**亲身经历 / 知情**的事件（在场、或该角色被明确告知/目击的部分）；
- 对角色**未知**的剧情，prompt 中给出占位（"你对本回合前这段尚未发生的事情一无所知"）而非剧透；
- 意图、秘密、私人计划（L3 策略层）一律不跨角色注入，除非角色亲口说出。

**机制线索**（本文只定语义，不定死实现）：

- 可见范围 = f(该角色在场记录、该角色历史产出中显式的"知晓/目睹/被告知"标记)；
- 事件打"可见性"标签（private/scene_known/public），角色的视图只聚合满足其可见性的事件；
- `shared_story_snippet` 由"全量公开流"改为"按角色过滤视图"（可保留一个场景级公开子集供氛围使用）。

**与多视角/单主角的关系（§1.2a 分层）**：信息不对称对**每个关键角色（含主角）平等生效**——主角在内部并不比他人看到更多，也不是全知视角；它只是被用户选定为主书导出镜头的那一个关键角色。**主书正文跟随用户选定的主角镜头**（其余关键角色在主书中仅在其被看到时展开），但**内部模拟保持多视角**——各关键角色的差异化认知/隐瞒/猜测仍是其独立演进的机制本体。

---

## 4.7 回合内二次反应链（U-6；对话而非拼接）

**问题**：默认单回合内所有在场关键角色**并行**各产出一份独立言行（`run_one_turn` 一次 wave），彼此没有"听到对方、再回应"的先后，多角色场面是并行拼接而非真实你来我往。

**模型（先发批 → 定向二次批 → 合并）**：
- **先发批**：各在场角色首波输出（现有行为），作为该回合"先说出口/先动作"的部分。
- **定向二次批**：先发批完成后，每角色看到**其他在场角色**的首波**公开言行**（`dialogue_action`），据此对其中与自己相关的一人给出一段简短定向回应。
- **合并**：将二次回应并入该角色的 `dialogue_action` / `inner_monologue`；另存 `reaction` 字段供观测，不落私有逐步记忆槽（随言行写成记忆即可）。

**可见性规则（承接 §4.6）**：二次批的 peers_snippet 只注入其他在场角色的**公开 `dialogue_action`**（同场者能听到的言语/动作），**不注入任何他人的私有 `inner_monologue`**——私有内心/计划不跨角色，只有公开言行触发回应，避免"上帝视角回应"。

**开关**：`runtime_config.agents.characters.react_chain`（bool，**默认关**）。关闭时输出与现状一致；壳/Dummy 路径不产生二次批。非目标：多轮串行话轮、结构化"谁回应谁"路由（由模型在 prompt 内自选回应对象）。

---

## 5. 与现有代码接入方案

### 5.1 新增 / 扩展模块

**就绪性核对**：`src/runtime/relationship_graph.py` 与 `src/retrieval/relationship.py` **已存在**（见 §4.5.2），本方案的承载基础是**新增**成长模块 + **扩展**已存在的关系模块，不再新增关系图库。

新增模块：

- `src/runtime/character_growth.py`（**新建**）
  - `load_growth_state(character_id, novel_root)`
  - `apply_growth_transition(character_id, event_bundle, context)`
  - `save_growth_state(...)`

- `src/retrieval/growth.py`（**新建**）
  - `format_growth_snippet(...)`（供角色/范围 Agent 注入）

- `src/retrieval/info_view.py`（**新建**，§4.6 信息视野）
  - `build_character_event_view(character_id, storage)`——返回该角色可见的事件视图/占位，供 `build_turn_context_from_storage` 按角色注入。

已存在、需扩展：

- `src/runtime/relationship_graph.py`：`sync_relationship_graph_after_scope_turn` 叠加语义边判定；`upsert_co_presence_edge` 之外新增 `upsert_semantic_edge`。
- `src/retrieval/relationship.py`：`format_relation_snippet` 已具备，按需增强呈现方向/强度/最近变化。

### 5.2 插入点（主流程）

在 `Orchestrator.apply_event_and_state_write` 后：

1. 读取本回合关键事件（含角色参与信息）
2. 对关键角色执行迁移（`character_growth.apply_growth_transition`）
3. 写入 `growth_state.yaml`
4. 记录 `transition_log`
5. 同步更新 relationship graph（在既有共现逻辑上叠加语义边与证据事件）

在 `build_turn_context_from_storage`（对齐既有主角/名册注入 `protagonist.format_main_characters_snippet`，该注入已接入 ScopeAgent 的计划/正文三处）：

- 注入 `character_growth_snippet`（当前成长状态 + 本回合边界 + 禁止跨级规则）
- 注入 `relationship_snippet`（当前关系网摘要 + 最近关系变化证据）
- **按角色过滤 `shared_story_snippet`**（§4.6 信息视野）：`format_main_characters_snippet` 注入的是"主角名册"，本项注入的是"各关键角色各自可见的事件视图"。

在角色生成 prompt：

- 注入“当前成长状态 + 本回合边界 + 禁止跨级规则”
- 注入“当前关系网摘要 + 最近关系变化证据”
- 注入“你的信息视野”（可见/未知事件的占位），与私有记忆共同决定角色的当下认知。

---

## 6. Growth Guard（强约束）

新增 `GrowthGuard` 校验，至少覆盖（以叙事一致性为核心）：

- 单回合成长跃迁边界（避免“无铺垫神跳级”）
- 无代价收益禁止（成长必须有代价、代偿或后遗症）
- 关系变化连续性（避免“无事件铺垫立场反转”）
- 目标切换频率限制（避免角色动机抖动）

校验失败策略：

- 拒绝本次迁移写回
- 记录告警（含失败规则）
- 尝试最小安全迁移（若可用）

---

## 7. 观测与审计

### 7.1 日志

- 每回合输出：
  - 角色迁移触发规则
  - 关键 delta
  - 被拒绝迁移原因

### 7.2 审计文件

- `transition_log` 保留最近 N 条（建议 100）
- 可选导出：
  - `data/novels/<slug>/book/characters/<id>/growth_audit.md`

---

## 8. 测试方案

### 8.1 单元测试

- 规则命中/不命中
- 校验失败回滚
- 冷却生效
- 代价扣减正确

### 8.2 集成测试

- 多回合后状态连续性
- 角色成长与事件因果一致
- Prompt 注入包含成长快照
- **信息视野过滤**：角色 prompt/事件视图不包含其未知事件（§4.6）——"未在场 + 未被告知"的事件不得泄露给该角色。

---

## 9. 分阶段实施计划

> 排名基于"关键角色独立演进"的性价比：**先让角色拥有差异化视野与客观关系，再铺五维迁移**，避免在"上帝视角 + 无关系语义"上做迁移而失真。

### 阶段 1a（MVP-A：差异化视野 + 语义关系——独立演进的前提）

- 建立 `growth_state.yaml` 结构与 `CharacterGrowthState` 数据类（含 `mind_state` 接入 `storage.emotions[]`，§2.1）
- §4.6 信息视野：`src/retrieval/info_view.py` 的可见性标签 + 按角色事件视图过滤，替换 `build_turn_context_from_storage` 的全量 `shared_story_snippet`
- §4.5 语义边：在既有 `relationship_graph.py` 上叠加 `relation_type/intensity/status` 语义判定（复用 `get_relation/get_neighbors/get_relation_change_log`）
- 三层记忆（L1/L2/L3）标签落库

### 阶段 1b（MVP-B：五维状态迁移）

- 增加 8~12 条“语义迁移规则”（非数值）
- 接入 `apply_event_and_state_write` 后的自动迁移（`character_growth.apply_growth_transition`）
- 记录 `transition_log` 并审计

### 阶段 2

- 加入 `GrowthGuard` 与拒绝回退机制
- 接入记忆分层标签的写入校验（事实不动/解释可更新/策略可过期）
- 完善测试与审计导出

### 阶段 3

- 与“设定深挖两段式”联动
- 对不同题材提供可切换规则模板（narrative_only/hybrid/numeric）

---

## 10. 验收标准

- 连续 20 回合角色状态变化可追踪、可解释
- 无“无代价跨级成长”异常
- 关键角色目标与关系变化具备因果闭环
- 两个关键角色对同一事件的**解读不一致**可被检索到（信息视野生效，§4.6）
- 不存在角色获得其未知事件的剧透注入（信息视野负例通过，§8.2）
- **多视角导出**（§1.2a）：任一关键角色的独立成长可被选为导出主角、以该角色为镜头重导出主书，且不改变其内部状态
- 单元+集成测试稳定通过

