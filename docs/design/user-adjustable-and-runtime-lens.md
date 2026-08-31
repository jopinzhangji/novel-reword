# G3 SDD：用户可调收敛 + 运行时主角切换（Capability Surface + Runtime Lens）

**代号**：**G3**（全仓梳理 2026-08-31 三大优化主轴之三；紧接 **G1** 屏外线/并列主线、**G2** 演进层耦闸）。
**类型**：SDD（L2）。**登记**：**[SPEC_SDD.md](../framework/SPEC_SDD.md) D12**。**状态**：**文档闸 ✅**；编码 ⏳（一次 MVP）。

---

## 0. 一句话

把散落于配置深层的能力开关收敛成**统一「能力开关」外观面**（`runtime.features`），并给作者一个**不手改配置文件**即可在场互动地开关能力 / 换主角镜头的出口（CLI 交互 + 未来 D9 `/system` 同契约）。默认全部关，船身不破。

---

## 1. 背景与目标

### 1.1 现状（代码落地事实）

> **两层架构（本 SDD 的显式前提）**：**演进层**（内部生成）中，关键多角色**各自独立演进**（成长/记忆/信息视野/关系边，G1/G2 载体），
> **与镜头选择无关**、照常累积；**导出层**（最终成文）中，**任意时刻只有一个「运行时镜头」= 作者最终选定的小说内容（正篇成文）**，
> 其余关键角色只在演进层继续、不进入成文，除非作者重选镜头。**镜头是「最终内容的选择器」，不是演进的对象。**

- **开关散落**：每项增强各自在 `runtime_config` 深层 `runtime_config.get(..., False)`/`agents.*.enabled_ids` 处门闩——
  `setting_research.enabled`、`runtime.parallel_threads.enabled`（G1 桥接/屏外批）、`runtime.evolution_pacing.{enabled, beat_tags_to_growth}`（G2）、
  `runtime.react_chain.enabled`（U-6 二次反应链）、`runtime.internet_search.enabled`（联网，见 `internet_search.py:77`）、
  `agents.characters/scopes.enabled_ids`、三层记忆分层/信息视野/语义边等。**互无统一读法、无统一写口**，作者要改能力只能编辑 YAML。
- **导出镜头仅配置期**：`resolve_protagonist_id`（`protagonist.py:10`）只在 `novel_run.protagonist_id` 或 `is_protagonist` 解析一次，
  run_novel（L99）在 **loop 外**定死 `_prot_id/_prot_name`，整本不可换镜头——「单一主角导出」目前实际上是「**全书固定单一**成文镜头」，
  **演进层多角色独立**已由 G1/G2 承载，只差**导出镜头运行时可重选**这一环。
- **D9 `/system` 可写未立**：`novel-reader-ui.md §5.6/§8.7` 已定义 `GET/PATCH /system/config` 白名单写口，但 W3 待立项；作者侧可调出口尚未有承载面。

### 1.2 目标

1. **统一能力外观面**：新增 `runtime.features: {name: bool}` 作为**唯一规范读法**，`resolve_features(runtime_config)` 聚合返回
   `CapabilityFlags`（全默认关），并对仍走**旧深层位置**的调用点做一次性 `WARN` 提示迁移；新增 per-novel `config/features.yaml` 可写覆盖，
   作者改能力不必侵入合并后 `runtime.yaml` 的深层结构。
2. **运行时镜头切换（= 最终成文镜头重选，含候选备选稿档）**：新增 `ProtagonistContext`（可变、会话内持有当前**导出镜头**），`switch_protagonist(...)` 校验后翻转；
   run_novel 在**作者交互点**提供「换主角」出口，**下一回合起**正篇成文（主角约束、scope 主轴）即按新镜头。**显式提升的备选稿**可**替稿单章**（作者选定档），
   其余情况切换只影响后续回合成文、不回写改写历史章节；演进层多角色照常独立累积、不受镜头影响。持久化到 `state/protagonist_runtime.yaml`，跨回合/续读生效。
3. **作者交互出口（CLI 优先 + D9 同契约）**：在 run_novel 既有 `read_line` 作者交互点挂一「能力/镜头」菜单
   （开/关某能力、换主导镜头、生成/提升候选备选稿），写回会话态；并把同一 `resolve_features` / 主角切换**对外契约**明文映射到 D9 W3 `/system`
   （`runtime.features` ← `PATCH /system/config`；`PUT /session/protagonist` ← 换主导镜头）。
4. **可观测 / 不破船**：`CapabilityFlags` 可判空、可序列化；默认 `features={}`（逐项关）时全量行为与 G2 末一致。

### 1.3 非目标

- **不**在 G3 内建 D9 Web（W3 仍待立项）；G3 只交付规范表面 + CLI 出口 + 放 docs 里的 W3 契约映射。
- **不**重写倍率/收益/成长规则（成长语义归 G2）；主角切换只改**导出镜头**，不改角色自身的演进/记忆/成长数据。
- **不**做多主角并列叙事（仍单镜头）；`protagonist.py` 多 `is_protagonist` 告警逻辑保留原样。
- **不**把现有深层 `.get(...)` 调用点一次性全删重写——本 SDD 收敛**新统一读法**并迁移 run_novel 一侧的门闩；其余尽力而为、余下照旧 WAORM 兼容。

---

## 2. 术语

| 术语 | 含义 |
|------|------|
| **能力开关（capability switch）** | 一个布尔增强门闩，如桥接摘要、演进耦闸、反应链、离线批、联网检索。统一读法 = `runtime.features.<name>`。 |
| **能力外观面（capability surface）** | `CapabilityFlags` + `resolve_features`：把散落深层位置的开关聚合为单一规范入口。 |
| **运行时镜头（runtime lens）** | 作者在运行期选定的**最终成文镜头** = 此刻唯一进入正篇导出的小说内容选择器，存于 `ProtagonistContext`，按章/弧可重选，覆盖配置期 `protagonist_id`。**只管导出层「哪条变正篇」**，不改演进层。 |
| **演进层 / 导出层两分** | 演进层 = 关键多角色各自独立演进（成长/记忆/视野/关系边，与镜头无关）；导出层 = 单镜头成文（某时刻唯一）。运行时镜头切换落在**导出层**。 |
| **per-novel 覆盖（features.yaml）** | 小说级 `config/features.yaml`：作者不侵入合并后 runtime 深层，直接开/关能力的写口。 |

---

## 3. 能力外观面（新 `src/runtime/capabilities.py`）

```python
@dataclass(frozen=True)
class CapabilityFlags:
    stream_change_enabled = False
    # G1 桥接/离线批
    bridging: bool = False
    off_screen_batch: bool = False
    # G2 演进耦闸
    evolution_pacing: bool = False
    beat_tags_to_growth: bool = False
    # U-6 二次反应链 / 联网/ 检索 / 增强记忆 / 视野 / 语义边
    react_chain: bool = False
    internet_search: bool = False
    memory_layers: bool = False
    info_view: bool = False
    semantic_edges: bool = False
    alt_draft: bool = False       # 候选备选稿（§4.1）——默认关，作者显式开启后方可生成/提升
```

- `resolve_features(runtime_config, *, features_override: dict | None = None, data_root: Path | None = None) -> CapabilityFlags`：**唯一规范读法**。
  优先读 `runtime.features`；缺失字段回退到**旧深层位置**（下表）并在首次命中时 `logger.warning`（一次性提示迁移）；`features_override`（会话内作者改动）最后覆盖。
  默认全 False。
- `capabilities_to_dict(flags) -> dict` / `capabilities_from_dict`：序列化（供 `features.yaml` 落盘 / `/system/config` 表单调回）。
- `save_features(data_root, override) -> Path | None`：写 `config/features.yaml`（仅覆盖键，不整树重写）；`load_features(data_root) -> dict` 读回。

**旧深层位置回退表**（命中即 WARN「请迁移到 novel 级 config/features.yaml」）：

| 能力名 | 旧位置 |
|--------|--------|
| `bridging` | `runtime.parallel_threads.enabled` |
| `off_screen_batch` | `runtime.parallel_threads.enabled`（trigger=batch 时才随批） |
| `evolution_pacing` | `runtime.evolution_pacing.enabled` |
| `beat_tags_to_growth` | `runtime.evolution_pacing.beat_tags_to_growth` |
| `internet_search` | `setting_research.internet_search.enabled`（fallback 到 deep） |
| `react_chain` / `memory_layers` / `info_view` / `semantic_edges` | 各自既有的深层位置（未命中即 False） |

---

## 4. 运行时镜头（新 `src/runtime/protagonist_switch.py`）

> **语义**：运行时镜头 = **最终成文镜头**。它决定了「此刻哪条正篇变最终小说内容」，**不**约束多角色独立演进——
> 演进层照常每一关键角色各自累积，镜头切换只改导出层的成文视角。**切换是前向的**：只影响后续回合写出的正篇，
> 已写章节不回写改写；作者可随时再切回/再切到另一角色，演进数据始终不动。

```python
@dataclass
class ProtagonistContext:
    protagonist_id: str | None = None
    display_name: str | None = None
    def is_override(self) -> bool: return bool(self.protagonist_id)
```

- `switch_protagonist(ctx, runtime_config, characters_config, target_id) -> tuple[str|None, str|None]`：
  校验 `target_id` 存在于 `characters_config.characters[].id`（不在则 `WARN` 返回原镜头不变）；在则沿用 `protagonist.py` 的显示名解析，
  更新 `ctx`；返回 `(protagonist_id, display_name)`。
- `load_protagonist_context(data_root) -> ProtagonistContext`（读 `state/protagonist_runtime.yaml`，缺省用配置期解析值）；
  `save_protagonist_context(data_root, ctx) -> Path | None`（写 `state/protagonist_runtime.yaml`，`{protagonist_id, display_name}`）。
- `effective_protagonist(runtime_config, characters_config, ctx=None) -> tuple[str|None, str|None]`：
  `ctx.is_override()` 时取 ctx，否则委派 `resolve_protagonist_id` → **统一镜头判定**，供 run_novel L99 及主角提示注入复用。

### 4.1 候选镜头 · 备选稿机制（新 `src/runtime/alt_draft.py`，作者选定档）

> **定位**：在「切换是前向、只影响后续回合」之上，再加一层**备选稿（alt draft）**：作者在某章下可**临时**以另一镜头生成一条
> 该章正篇正文的**备选稿**做比较，选定后**提升（promote）**为最终成文并由此切换导出镜头。备选稿**不进演进/不进主书事件簿立库**
> （dry-run：不触发成长迁移、不写 events、不写记忆），**每时刻仍只有一条成文**，不生成各角色的平行整树文本。

```python
# state/drafts/{chapter_id}_{lens_id}.md 头
# ---
# type: alt_draft
# chapter_id: <str>
# lens_id: <str>            # 以谁为镜头生成的备选稿
# status: draft | promoted
# ---
```

- `write_alt_draft(data_root, chapter_id, lens_id, body) -> Path`：建 `state/drafts/` 并写带头创建备选稿（幂等覆盖同名）。
- `list_alt_drafts(data_root, chapter_id) -> list[dict]`：读回该章所有 `status=draft` 的备选稿（供作者对比/选择）。
- `promote_alt_draft(data_root, chapter, lens_id) -> tuple[Path, str] | None`：把 `status` 置 `promoted`，把正文**提升**为该章正篇成文
  （写入 canonical 常显路径），并返回 `(canonical_path, lens_id)` —— 调用方据此 `switch_protagonist(ctx, …, lens_id)` 切换导出镜头。
- **不自动消费**：备选稿生成全程不触发 `apply_growth_transition_for_turn`/`apply_event_and_state_write`；
  提升也不重放演进（演进只认最终成文所在回合，备选稿是「试探镜头」，不视为真实事件）。

---

## 5. 交互出口（run_novel + D9 契约映射）

## 5. 交互出口（run_novel + D9 契约映射）

### 5.1 run_novel 作者交互（CLI）

- loop 外：一次 `CapabilityFlags = resolve_features(runtime)`、`ProtagonistContext = effective_protagonist(...)`，替代 L99 仅配置期解析。
- 在既有交互点（L583 `_adv = read_line(...)` 作者审阅之后 / L558 `apply_event_and_state_write` 之后）挂一**可选**菜单项：
  - 「**🧭 镜头/开关**」→ 子菜单「换主导镜头 / 生成候选备选稿 / 开关能力 / 返回」；
  - 「换主导镜头」→ 列出 `characters` 可选项 → `switch_protagonist` → 更新会话内 `_prot_id/_prot_name` 与 `main_characters_snippet`，
    后续回合正文/分析 prompt 即按新镜头（复用 `format_main_characters_snippet`，不给 `novel_run.protagonist_id` 写盘）；
  - 「生成候选备选稿」→ 选另一角色镜头 → **dry-run** 重生成该章正文（`alt_lens_id` + `draft_mode=True`，不触发成长/事件/记忆写回）
    → `write_alt_draft`；作者对比后「提升」→ `promote_alt_draft` → 该稿成为该章最终成文，并 `switch_protagonist` 切到该镜头；
  - 开关能力 → 写会话 `features_override` 并（可选）`save_features` 到 `config/features.yaml`，下一回合起生效。
- **默认无菜单打扰**：仅当 `runtime.author_workbench.enabled` 或运行到作者审阅点时展示；开关/换镜头/生成备选稿均为**显式操作**，
  **自动态全程只有**备选稿（`status=draft`）**不会**写入正篇/演进，静默跳章照旧不做。

### 5.2 D9 `/system` 契约映射（本 SDD 只留文，W3 立项后复用）

| D9 端点 | 读/写 | 复用的本表面 |
|--------|------|--------------|
| `GET /system/config` | 读 | `resolve_features` + `capabilities_to_dict`（每项 `source: system|novel|novel_runtime`） |
| `PATCH /system/config`（scope=novel，白名单 `features.*`） | 写 | `save_features(data_root, patch)` → 后续 `resolve_features` 读到 |
| `PUT /session/protagonist`（W3 会话 API） | 写 | `switch_protagonist` + `save_protagonist_context` |

---

## 6. 与既有模块接线（代码落点）

| 模块 | 现状 | G3 改动 |
|------|------|---------|
| `src/runtime/capabilities.py`（新） | — | `CapabilityFlags` + `resolve_features` + 序列化 + `load_features`/`save_features` |
| `src/runtime/protagonist_switch.py`（新） | — | `ProtagonistContext` + `switch_protagonist` + `effective_protagonist` + 持久化 |
| `src/runtime/protagonist.py` | `resolve_protagonist_id` / `format_main_characters_snippet` | **不改**（被 `effective_protagonist` 复用） |
| `run_novel_with_author.py` | L99 配置期定死主角；能力散点 `.get(...)` | loop 外一次 `resolve_features`/`effective_protagonist`；作者交互点挂「镜头/开关」菜单；把 G1/G2 门闩改走 `CapabilityFlags` |
| `(D9 W3 未来)` `web/api/routers/system_config.py` | 待立项 | 复用 `resolve_features`/`save_features`/`switch_protagonist`（本 SDD 定义、文档留契） |

**门闩迁移（本 SDD）**：run_novel 内 G1 `pt_cfg.get("enabled")+trigger==batch` 与 G2 `_evo_enabled/_beat_tags_to_growth` 改为读 `CapabilityFlags.bridging/off_screen_batch/evolution_pacing/beat_tags_to_growth`；其余模块（`bridging.py`/`evolution_pacing.py`/`internet_search.py`）**保持自带默认关 + 传参 gated**，不强迫整体重构 → 船身不破。

---

## 7. 分阶段落地（本 SDD 一次 MVP）

| 阶段 | 内容 | 验收 |
|------|------|------|
| **G3 文档闸** | 本 SDD + SPEC_SDD D12 登记 + next-iteration G3 标注 + WORKLOG 条目 | ✅（2026-08-31） |
| **G3 编码** | `capabilities.py`（外观面+回退 WARN+features.yaml）；`protagonist_switch.py`（运行时镜头+持久化+`effective_protagonist`）；`alt_draft.py`（候选备选稿写/列/提升，dry-run 不立库）；run_novel 迁移门闩 + 作者「镜头/开关/备选稿」菜单 | 12–16 条单测；`features={}` 默认全量回归与 G2 末一致（359 通过 + 1 跳过） |

**验收总纲**：默认（无 `runtime.features`、无覆盖）行为逐字节等价旧版；开启后单测可断言：`resolve_features` 规范读法命中、features.yaml 覆盖生效、旧深层位置命中触发 WARN、`switch_protagonist` 校验+替换+持久化、`effective_protagonist` override 优先；备选稿写/列/提升：dry-run 不触发成长/事件立库（发电机与演进解耦），提升替稿切镜头。全程无 LLM。

---

## 8. 不做（留后续）

- D9 Web `/system` 落地（W3 立项）。
- 多主角并列叙事/每角色独立**导出成文树**（G3 仍**单导出镜头**：演进层所有关键角色独立，但正篇成文每时刻只有一条；**备选稿只按作者显式请求单章生成**、提升后即替稿并切镜头，不并行维护多条完整正文）。
- 整树重导出历史（备选稿是**单章、作者显式**的替稿例外；默认切换镜头是**前向**的；整长效重做成型 ≠ 本 SDD）。
- 把全部深层 `.get(...)` 一次性删净（尽力迁移；余下走回退 WARN 兼容）。
- 联动龙脉/收益倍率等「用户可调」数值面（本次只布尔能力开关 + 镜头 + 备选稿）。

---

## 9. 关联文档

- [evolution-pacing-coupling.md](./evolution-pacing-coupling.md)：G2（成长站姿前馈 + 节拍标签反馈）——其 `runtime.evolution_pacing.*` 开关被本 SDD 收进 `runtime.features`。
- [parallel-thread-bridging.md](./parallel-thread-bridging.md)：G1（屏外演进 + 桥接）——`runtime.parallel_threads` 开关收敛。
- [protagonist 主角解析](./protagonist.py)：被 `effective_protagonist` 复用，不改。
- [novel-reader-ui.md](../design/novel-reader-ui.md)：**D9** `/system` §5.6/§8.7（W3 可写）——本 SDD 定义其复用的表面契约。
- [SPEC_SDD.md](../framework/SPEC_SDD.md)：**D12**。
- [`docs/planning/next-iteration.md`](../planning/next-iteration.md)：G3 项。

---

## 10. 修订记录

- **2026-08-31**：G3 SDD 初稿；登记 **D12**；与 next-iteration G3 项挂链；与 G1/G2/D9 互链。