# G2 SDD：演进层 ↔ 叙事策略层耦闸（Evolution ↔ Pacing Coupling）

**代号**：**G2**（全仓梳理 2026-08-31 三大优化主轴之二；紧接 **G1** 屏外线/并列主线）。
**类型**：SDD（L2）。**登记**：**[SPEC_SDD.md](../framework/SPEC_SDD.md) D11**。**状态**：**文档闸 ✅、编码 ✅**（2026-08-31，一次 MVP）。

---

## 0. 一句话

让**成长/关系/信息视野（演进层）**与**节奏契约/审阅（叙事策略层）**在同一回合**互相可影响**：
演进状态喂给正文生成前的节拍裁定与正文后的 Critic（反馈前馈），节拍 `tags` 真正驱动当回合成长（反馈回路），全程可观测。默认关，船身不破。

---

## 1. 背景与目标

### 1.1 现状（代码落地事实）

- **演进层**跑在编排器**写回**侧：`Orchestrator.apply_event_and_state_write`（`B orchestrator.py:236`）在回合正文写回后调
  `apply_growth_transition_for_turn`（`character_growth.py:500`），仅对**在场**关键角色做五维语义迁移 + `GrowthGuard` 约束，
  落盘 `growth_state.yaml`、mind 写 emotions。信息视野（`info_view`）与语义关系边（`relationship_graph`）同在写回侧累积。
- **叙事策略层**跑在 `turn_planning` 内：`generate_turn_body` 先 `resolve_pacing_contract`（`policy_assembler.py:24`，从
  `chapter_goal`/pace_mode 推 `goal_window`=铺垫/推进/兑现 → 产出约束块），正文生成后 `evaluate_body_against_pacing`
  （`critic.py:21`，规则关键词评分，Dummy 场景也跑）。
- **互不调用**：两层共享 `runtime_config`，但成长状态不进入契约/Critic 输入；节拍 `tags` 目前仅在正文 prompt 作为**弱提示**
  （`outline_store.py:317` 渲染「标签：…」），不实际影响成长迁移规则命中（`match_rules_for_event` 仅看 summary 关键词，`character_growth.py:275`）。
- 大纲 `BeatContext` 已带 `tags: list[str]`（`outline_store.py:180`），可作为节拍→成长的载体，尚无消费。

### 1.2 目标

1. **成长 → 节奏（前馈）**：单回合正文生成前，把在场角色的演进状态（五维触发积累、「兑现边缘」信号）译为节拍倾向，
   微调 `PacingContract.goal_window`/`forbidden_moves`（如成长已到兑现点 → 契约向「兑现」偏置，正文该回收而不宜继续埋坑）。
2. **成长 → 审阅（前馈）**：`Critic` 对正文的暗线显露评分结合成长基线——某在场角色挂有未兑现的成长回响（如「受恩于人」/「突破契机」）
   而正文未承接，则判定为悬置回响，小幅上调 `subplot_reveal_deviation`，提示作者/审阅。
3. **节拍 → 成长（反馈）**：把 `BeatContext.tags` 真正喂进当回合成长迁移——按「标签→迁移规则」映射**补足命中**，使节拍意图
   （如标 `growth:action`、`dimension:social`）实影响该回合演进，而不再只是弱提示。
4. **可观测**：两次耦合的输入/输出在 `TurnContext`/日志可见（记录 `growth_window_override`、用的 `beat_tags`、Critic 输入是否含成长基线）。

### 1.3 非目标

- 不再做逐回合 LLM 成长刷新（承接 G1 成本控制裁决）；成长数据源仍 `growth_state.yaml` 单一。
- 不重写 `/` Critic 评分器（在既有接口上加 `growth*` 可选输入与一条悬置回响判据）。
- 不变更演进层的语义迁移规则本身（`_RULES`）；只加「节拍标签补足命中」这一**可选**旁路。

---

## 2. 术语

| 术语 | 含义 |
|------|------|
| **成长站姿（growth standings）** | 对在场角色成长状态的**紧凑聚合**：五维计数、已集结/可兑现回响的标记派生，供契约/Critic 用（非长文本 prompt 块）。 |
| **兑现边缘（payoff edge）** | 某角色成长已积累到「该回收回响」的信号（如受恩于人、突破契机等目标型规则已有计数）而未在正文兑现。 |
| **节拍标签旁路（beat-tag bypass）** | `BeatContext.tags` → 迁移规则名的映射，命中即**补足**该规则到本回合触发集合（可选、默认关）。 |

---

## 3. 前馈耦合：成长 → 节奏与审阅

### 3.1 成长站姿（新 `evolution_pacing.py`，`author_harness` 下）

```python
@dataclass(frozen=True)
class GrowthStandings:
    by_character: dict[str, dict]   # {cid: 该角色五维计数 snapshot + edge 标记}
    payoff_edge: list[str]          # 处于兑现边缘的角色 id（aggregated）
    def empty() -> GrowthStandings ...
```

- `load_growth_standings(data_root, characters_config, present_character_ids) -> GrowthStandings`：读 `load_growth_state`（缺省空状态），
  聚合在场角色五维 `power/social/resource/mind/will` 计数；凡**目标影响型规则**（`character_growth._GOAL_RULES` = 会改目标的规则，如
  `goal_affirmed`/`trusted_betrayal`/`deep_loss`）对应维度计数 ≥1 且本回合正文尚未回用 → 记入 `payoff_edge`。确定性、无磁盘写。
- `format_standings_hint(standings) -> str`：转一行紧凑提示（给 Critic 解释用），空返回空串。

### 3.2 契约偏置（`policy_assembler.py`）

- `infer_growth_window(standings) -> "铺垫" | "推进" | "兑现" | None`：`payoff_edge` 非空 → `"兑现"`；全角色休眠/无在场 → `None`（不偏置）。
- `override_contract_for_growth(contract, standings) -> PacingContract`：在现有契约基础上，仅当 `infer_growth_window` 返回非 None 时
  **覆盖 `goal_window`** 并相应调整 `forbidden_moves` 追加一条「勿悬置已到兑现点的角色回响」；其余字段原样。None → 返回原契约（零改动）。
- `resolve_pacing_contract(runtime_config, *, chapter_goal, requested_mode, growth_standings=None)`：新增可选参，内部委托 override。

### 3.3 Critic 审阅（`critic.py`）

- `evaluate_body_against_pacing(contract, body, growth_standings=None)`：新增可选参。当 `growth_standings.payoff_edge` 非空且正文
  （`body`）未出现该角色回响关键词 → 在原有 `subplot_reveal_deviation` 上**小幅上调**（+0.15，封顶 1.0）并更新 `reason`；
  若正文已承接则不加。默认 None → 行为与原逻辑完全一致。

### 3.4 接线（`turn_planning.generate_turn_body` + `run_novel_with_author`）

- `generate_turn_body` 增 `growth_standings=None`；仅当 `runtime.evolution_pacing.enabled` 才在 resolve 契约/调 Critic 时传入（否则传 None，行为等价旧版）。
- 调用侧（`run_novel_with_author` 回环，ctx 已建）：按 gated 从 `_dr` 调 `load_growth_standings` 传入两处 `generate_turn_body`。
- 可观测：`TurnContext.growth_hint` 或日志记录 `growth_window_override` 与 `payoff_edge`。

---

## 4. 反馈耦合：节拍 → 成长

### 4.1 节拍标签补足命中（`character_growth.py`）

- 映射表 `BEAT_TAG_TO_RULES: dict[str, tuple[str, ...]]`（如 `{"growth:power": ("power_gain",), "growth:social": ("rescue_debt",), "growth:action": (…)}`，
  穷举规则名以 `_RULES` 为准；未收录的标签忽略）。
- `match_rules_for_event(summary, extra_tags=())`：现有关键词匹配不变；当 `extra_tags` 命中映射，把对应规则名**补足**进 fired（去重）。
  默认无 tags → 与原逻辑逐字节一致。
- `apply_growth_transition_for_turn(..., beat_tags=())`：新可选参；构造 `event_bundle["beat_tags"]` 并传给 `match_rules_for_event(summary, beat_tags)`。
- **讨论**：为何是「补足」而非「过滤」？节拍意图应**放大**当回合成长而非取代事件语义；实测有既有 guard 约束（GrowthGuard 仍会对无代价收益拒之），
  补足后可经 guard 复核，不破坏 GrowthGuard 的守恒语义。

### 4.2 接线（`run_novel_with_author` → `apply_event_and_state_write`）

- `Outlining.*` 已提供 `outline_beat.tags`；在阶段一写回处把 `outline_beat.tags` 透传进 `apply_event_and_state_write(result, …, beat_tags=…)`。
- 若 `runtime.evolution_pacing.beat_tags_to_growth` 为 false（默认）→ 传空元组（行为不变）。

---

## 5. 配置项

```yaml
# runtime 级（可在 <小说>/config/runtime.yaml 覆盖）
runtime:
  evolution_pacing:
    enabled: false            # 总开关：关 → 成长不进节奏/审阅，船身零变更
    beat_tags_to_growth: false  # 节拍标签补足命中（即使 enabled=true 也可单独关）
```

---

## 6. 与既有模块接线（代码落点）

| 模块 | 现状 | G2 改动 |
|------|------|---------|
| `src/author_harness/evolution_pacing.py`（新） | — | `GrowthStandings` + `load_growth_standings` + `format_standings_hint` |
| `src/author_harness/policy_assembler.py` | `resolve_pacing_contract(runtime…, chapter_goal, requested_mode)` | 增 `growth_standings=None`、`infer_growth_window`、`override_contract_for_growth` |
| `src/author_harness/critic.py` | `evaluate_body_against_pacing(contract, body)` | 增 `growth_standings=None` + 悬置回响判据 |
| `src/author_loop/turn_planning.py` | `generate_turn_body(…, main_characters_snippet, bridging_snippet)` | 增 `growth_standings=None`，gated 后传入 |
| `src/runtime/character_growth.py` | `match_rules_for_event(summary)`；`apply_growth_transition_for_turn(…, guard)` | 增 `BEAT_TAG_TO_RULES` + `match_rules_for_event(summary, extra_tags)` + `apply_growth_transition_for_turn(…, beat_tags)` |
| `src/orchestrator/orchestrator.py` | `apply_event_and_state_write(result, scope_id, time, place)` → growth 写回 | 增 `beat_tags=()` 可选参透传 |
| `src/context/__init__.py` | `TurnContext` 已有 bridging_snippet | 本轮可观测改由日志承担（`[G2] 前馈成长站姿` info/debug）而非新增 `growth_hint` 字段，避免扰动 builder 面（后续需要再补） |
| `run_novel_with_author.py` | 回环 gated 桥接/批处理 | 按 `evolution_pacing.enabled` 加载 standings 传 body；把 `outline_beat.tags` 透传写回 |

---

## 7. 分阶段落地（本 SDD 一次 MVP）

| 阶段 | 内容 | 验收 |
|------|------|------|
| **G2 编码** | 新 `evolution_pacing.py` + 契约偏置 + Critic 悬置回响 + 节拍标签补足 + 两侧接线 + 单测 | ✅（2026-08-31）：`evolution_pacing.py`（`GrowthStandings`/`load_growth_standings`/`format_standings_hint`）；`resolve_pacing_contract` 增 `growth_standings` + `infer_growth_window`/`override_contract_for_growth`；`evaluate_body_against_pacing` 悬置回响；`match_rules_for_event`/`apply_growth_transition_for_turn`/`apply_event_and_state_write` 透传 `beat_tags`；`run_novel` 按 `evolution_pacing` 门控前馈/反馈；8 条单测，全量 359 通过 + 1 跳过 |

**验收总纲**：默认 `enabled=false` 全量回归与 G1 末一致（351 通过 + 1 跳过）；`enabled=true` 时单测覆盖三类断言，且无 LLM 参与。

---

## 8. 不做（留后续）

- 节拍 `tags` → **策略**（PacingContract）直连（先做 → 成长与 → Critic 两条前馈 + → 成长一条反馈；节拍直接改契约留待体验验证）。
- 单角色持久化档 / 运行时主角切换（G3）。
- Critic 多维度大改。

---

## 9. 关联文档

- [parallel-thread-bridging.md](./parallel-thread-bridging.md)：G1（屏外演进 + 桥接 + 批处理），演进层数据侧；本 SDD 复用其成长栈/`GrowthGuard`。
- [character-growth-state-machine.md](./character-growth-state-machine.md)：成长迁移规则 + `GrowthGuard`（`_RULES`/`_GOAL_RULES` 来源）。
- [outline-and-beats.md](./outline-and-beats.md)：节拍/`BeatContext.tags` 载体。
- [author-in-loop-spec.md](../specs/author-in-loop-spec.md)：叙事策略层/Harness 交互。
- [SPEC_SDD.md](../framework/SPEC_SDD.md)：**D11**。

---

## 10. 修订记录

- **2026-08-31**：G2 SDD 初稿；登记 **D11**；与 next-iteration G2 项挂链；与 G1 屏外线互链。