# 记忆分类、存储与检索方案

本文档约定**小说主体内容**与**各类记忆**的目录存储、Markdown 文件格式及**基于渐进式目录的检索**方案，使大模型可依托目录结构按需查找记忆，**无需向量数据库**。与 [TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md) §7、[DESIGN.md](../../DESIGN.md) §4～6 对齐。

**组装后上下文压缩**（检索结果已拼入提示词、需逼近预算上限时的 **任务锚定压缩**，与 `retrieve_for_intent` 内字符截断衔接）见专题 SDD **[context-compression-adaptive-layered.md](./context-compression-adaptive-layered.md)（登记表 D8）**。

---

## 一、目标与原则

| 目标 | 说明 |
|------|------|
| **小说主体按回合存储** | 正文/叙述按回合落盘，便于按回合回放、版本与审阅。 |
| **记忆统一用 Markdown** | 各类记忆以 `.md` 存于文件系统，人类可读、可编辑、可版本管理。 |
| **按记忆类型分子目录** | 角色记忆、范围事件、次要角色、设定等各占子目录，边界清晰。 |
| **渐进式目录（类 Skills）** | 每层目录通过 `README.md` 或索引文件描述「本层有什么、如何往下找」，大模型可**先看目录再选文件**，按路径查找对应记忆，而不必全量加载或依赖向量检索。 |
| **免向量库检索** | 通过「目录即索引」+ 按需读文件实现检索，降低依赖与复杂度；若后续需要语义检索可再叠加向量层。 |

---

## 二、记忆分类

与 DESIGN §4、§5 及 TECH_IMPLEMENTATION §7.2 一致，记忆与内容分为以下类别。

### 2.1 小说主体内容

- **定义**：每回合产出的叙述正文（作者在环审阅后的最终正文）与其对应摘要的持久化。
- **用途**：按回合回放、成书导出、审阅与修改；**检索到摘要时能直接回看对应正文**。
- **归属**：全局共享，按回合组织；**正文的单一数据源为「范围事件簿」中的事件条目（scope events）**，避免多处存储导致不一致。

### 2.2 角色记忆（每角色独立）

| 子类 | 说明 | 检索需求 |
|------|------|----------|
| **profile** | 人物设定（姓名、背景、性格、目标等）；须与总设定一致。 | 按 character_id 取一份，体量小可全量注入。 |
| **relations** | 社交关系（与谁、关系类型、亲疏变化）。 | 按 character_id 取，可限条数或按 target 过滤。 |
| **events** | 该角色所知事件的提炼/摘要（按时间线或范围）。 | 按 character_id + 最近 N 条或按 turn/scope 取。 |
| **emotions** | 对某人某事的情感变化。 | 按 character_id、可选 target_id、最近 N 条。 |

每类可单独子目录、单独文件或按回合分文件，便于「只读最近事件」等检索。

### 2.3 范围记忆（每范围独立）

| 子类 | 说明 | 检索需求 |
|------|------|----------|
| **events** | 本范围事件簿（时间、地点、参与角色、结果）。 | 按 scope_id + 最近 k 条。 |
| **state** | 本范围当前状态快照（势力、地点、局部规则等）。 | 按 scope_id 取一份。 |

### 2.4 次要角色列表

- **定义**：小说中非配置关键角色的动态列表（如村长、猎户），供 ScopeAgent/CharacterAgent 查阅。
- **检索**：按 scope_id 过滤、限条数。

### 2.5 设定（世界共享基础规则）

- **定义**：战力体系、境界体系、世界规则等（来自设定研究或编辑）。见 DESIGN §6.5。
- **检索**：按主题/类型取摘要或片段，**不得**每回合全量注入（见 DESIGN §6.5、[llm-and-agents.md](./llm-and-agents.md) 上下文约定）。

### 2.6 外网知识缓存（可选）

- **定义**：由受控联网工具（如 Playwright 路线或等价搜索工具）抓取并摘要后的参考知识片段。  
- **用途**：服务套路研究、背景核对、题材常识补充；作为“检索候选”参与 PromptAssembler，而非直接覆写正文。  
- **最小元数据**：`source_url`、`fetched_at`、`trust_level`、`topic_tags`、`summary`、`evidence_snippets`。  
- **约束**：仅保存必要摘要与证据片段，避免原文大段落盘；受配额、超时与来源策略控制。

---

## 三、存储布局（根目录约定）

建议在项目或运行根下设**统一数据根**（如 `data/` 或 `novel_data/`）。**当前实现**：其下以 **book/** 为一级目录，小说相关输出统一落盘于 book 下四个二级目录：**content（内容）、setting（设定）、characters（人物）、events（事件）**；配置文件仅保留最关键信息（路径、摘要），具体内容以 MD 存储。

### 3.1 当前实现：data_root/book/ 布局（正文单一数据源）

由 `runtime.storage.data_root` 指定数据根后，双写路径为：

```
<data_root>/
├── .turn_counter                # 回合计数器（与 book 共用）
└── book/                        # 一级目录：小说相关输出
    ├── README.md                # 总索引：content / setting / characters / events
    ├── content/                 # 内容：可选派生视图（不作为正文单一数据源）
    │   ├── README.md
    │   └── turns/               #（当前实现可能存在旧产物；如需可由 events 派生生成）
    │       └── ...
    ├── setting/                 # 设定：设计会话 MD、各方向设定 MD（境界/战力等）
    │   ├── README.md
    │   ├── session_<timestamp>.md   # 设定会话完整内容（配置中仅存路径与摘要）
    │   ├── level_system.md      # 境界体系等，按 key 命名
    │   └── ...
    ├── characters/              # 人物：角色记忆（每角色一目录）
    │   ├── README.md
    │   ├── <character_id>/
    │   │   ├── events/
    │   │   │   ├── turn_0001.md
    │   │   │   └── ...
    │   │   └── ...
    │   └── ...
    └── events/                  # 事件：范围事件与状态（原 memory/scopes）
        ├── README.md
        ├── <scope_id>/
        │   ├── events/
        │   │   ├── turn_0001.md
        │   │   └── ...
        │   └── state.md
        └── ...
    └── knowledge/               # 可选：外网知识缓存（受控检索产物）
        ├── README.md
        └── internet_cache/
            ├── README.md
            └── entries.md
    └── memory/                  # 作者在环补充记忆（与 events 正文数据源分离）
        └── author_classified/   # LLM 归类 + 按子目录持久化；写作前分析渐进式检索注入
            ├── README.md
            ├── setting/entries.md
            ├── character/entries.md
            ├── constraints/entries.md
            ├── narrative/entries.md
            └── meta/entries.md
```

实现见 `src/author_loop/author_classified_memory.py`：作者自由输入 → `classify_author_input` → `append_classified_entries`；`progressive_author_memory_for_plan` 先拼各类 `entries.md` 尾部索引，再经 LLM 输出 `ordered_categories`，最后按序加载片段注入 `generate_turn_plan_for_turn`。

**动态分类**：分类列表由 `runtime.author_classified_memory` 配置（见 `config/novel_writing.yaml` 注释示例；与 `system_config`、`example_runtime` 合并加载）。`include_defaults: true`（默认）时在内置 5 类基础上追加小说类型专用维度（如 `romance`、`mystery_clues`）；`include_defaults: false` 时可完全自定义 id（须符合 `^[a-z][a-z0-9_]{0,63}$`）。`fallback_id` 用于无法识别或 Dummy LLM 时的兜底目录，且必须在最终 id 列表中。

- **config/design_session.yaml**：仅保存 version、last_updated、theme、genre、**session_file**（如 `book/setting/session_20260218_130204.md`）、**summary**；完整会话内容在 session_*.md。
- **config/setting_research_output.yaml**：仍保存完整 YAML 供程序加载；各方向同时写入 **book/setting/<key>.md** 便于查阅与检索。

**关于“正文单一数据源”的约定（与最新代码一致）**

- **正文仅存一处**：每回合正文存放于 `book/events/<scope_id>/events/turn_NNNN.md` 的 `## 正文` 段（同一条事件同时含 `## 摘要`）。程序运行时也仅以 scope events（`storage.get_recent_events(scope_id)` 返回的事件条目中的 `body` 字段）作为正文来源。
- **展示/检索**：需要展示正文时，从事件条目取 `body`（如 `src/retrieval/memory.get_turn_body_from_storage`）；需要注入 prompt 的“最近事件”仍优先使用 `summary`（如 `format_scope_events_snippet`），避免上下文过长。
- **避免不一致**：不再把正文同时写入多处路径；如需要导出“按回合的全局正文”，建议以 events 为源生成（离线导出或另一个同步步骤），而不是运行时双写正文。

### 3.2 原推荐结构（渐进式 memory 细化参考）

以下为细化角色/范围子目录时的参考；当前双写已统一到 book/ 下 content、setting、characters、events。

```
<data_root>/
├── README.md                    # 总索引：说明 content/ 与 memory/ 的用途及如何查找
├── content/                     # 小说主体内容
│   ├── README.md                # 说明：按回合存储，每文件为一回合叙述
│   └── turns/
│       ├── README.md            # 列出 turn_0001.md, turn_0002.md, ...（按回合顺序）
│       ├── turn_0001.md
│       ├── turn_0002.md
│       └── ...
│
└── memory/                      # 所有记忆（按类型分子目录）
    ├── README.md                # 索引：characters / scopes / secondary_characters / setting
    │
    ├── characters/              # 角色记忆（每角色一目录）
    │   ├── README.md            # 列出所有角色目录：张凡, 李墨, 王石头, ...
    │   ├── 张凡/
    │   │   ├── README.md        # 本角色索引：profile, relations, events, emotions
    │   │   ├── profile.md
    │   │   ├── relations.md
    │   │   ├── events/
    │   │   │   ├── README.md    # 按回合列出：turn_0001.md, turn_0002.md, ...
    │   │   │   ├── turn_0001.md
    │   │   │   └── ...
    │   │   └── emotions/
    │   │       ├── README.md    # 可选：按对象或时间列出
    │   │       └── *.md
    │   ├── 李墨/
    │   │   └── ...
    │   └── ...
    │
    ├── scopes/                  # 范围事件与状态（每范围一目录）
    │   ├── README.md            # 列出所有范围目录：怪物来袭, 村庄, ...
    │   ├── 怪物来袭/
    │   │   ├── README.md        # events/, state.md
    │   │   ├── events/
    │   │   │   ├── README.md    # 按回合：turn_0001.md, turn_0002.md, ...
    │   │   │   ├── turn_0001.md
    │   │   │   └── ...
    │   │   └── state.md
    │   ├── 村庄/
    │   │   └── ...
    │   └── ...
    │
    ├── secondary_characters/    # 次要角色列表
    │   ├── README.md            # 说明：entries.md 或按 scope 子目录
    │   └── entries.md           # 或 by_scope/怪物来袭.md, by_scope/村庄.md
    │
    └── setting/                 # 世界共享设定（来自设定研究或编辑）
        ├── README.md            # 索引：power_system, level_system, world_rules, ...
        ├── power_system.md
        ├── level_system.md
        └── world_rules.md       # 可选
```

### 3.1 小说主体：按回合存储

- **路径**：`content/turns/turn_NNNN.md`（如 `turn_0001.md`）。
- **内容**：本回合的叙述正文（可含 YAML frontmatter：`scope_id`、`time`、`place`、`turn_id`、`character_ids` 等）。
- **约定**：每回合写一个文件；如需按范围分目录，可为 `content/turns/<scope_id>/turn_NNNN.md`，由 `content/turns/README.md` 说明规则。

### 3.2 角色记忆：按类型与回合

- **profile**：单文件 `memory/characters/<character_id>/profile.md`，整份可读。
- **relations**：单文件 `relations.md` 或按对象分文件；更新时追加或覆盖，由 README 说明格式。
- **events**：目录 `events/`，按回合分文件 `turn_0001.md`, `turn_0002.md`；`events/README.md` 列出「最近 N 个回合文件名」，便于检索时只读最近若干文件。
- **emotions**：目录 `emotions/`，可按对象或时间分文件，README 列出索引。

### 3.3 范围记忆：按范围与回合

- **events**：`memory/scopes/<scope_id>/events/turn_NNNN.md`，每回合追加一个文件；`events/README.md` 列出回合列表。
- **state**：单文件 `memory/scopes/<scope_id>/state.md`，每回合或关键变更时覆盖/更新。

### 3.4 渐进式目录的 README 约定

- 每个 **README.md** 建议包含：
  - **本层含义**（一两句话）；
  - **子项列表**（子目录或文件名的清单，按时间或字母序）；
  - **如何用**（例如：「查某角色最近 5 回合事件 → 进 events/ 读 README，再按列表读最近 5 个 turn_*.md」）。
- 大模型检索流程：先读 `memory/README.md` → 确定类型（如 characters）→ 读 `memory/characters/README.md` 选角色 → 读 `memory/characters/张凡/README.md` 选子类（如 events）→ 读 `events/README.md` 选回合文件 → 只读需要的若干文件，避免全量加载。

---

## 四、Markdown 文件格式建议

- **小说回合** `content/turns/turn_NNNN.md`：可选 YAML frontmatter + 正文；正文为叙述内容。
- **profile.md**：可选 frontmatter（如 character_id, updated_at）；正文为键值或短段落（姓名、背景、性格等）。
- **relations.md** / **events/*.md** / **emotions/*.md**：每条记忆可为一节（`## 条目标题`）或列表项，内容为结构化摘要或自由文本；若需机器解析可内嵌 YAML 块或约定表格。
- **state.md**：当前范围状态，键值或短段落。
- **setting/*.md**：设定研究产出的战力/境界等，可为结构化标题 + 段落，便于人工维护与检索摘要。

具体字段名与层级可与现有 `MemoryStorage` 的键结构（TECH_IMPLEMENTATION §7.2）一一对应，便于实现「内存 Storage ↔ 文件目录」的双写或迁移。

---

## 五、检索方案（基于目录、免向量库）

### 5.1 检索流程（大模型或程序）

1. **确定检索目标**：例如「角色 张凡 最近 5 条事件」「范围 怪物来袭 最近 10 条事件」「当前范围状态」。
2. **沿目录定位**：从 `memory/README.md` 或 `content/README.md` 进入对应类型 → 读该类型 README 得子项列表 → 进入目标实体（角色/范围）→ 读该实体 README 得子类（events/state/…）→ 若为列表类（events），读子类 README 得回合文件列表。
3. **按需读取文件**：只打开需要的 N 个文件（如最近 5 个 turn_*.md），拼成片段注入 prompt；不读整库。
4. **限长与摘要**：单文件或拼接后若超长，由程序做截断或摘要（与现有 `retrieve_character_memory(limit=…)`、`format_scope_events_snippet(k=…)` 一致）；设定类用「设定检索」只取相关段落（DESIGN §6.5）。

### 5.2 与现有 retrieval 模块的对应

| 现有接口 | 文件侧等价行为 |
|----------|----------------|
| `retrieve_character_memory(storage, character_id, events_limit, relations_limit)` | 读 `memory/characters/<id>/profile.md` + `relations.md`（限条）+ `events/` 下最近 events_limit 个 turn_*.md |
| `format_scope_events_snippet(storage, scope_id, k)` | 读 `memory/scopes/<scope_id>/events/` 下最近 k 个 turn_*.md 并拼接摘要 |
| 范围 state | 读 `memory/scopes/<scope_id>/state.md` |
| 次要角色 | 读 `memory/secondary_characters/entries.md` 或按 scope 子文件 |
| 设定片段 | 读 `memory/setting/README.md` 选文件，再读 `power_system.md` / `level_system.md` 的摘要或相关段落 |
| 外网知识缓存（可选） | 读 `book/knowledge/internet_cache/entries.md`，按 tag/trust/source 过滤后注入摘要 |

**R7c（正篇阶段一审阅、意图 `review_revise`）**：`retrieve_for_intent` 对**运行时** `Storage` 调用 **`format_scope_events_snippet(storage, scope_id, k)`**（与上表「范围事件摘要」同源），并与 **`author_interaction_state` digest** 拼入检索片段；与 **渐进式 author_classified** 并列属不同工具链，见 [author-agent-harness.md §6.3](./author-agent-harness.md)。主循环将片段注入修订 Handler（**R7d**）后，本条与 S2 §3.4 SHOULD 对齐。

实现时可在 `src/retrieval/` 下增加「文件存储适配」：给定 data_root，按上述路径规则读 MD 文件，返回与现有接口相同格式的字符串或结构，供 Agent 与编排器复用。

### 5.3 索引文件的维护

- **README.md**：在**写入记忆或新回合时**由程序更新（如追加一行新 turn 文件名、更新「最近 N 个」列表）；或由定时/回合结束任务批量生成。
- 若目录较多，可只保证「当前活跃角色/范围」的 README 为最新，其余按需再生成，以控制写放大。

---

## 六、与现有实现的关系

- **当前**：`src/runtime/storage.py` 的 `MemoryStorage` 为内存实现，键结构符合 §7.2；`src/retrieval/` 从该 Storage 读数据并格式化为 prompt 片段。
- **本方案**：约定**持久化形态**为目录 + MD；可与现有实现并存：
  - **方案 A**：新增 `FileStorage` 或 `MarkdownStorage`，实现与 `MemoryStorage` 相同的接口（get_profile、append_events、…），内部按本节路径读写 MD 与 README；编排器与 retrieval 仅依赖 Storage 抽象，可切换为 FileStorage。
  - **方案 B**：保持 MemoryStorage 为运行时主存储，每回合结束或定时将内存状态**同步到**文件目录（双写），文件侧专供「按目录检索」与人类审阅；检索仍可从 MemoryStorage 读，或增加「从文件目录读」的检索分支。
- **小说主体**：当前若未落盘，可在编排器写回回合结果时增加「写入 content/turns/turn_NNNN.md」的逻辑，与现有事件簿/记忆写回并列。

---

## 七、小结

| 项 | 约定 |
|----|------|
| 小说主体 | 按回合存于 `content/turns/turn_NNNN.md`，可带 frontmatter。 |
| 记忆分类 | 角色（profile/relations/events/emotions）、范围（events/state）、次要角色、设定；每类单独子目录。 |
| 存储格式 | 全部 Markdown；每层目录配 README 作索引。 |
| 渐进式目录 | 大模型（或程序）通过 README 逐层定位，只读需要的文件，避免全量与向量库。 |
| 检索 | 与现有 retrieval 接口对应；可新增文件侧适配器或双写，保持限长与摘要约定（DESIGN §6.5）。 |

实现时优先保证「目录与 README 的生成与更新」「按路径读 MD 并拼成检索结果」，再视需要将现有 MemoryStorage 与文件存储打通或切换。
