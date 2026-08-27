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

全书 / 章 / 节拍结构见 [outline-and-beats.md](./outline-and-beats.md)。节拍与章仅作**主线指导**；角色成长仍以本文所述**事件驱动语义迁移**为主，节拍 `tags` 可作为可选提示，不做硬编码数值跳变。正文以主角为主线时，非主角成长仍落盘于各角色记忆与成长状态，与「并列主线」方案一致。

### 1.3 非目标

- 不在本阶段实现完整战斗数值系统。
- 不引入外部数据库；继续使用 YAML/MD 文件与现有存储机制。
- 不实现复杂可视化 UI，仅提供日志与文件可读性。

---

## 2. 角色成长状态模型

每个关键角色维护一个 `CharacterGrowthState`，分为五个子状态：

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

路径（小说级）：

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

---

## 4.5 关系知识图谱（Relationship Knowledge Graph）

为增强“角色关系线”的可追踪与可检索能力，建议新增轻量关系图谱层（文件化，不引入重型图库）。

### 4.5.1 定位

- **状态机**：描述“角色内部成长”与主观状态变化；
- **关系图谱**：描述“角色之间关系结构”与客观演化轨迹；
- 两者互补，避免仅靠回合摘要导致关系线丢失或跳变。

### 4.5.2 存储建议（小说级）

- `data/novels/<slug>/book/relationships/graph.yaml`
- 可选：`data/novels/<slug>/book/relationships/history/turn_XXXX.yaml`

### 4.5.3 数据结构（MVP）

- **节点（node）**：关键角色（后续可扩展势力/地点/物件）
- **边（edge）**：
  - `source_id`
  - `target_id`
  - `relation_type`（ally/trust/rival/debt/mentor/love/hate 等）
  - `intensity`（默认语义档位：low/med/high）
  - `status`（active/fragile/broken）
  - `evidence_events`（支撑该关系变化的事件 id 列表）
  - `last_updated_turn`

### 4.5.4 查询能力（先做最小集）

- `get_relation(a, b)`：查当前关系
- `get_neighbors(a, types=None)`：查角色一跳关系网
- `get_relation_change_log(a, b, last_k)`：查关系演化轨迹

### 4.5.5 与主流程接入点

- 在 `apply_event_and_state_write` 后，基于本回合事件更新关系边；
- 在角色生成前注入“关系图谱摘要”（近邻 + 最近变化）；
- 与 `social_state` 联动：图谱作为客观关系，`social_state` 作为角色主观感受，不强制完全一致。

### 4.5.6 约束原则

- 默认语义档位，不做重数值化（非游戏题材保持叙事温度）；
- 关系反转必须有事件证据（`evidence_events`）；
- 单回合关系跃迁受 `GrowthGuard` 约束（避免无铺垫突变）。

---

## 5. 与现有代码接入方案

### 5.1 新增模块

- `src/runtime/character_growth.py`
  - `load_growth_state(character_id, novel_root)`
  - `apply_growth_transition(character_id, event_bundle, context)`
  - `save_growth_state(...)`

- `src/retrieval/growth.py`
  - `format_growth_snippet(...)`（供角色/范围 Agent 注入）

- `src/runtime/relationship_graph.py`
  - `load_graph(novel_root)` / `save_graph(...)`
  - `update_edges_from_events(...)`
  - `query_relation(...)`

- `src/retrieval/relationship.py`
  - `format_relationship_snippet(...)`（供角色/范围 Agent 注入）

### 5.2 插入点（主流程）

在 `Orchestrator.apply_event_and_state_write` 后：

1. 读取本回合关键事件（含角色参与信息）
2. 对关键角色执行迁移
3. 写入 `growth_state.yaml`
4. 记录 `transition_log`
5. 同步更新 relationship graph（边变化与证据事件）

在 `build_turn_context_from_storage`：

- 注入 `character_growth_snippet`
- 注入 `relationship_snippet`

在角色生成 prompt：

- 注入“当前成长状态 + 本回合边界 + 禁止跨级规则”
- 注入“当前关系网摘要 + 最近关系变化证据”

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

---

## 9. 分阶段实施计划

### 阶段 1（MVP，通用版）

- 建立 `growth_state.yaml` 结构
- 增加 8~12 条“语义迁移规则”（非数值）
- 接入 `apply_event_and_state_write` 后的自动迁移
- 建立最小关系图谱结构（角色节点+角色边）与 3 个基础查询

### 阶段 2

- 接入记忆分层标签（事实/解释/策略）
- 加入 `GrowthGuard` 与拒绝回退机制
- 完善测试与审计导出

### 阶段 3

- 与“设定深挖两段式”联动
- 对不同题材提供可切换规则模板（narrative_only/hybrid/numeric）

---

## 10. 验收标准

- 连续 20 回合角色状态变化可追踪、可解释
- 无“无代价跨级成长”异常
- 关键角色目标与关系变化具备因果闭环
- 单元+集成测试稳定通过

