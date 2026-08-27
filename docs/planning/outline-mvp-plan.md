# 大纲 MVP 执行方案（MVP-0 / MVP-1 / MVP-2）

本文在 **[outline-and-beats.md](../design/outline-and-beats.md)** 原则不变的前提下，将「分阶段落地」**细化成可实现的范围、验收与代码接入点**。架构蓝图仍以大纲设计文档为准；本文件只约束 **MVP 三阶段** 的**边界与交付**。

---

## 1. 原则回顾（约束 MVP 不做的事）

- **节拍不是硬状态机**：完成某节拍、换章以 **作者在环** 为主；系统只给 **软提示**（如「本节拍已 N 回合，建议 ≤3」）。
- **正文主轴**：叙述以 **主角** 为锚；非主角仅在 **在场 / 桥接摘要** 需要时展开（与现有 Agent prompt 一致，MVP-1 用配置 **显式化主角 id**）。
- **无大纲文件**：行为与当前版本一致（**零侵入**）；不因缺大纲报错。

---

## 2. 单一真相（SSOT）：`outline.yaml` 与设定「章节大纲」

| 来源 | 位置 | MVP 阶段 |
|------|------|----------|
| **运行时大纲（主）** | `<data_root>/book/outline/outline.yaml` + 可选 `progress.yaml` | MVP-0 已加载；MVP-1/2 **只认此树** 注入写作管线 |
| **设定阶段归纳** | `<novel>/config/setting_research_output.yaml` 顶层 **`章节大纲`** | 可与 `outline.yaml` **不一致**；MVP 要求通过 **一次性流程** 对齐，避免双源长期漂移 |

**推荐约定（MVP-1 可一起做 MVP-1b）**

1. **首次有 `章节大纲`、尚无 `outline.yaml`**：提供 **单向生成**（脚本或设定满意后一步）：把 `chapters[].{chapter_number,title,summary}` **映射**为 `outline.yaml` 的 `chapters[].{id,title,dramatic_question?,beats[]}`（无节拍时自动生成 **单节拍占位**，`intent = summary`）。  
2. **此后**：以 **`book/outline/outline.yaml` 为 SSOT**；若要改结构，作者改 YAML 或在设定里讨论后再执行一次「从设定刷新大纲」（覆盖或合并策略需在交互里二选一，MVP 可先 **覆盖初版 + 手改**）。  
3. **不在每一回合自动双向同步** 两个文件。

---

## 3. MVP-0（已完成）

**目标**：能 **加载**、**轻量校验**、**可观测**，且不强迫用户建大纲。

| 项 | 状态 | 说明 |
|----|------|------|
| Schema 与示例 | ✅ | `docs/examples/outline.yaml`、`progress` 字段见 `outline_store.validate_*` |
| 加载入口 | ✅ | `src/runtime/outline_store.py`：`load_outline_snapshot(data_root)` → `OutlineSnapshot \| None` |
| 主流程日志 | ✅ | `run_novel_with_author`：存在大纲时 `[大纲]` INFO 一行（`OutlineSnapshot.log_line()`） |
| 无文件 | ✅ | `load_outline_snapshot` 返回 `None`，主流程跳过 |

**验收（回归）**：无 `outline.yaml` 时全量单测与主流程行为与改前一致；有示例文件时能加载且日志含章数/进度摘要。

---

## 4. MVP-1（下一步开发）

**目标**：写作前分析与正文生成 **感知当前章/节拍与主角**，并与大纲 **`intent` / `dramatic_question` / 软提示** 对齐。

### 4.1 配置（必须先定稿）

在 **`runtime` 合并结果**中解析（具体键名实现时二选一，**文档以先实现者为准**）：

- **主角**：`runtime.novel_run.protagonist_id: <str>` **或** `characters.yaml` 中某一角色 `is_protagonist: true`（**全仓仅一个**）；须与 `agents.characters.enabled_ids` 兼容，启动或编排器初始化时 **校验**，失败则 **ERROR + 退出** 或 **降级仅 WARN**（实现时选一种，建议 **WARN + 正文不注入主角轴** 以免打断旧项目）。
- **大纲开关（可选）**：`runtime.outline.enabled` 默认 true；`soft_max_turns_per_beat` 默认 **3**（仅写进 prompt 文案，不强制截断）。

### 4.2 `outline_store` 扩展（建议 API）

在 **`outline_store.py`** 增加（命名可微调，职责如下）：

1. **`resolve_current_beat(snapshot: OutlineSnapshot) -> BeatContext | None`**  
   - 输入：`progress` 中的 `chapter_id`、`beat_id`（缺省时 **MVP-1 可约定**：取第一章第一个 `planned/active` 节拍，或返回 `None` 仅不打大纲块）。  
   - 输出（dataclass 或 dict）：`chapter_title`、`dramatic_question`、`beat_id`、`beat_intent`、`suggested_scope_id`、`tags`、`turns_in_beat`、`soft_max_turns`、`next_beat_hint`（可选一行）、`protagonist_label`（来自配置，供 prompt 引用）。

2. **`format_outline_snippet_for_prompt(ctx: BeatContext | None, *, protagonist_id: str | None) -> str`**  
   - 拼 **固定护栏**：单节拍建议回合数、「以主角为主线」一句；无 `ctx` 时返回空串。

### 4.3 `turn_planning` 接入

- **`build_turn_plan_prompt`**：末尾或独立一节注入 **`【全书大纲·当前节拍】`**（来自 `format_outline_snippet_for_prompt`），要求分析中的「本段目标」与 **`beat_intent` 一致或可解释偏离**。  
- **`generate_turn_plan_for_turn`**：签名增加可选参数 **`outline_snapshot: OutlineSnapshot | None`**、**`protagonist_id: str | None`**（或由 `runtime_config` 内读）；内部构造 `BeatContext` 再调 `build_turn_plan_prompt`。  
- **`build_turn_body_prompt`**：同样注入 **大纲节 + 主角句**，约束正文 **不超过节拍所需、不提前写完下一节拍**（提示语，非硬编码字数）。

### 4.4 主流程接入

- **`run_novel_with_author`**：在已有 `load_outline_snapshot` 处缓存 **`OutlineSnapshot | None`**（或每回合重新加载以支持手改文件）。  
- 调用 **`generate_turn_plan_for_turn`** / 后续 **`generate_turn_body`** 时传入 **大纲快照 + 主角 id**。  
- **Orchestrator / TurnContext**：MVP-1 **可不改** Storage；若已有 `project_root`/`data_root`，只读大纲即可。

### 4.5 MVP-1b（可选，与同版本并行）

- **从设定 `章节大纲` 生成首版 `outline.yaml`**：映射规则见 §2；实现为 `src/runtime/outline_store.py` 中 **`extract_chapter_outline_from_setting`**、**`outline_dict_from_setting_chapter_outline`**、**`materialize_outline_from_setting_research(data_root, setting_research, overwrite=..., write_initial_progress=...)`**（写入 `<data_root>/book/outline/outline.yaml`，可选首章首节拍的 `progress.yaml`）。生成后请作者手查 `beats`。  
- **单元测试**：`tests/unit/test_outline_store.py` 含映射与落盘加载；`resolve_current_beat` golden case 见同文件既有用例。

### MVP-1 验收清单

- [x] 配置中存在合法 `protagonist_id`（或唯一 `is_protagonist`）时，**写作前分析 / 正文 prompt** 中出现 **主角约束** 与 **当前节拍 intent**（`build_outline_prompt_snippet` + `turn_planning` 已接入；`run_novel_with_author` 每回合传 `outline_snippet`）。  
- [x] 存在 `outline.yaml` + `progress.yaml` 时，`turns_in_beat` 与 **软上限** 出现在提示中；回合开始 **INFO** `[大纲进度]`。  
- [x] 无大纲或 `runtime.outline.enabled: false` 时，不注入大纲块（行为与 MVP-0 一致）。  
- [x] （MVP-1b）从 `章节大纲` 生成的 `outline.yaml` 可被 `load_outline_snapshot` 加载；`validate_outline` 仅提示性（见 `materialize_outline_from_setting_research`）。

---

## 5. MVP-2（接续 MVP-1）

**目标**：作者在写稿循环中能 **看见进度**，并在 **确认写回** 后 **持久化进度**（重启可读）；**不**在 MVP-2 强制自动改写 `outline.yaml` 里大面积 YAML 树（降低合并冲突与误删风险）。

### 5.1 CLI / 交互（建议）

- **每回合开始**（或进入阶段一前）：**INFO** 再打一行紧凑进度，例如  
  `[大纲进度] chapter=ch01 beat=ch01_b2 turns_in_beat=2/3`。  
- **阶段一作者确认正文后**（或整回合结束前）：询问是否 **「本节拍已够 / 进入下一节拍」**（y/n）；或子菜单：**仅增加 `turns_in_beat` / 前进到下一 `beat_id` / 跳过（手改 YAML）**。  
- **默认安全路径**：只更新 **`progress.yaml`**（`chapter_id`、`beat_id`、`turns_in_beat`、`last_updated`）；必要时更新当前节拍 `status: active → done` **若** 选择「前进」，则下一节拍 `planned → active` 的更新 **优先只写在 progress 里**（`beat_id` 指针迁移）；**全量回写 outline.yaml** 留作 **Phase 2** 或手工编辑。

### 5.2 写回规则（建议）

- **`progress.yaml`**：`version`、`chapter_id`、`beat_id`、`turns_in_beat`、可选 `updated_at`。  
- **与文件锁**：单进程 CLI 可无锁；若未来 Web 并发再引入锁。

### MVP-2 验收清单

- [ ] 重启后 `load_outline_snapshot` 读到 **上一轮写入的 progress**。  
- [ ] `resolve_current_beat` 在同一文件下与作者选择的节拍 **一致**。  
- [ ] 作者在环 **明确操作** 才推进节拍（无静默自动跳章）。

---

## 6. MVP 之后（本文件不展开实现）

| 阶段 | 内容 | 见 |
|------|------|-----|
| Phase 2 | 设定/LLM 辅助生成大纲初稿、节拍级精修 | `docs/design/outline-and-beats.md` §8 |
| Phase 3 | 屏外记忆类型、桥接摘要触发、副轨低成本更新 | 同左 |
| Phase 4 | 单角色同文导出 | 同左 §6 |

---

## 7. 修订记录

- **2026-03-29**：初稿；统一 MVP-0/1/2 范围、SSOT、`outline_store`/`turn_planning`/主流程接入点、MVP-2 进度写回策略；与 `docs/planning/next-iteration.md`、`WORKLOG.md` 互链。
