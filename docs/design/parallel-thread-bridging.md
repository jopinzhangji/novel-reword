# G1 SDD：屏外线 / 并列主线（Off-screen Evolution + Bridging）

**代号**：**G1**（全仓梳理 2026-08-31 三大优化主轴之首）；对应 [outline-and-beats.md](./outline-and-beats.md) **Phase 3**。
**类型**：SDD（L2）。**登记**：**[SPEC_SDD.md](../framework/SPEC_SDD.md) D10**。**状态**：**G1a 已编码 ✅**（2026-08-31）；G1b/G1c 待立项。

---

## 0. 一句话

让每个关键角色在**未入场**时也有真实独立的"生活"——屏外戏份持续累积为可追溯记忆、必要时做低成本演进；当主书下一场景依赖其屏外结果时，向正文管线注入**桥接摘要**（非全文）。这把"多视角内部独立演进"从"**仅在场角色累积**"补成"**全角色全程演进**"，主书仍以主角为镜头轴。

---

## 1. 背景与目标

### 1.1 现状（代码落地事实）

- 演进仅作用于**在场**角色：`orchestrator.apply_growth_transition_for_turn` 只遍历 `present_character_ids`（`character_growth.py:500`），且 `info_view` 只让角色见到 `present_characters` 标注其在场的事件（`info_view.py:13`）。**缺席 = 停滞**。
- 私密记忆以 L1 事实卡为主（`apply_memory_write`，orchestrator:333）；L2/L3 分层默认关（`agents.characters.memory_layers`）。
- 屏外概念在 [outline-and-beats.md](./outline-and-beats.md) §2.2/§2.3 有蓝图，但无数据模型、无触发模型、无桥接注入代码。

### 1.2 目标

1. **屏外数据模型**：每角色可累积 `off_screen` / `parallel_thread` 类型记忆条目，与主书 scope 事件分离、可追溯、可截断。
2. **屏外演进**：屏外戏份可**低成本**驱动成长/关系，避免"缺席即冻结的假独立"。
3. **桥接注入**：主书下一场景依赖某角色屏外结果时，向 `generate_turn_body` 注入短摘要（一两段结构化），不灌副线全文。
4. **主书轴线不变**：非主角仍仅在**在场**或**桥接摘要显式需要**时进入主书叙述（承接 outline-and-beats §1.1）。

### 1.3 非目标

- 不在此轮做**单角色同文导出**（Phase 4，独立立项）。
- 不承诺屏外线每回合全量 LLM 刷新（成本控制，见 §4 触发模型）。
- 不变更主书 scope 事件簿的单一数据源语义。

---

## 2. 术语

| 术语 | 含义 |
|------|------|
| **屏外线 / off-screen** | 角色不在当前场景（非 `present`）时发生的、累积于其私密记忆的独立活动。 |
| **并列主线 / parallel_thread** | 同世界观下另一条"真主线"的**记忆类型**；逻辑上可导出为番外/同文，主书仅消费摘要。 |
| **桥接摘要（bridging summary）** | 一段短摘要，来源为屏外记忆的（轻量 LLM 压缩或规则截取）产物，注入正文生成前，供角色把屏外结果带回主书。 |
| **演进回放（replay）** | 屏外戏份按触发模型**成批**（而非逐回合）交由 `apply_growth_transition` 迁移，控制成本。 |

---

## 3. 屏外数据模型（与 memory-layers 融合）

沿用 `memory_layers.build_layer_entry` 的标签体系，新增**记忆类型字段** `thread: "off_screen" | "parallel_thread"`，与既有 `layer`（L1/L2/L3）正交：

```yaml
# 示例：<characters/<id>/threads/off_screen.yaml> 片段
version: 1
entries:
  - id: off_0001
    thread: off_screen
    turn_index: 37          # 主书回合锚（屏外时间线对齐用，可空）
    scope_snapshot: "城北驿站"   # 角色自述所处（弱，不强制对齐主书 scope）
    layer: L1               # 复用三层分类
    summary: "受柳家所邀，夜访其地窖，留意到一具被秘药封存的棺椁。"
    tags: [romance, resource_gain]
    updated_at: "2026-08-31T..Z"
```

- **落盘位置**：`<data_root>/book/characters/<id>/threads/off_screen.yaml`（与 `growth_state.yaml` 同目录族），不混入主书 `events/`。
- **写入通道**：新增 `MemoryStorage.append_off_screen_refinement(...)`（镜像 `append_event_refinement`，带 `thread` 标签）；写回由作者/触发在 `apply_memory_write` 之侧异步/批处理发起（见 §4）。
- **截断策略**：与 L3 一致——每条目带 `updated_at`/`turn_index`；按"最近 N 条 + 移除最旧已消费"原则，防止无限增长。
- **来源**：谁生成屏外条目？**规则/作者在环**为主：①作者在主书回合侧显式补充"XX 屏外在做什么"；②可选**轻量 LLM 摘要压缩**（挂 `internet/memory` 预算，非默认）。第一版不强求 LLM 自动编剧。

---

## 4. 触发模型（resolve outline-and-beats §9.2 开放项）

原设计遗留问题"屏外线更新是**按需/按标签**还是**定时批处理**"。**G1 裁决**：

> **默认「按需 / 按标签」，批处理为可选增强，不做逐回合全量刷新。**

理由（成本 × 真实度权衡）：

| 模型 | 优点 | 缺点 | G1 选用 |
|------|------|------|---------|
| 逐回合 LLM 刷新 | 平行线最"活" | 每回合副线费用不可控；与"单一主角导出"收益失衡 | ✕ |
| **按需/按标签** | 便宜、可解释、作者可预期 | 屏外线细粒度上略滞后 | ✅ 默认 |
| 定时批处理 | 覆盖率均匀 | 时机不可控、可能空转 | ⚪ 可选（G1c） |

**具体触发条件**（满足其一即触发一次屏外演进）：
1. **作者显式**：在桥接菜单或在主书回合补充设定处标"给 <角色> 补一段屏外戏"。
2. **节拍/大纲标签**：当前节拍 `tags` 含 `cross_character` / `off_screen`（承接 [outline-and-beats.md](./outline-and-beats.md) §2.3 触发方式）。
3. **桥接缺口**：正文生成前检测"主书下一场景引用了某角色但该角色非 present"→ 需要该角色屏外结果时（§5）。

---

## 5. 桥接摘要注入（核心消费点）

### 5.1 触发与检测
在 `generate_turn_body` / `build_turn_body_prompt` 之前，由主流程检测当前回合是否**需要**某非在场角色的屏外结果：
- 依据：节拍 `character_hooks`（[outline-and-beats.md](./outline-and-beats.md) §3.1）或作者在桥接菜单勾选。
- 缺省：**一键关闭**（默认不自动搜屏外线灌摘要），仅在作者或标签明确需要时注入，保持主书零侵入。

### 5.2 注入点
- **新片段**：`build_turn_body_prompt`（`turn_planning.py`）增加可选 `bridging_snippet`；渲染为 `【桥接摘要（<角色> 屏外结果）】` 块，置于场景说明之后、主要角色名册之前。
- **片段内容**：取该角色 `threads/off_screen.yaml` 最近未消费条目，经 `format_bridging_snippet`（规则截断 ≤ 某预算字符）或可选轻量 LLM 压缩为 1～2 段；**不**注入副线全文。
- **可观测**：`TurnContext` / 日志记录 `bridging_character_ids`、来源条目 id，便于核对与回滚。

### 5.3 主书约束重申
桥接注入**不改变**主书叙述规则：非主角仍只在**在场**或**摘要铰链**处进入主书（§1.2.4）；桥接摘要用于"该角色为何此刻把屏外结果带回"，而非展开其整条副线。

---

## 6. 与既有模块接线（代码落点）

| 模块 | 现状 | G1 改动 |
|------|------|---------|
| `src/runtime/storage.py` | `_char_*` 桶，`append_event_refinement` | 增 `threads` 桶 + `append_off_screen_refinement` / `get_recent_off_screen(limit, thread)` |
| `src/runtime/memory_layers.py` | `build_layer_entry` 打 `layer/scope_id/...` | `build_layer_entry` 支持 `thread` 字段 |
| `src/runtime/file_sync.py` | 主书 `events/<scope>`/`characters/<id>/events` | 增 `threads/<id>/off_screen.yaml` 读写（与 growth 同目录族） |
| `src/runtime/character_growth.py` | `apply_growth_transition_for_turn`（present-only） | 增 `apply_off_screen_transition_for_turn`：按屏外条目 tags 迁移，`GrowthGuard` 复用；演出不经过主书事件簿 |
| `src/orchestrator/orchestrator.py` | `apply_memory_write` | 触发点时在 `apply_memory_write` 之侧写入屏外条目；桥接需要时把 `bridging` 字段带到 `TurnContext` |
| `src/context/__init__.py` | `TurnContext` | 增 `bridging_snippet`（可选，默认为空） |
| `src/author_loop/turn_planning.py` | `build_turn_body_prompt` | 增 `bridging_snippet` 参数与块渲染 |
| `src/author_loop/cli.py` / `run_novel_with_author.py` | 阶段一/二审阅 | 桥接菜单（作者补屏外戏 / 勾选需屏外结果）+ 两级写回后可选屏外演进 |

**与 Harness/U-1 关系**：桥接片段可视为 `retrieve_for_intent` 的一个新数据源（`threads`），后续并入"检索完整方案"；本 G1 先做直连注入，不强行改 Harness。

---

## 7. 配置项

```yaml
# runtime 级（均在 <小说>/config/runtime.yaml 可覆盖）
runtime:
  parallel_threads:
    enabled: false          # 默认关（船身不破）
    trigger: "on_demand"    # on_demand | batch（默认按需）
    batch_turns: 5          # 仅 batch 生效：每 N 回合扫一次
    bridge_budget_chars: 400  # 桥接摘要预算字符
    llm_compress: false     # 可选：轻量 LLM 压缩摘要（Dummy 则规则截断）
```

---

## 8. 分阶段落地

| 阶段 | 内容 | 验收 |
|------|------|------|
| **G1a 数据与演进** | `storage/file_sync/memory_layers` 增 `threads`/`off_screen`；`append_off_screen_refinement` + `apply_off_screen_transition_for_turn`（replay 迁移 + GrowthGuard） | 单测：屏外条目落盘 round-trip；按标签触发演进、非在场角色状态可增长、主书事件簿不变 |
| **G1b 桥接注入** | `TurnContext.bridging_snippet` + `build_turn_body_prompt` 块 + 桥接菜单（作者补充 / 勾选）；`format_bridging_snippet` | 单测：需桥接时块入库；未触发时正文 prompt 无桥接（默认关）；桥接来源可追溯 |
| **G1c 批处理（可选）** | `trigger=batch`：每 `batch_turns` 扫一次各角色 `threads` 累积演进 | 单测：批次触发、无新戏不空转 |

---

## 9. 关联文档

- [outline-and-beats.md](./outline-and-beats.md)：**Phase 3** 蓝图（§2.2 平行主线层、§2.3 桥接层、§5 接入点）；本 SDD 是其可执行细则。
- [character-growth-state-machine.md](./character-growth-state-machine.md)：成长迁移规则 + `GrowthGuard`（屏外演进复用）。
- [memory-storage-and-retrieval.md](./memory-storage-and-retrieval.md)：记忆目录与双写（`threads` 并入 `book/characters/<id>/`）。
- [ownership / D-series]：[SPEC_SDD.md](../framework/SPEC_SDD.md) **D10**。

---

## 10. 修订记录

- **2026-08-31**：G1 SDD 初稿；裁决 §9.2 开放项（默认按需/按标签）；登记 **D10**；与大纲 Phase 3、成长状态机、next-iteration G1 焦点互链。