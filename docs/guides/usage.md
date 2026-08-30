# 小说主程序使用说明

本文说明如何配置并运行小说主程序（`run_novel.py` / `run_novel_with_author.py`）。与 [TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md)、[design/llm-and-agents.md](../design/llm-and-agents.md) 一致。

---

## 一、是否可以开始执行

**可以。** 主程序已具备完整流程：加载配置 → 创建编排器与 Agent → 多回合执行 → 写回事件簿/状态与角色记忆。角色与范围 Agent **已接入 LLM**（`turn()` 内拼 prompt、调用、解析输出）；默认 LLM 为 **dummy**（不调用任何 API），运行后产出的是占位文案；接入真实 LLM 后（见下文「可选：使用真实 LLM」）可得到模型生成内容。

---

## 二、执行前需要配置的内容

### 2.1 配置文件与路径

程序从 **`config/`** 目录读取世界/角色与运行时配置；**运行时**由两部分合并（后者覆盖同名键）：

| 文件 | 用途 |
|------|------|
| **system_config.yaml**（可选但仓库已提供） | **系统级**：`framework`（LLM）、`debug`、`dev_agent` 等，与具体小说无关。 |
| **example_runtime.yaml**（可选） | **本书入口**：`runtime.novel_run`（开局）、`agents`（启用的角色/范围 ID）。**缺失时**使用代码内 `DEFAULT_RUNTIME_NOVEL`（占位 id：`main` / `protagonist`）；绑定小说目录后以 `data/novels/<slug>/config/runtime.yaml` 为准。 |
| **novel_writing.yaml**（可选但推荐） | **小说写作基础**（合并入 `runtime`）：世界协调者、设定研究、回合制、作者在环、正文字数、`storage`、`author_classified_memory` 等。 |
| **example_world.yaml** | 世界设定：范围列表（scopes）、时间起点、地点等 |
| **example_characters.yaml** | 角色设定：**仅关键角色**（id、name、traits、goals 等），即拥有独立 CharacterAgent 的主角/主要配角。 |

缺少 **example_world.yaml / example_characters.yaml** 会报错（未绑定 `current_novel` 时）。**example_runtime.yaml** 可省略（使用内置默认入口）。缺少 **system_config.yaml** 时仅使用小说向合并结果（建议在 system_config 中配置 `framework`）。

**关键角色与次要角色**：配置中只需列出**关键角色**（会参与回合演进的少数主角/核心配角）。小说中出现的其他角色（如村长、猎户、路人等）不必在配置里一一列出，可由剧情动态产生并写入存储的「次要角色列表」；编排器每回合会从存储中取出该列表并格式化为 `TurnContext.secondary_characters_snippet`，供 ScopeAgent / CharacterAgent 查阅。写入方式：在接 LLM 后由 Agent 或写回逻辑在引入新配角时调用 `storage.append_secondary_character({"name": "村长", "brief": "青石村村长，五十余岁", "scope_id": "村庄"})` 等；设定阶段或开局时也可预填。

### 2.2 必须一致的配置项

- **runtime.agents.characters.enabled_ids**（在 example_runtime.yaml 的 `agents.characters.enabled_ids`）  
  必须是 **example_characters.yaml** 里 `characters[].id` 的子集；否则 `validate_runtime_and_ids` 会报错：「存在未定义角色 id」。

- **runtime.agents.scopes.enabled_ids**（在 example_runtime.yaml 的 `agents.scopes.enabled_ids`）  
  必须是 **example_world.yaml** 里 `scopes[].id` 的子集；否则报错：「存在未定义范围 id」。

- **开局场景**：`runtime.novel_run.initial_scope_id` 必须是已启用的范围 ID（即在 `agents.scopes.enabled_ids` 中）；若不填，则取 `enabled_ids` 的第一个。

示例（与仓库内示例一致）：
- `enabled_ids: [a, b]` → characters 中需有 `id: a` 和 `id: b`。
- `enabled_ids: [capital, jianghu]` → scopes 中需有 `id: capital` 和 `id: jianghu`。
- `initial_scope_id: capital` → 开局在「京城·朝堂」范围。

### 2.3 开局场景（可选但建议填写）

在 **example_runtime.yaml** 的 `runtime.novel_run` 下：

```yaml
runtime:
  novel_run:
    initial_scope_id: capital   # 开局范围（须在 agents.scopes.enabled_ids 内）
    initial_time: "永和十年春"  # 不填则用 example_world.yaml 的 time.start
    initial_place: "京城"       # 不填则 "（未设定）"
```

### 2.4 可选：使用真实 LLM

若希望角色/范围 Agent 调用真实大模型（Agent `turn()` 已接 LLM），只需完成 LLM 配置。

**当前默认：火山方舟（Volcengine Ark，OpenAI 兼容端点）**

仓库 `config/system_config.yaml` 已配置 `framework.llm: openai_compatible`，`llm_options` 指向 `https://ark.cn-beijing.volces.com/api/coding/v3`、模型 `deepseek-v4-pro`；只需在**环境变量**（或项目根 `.env`）中设置 **`DASHSCOPE_API_KEY`** 即可。

**通义千问（阿里云 DashScope）**

1. 在 **system_config.yaml** 的 `framework` 中设置 **`llm: tongyi`**（或 `qwen-plus`），可选在 `llm_options` 中改 `model`（如 `qwen-plus`）、`base_url`（默认 DashScope 兼容端点）。
2. 在**环境变量**中设置 **`DASHSCOPE_API_KEY`**（阿里云百炼 / DashScope 控制台获取）。

**其他：OpenAI 或国内代理**

- `llm: openai`（或 `openai_compatible`），`llm_options` 中设 `model`、`api_key_env`（默认 `OPENAI_API_KEY`），国内代理时设 `base_url`。
- 环境变量中设置对应 API Key。

当前主流程在配置真实 LLM 后，回合内角色/范围 Agent 与写作前分析/正文生成等环节会调用该 LLM。详见 [design/llm-and-agents.md](../design/llm-and-agents.md)。

---

## 三、运行方式

### 3.1 环境与依赖

- **Python**：建议 3.10+。
- **依赖**：在项目根目录执行 `pip install -r requirements.txt`（含 PyYAML、pytest、openai 等）。

### 3.2 自动跑多回合（不打断）

```bash
# 在项目根目录（Linux）
python3 run_novel.py
# 或（虚拟环境）
.venv/bin/python run_novel.py
```

- 默认执行 **2 回合**；每回合自动写回事件簿与范围状态，**不写**角色记忆（记忆写回留作者确认，见下一节）。
- 可通过环境变量 **MIN_AUTOBOOK_TURNS** 指定回合数（1～100），例如：
  ```bash
  export MIN_AUTOBOOK_TURNS=3
  python3 run_novel.py
  ```

**日志**：主程序使用 `logging`，**同时输出到控制台与日志文件**。日志统一写入**日志文件夹** **`logs/`**（项目根下，自动创建）；日志文件**默认按日期命名**：**`logs/min_autobook_YYYY-MM-DD.log`**，便于多次运行分文件查看。可通过 **MIN_AUTOBOOK_LOG_DIR** 指定其他日志目录，**MIN_AUTOBOOK_LOG_FILE** 指定固定文件名（不设则用日期），**MIN_AUTOBOOK_LOG_LEVEL** 指定级别（默认 `INFO`），便于调试。

### 3.3 作者在环（每回合审阅/修改后再写回）

```bash
python run_novel_with_author.py
```

- 每回合先**不写回**，等待作者审阅。
- **阶段一**：审阅本回合结果（优先展示本回合正文；否则展示 scope 事件摘要与角色言行），可选：
  - **直接回复 `y` 或 `没问题`**：表示满意，系统会**生成本回合摘要并将「摘要 + 正文」写入主线事件簿**，然后进入阶段二/下一回合；
  - **直接输入修改意见**（例如“把动作写得更克制一点”）：系统会理解为“针对本回合正文的反馈”，调用大模型**修订正文并再次展示**，直到你回复 `y/没问题` 确认；
  - **e**：先修改再确认（内容写入 `dev_agent/output/author_edits/`，编辑后按提示读回）；
  - **s**：补充设定（在不推翻既有设定的前提下补充完善后，回到本回合审阅）；
  - **n**：驳回，本回合不写回事件/状态，跳过阶段二。
- **阶段二**：审阅角色记忆写回计划，可选 **y** / **e** / **n**；选 y 或 e 确认后写回各角色记忆。
- 同样支持 **MIN_AUTOBOOK_TURNS** 指定回合数。

### 3.4 测试配置的 LLM（简单对话）

在项目根目录运行 **`python test_llm_chat.py`**，会读取合并后的 `framework`（来自 **system_config.yaml** + example_runtime）中的 `llm` 与 `llm_options`，创建对应 Provider 并进入简单对话：输入内容回车发送，输入 `quit` 或 `exit` 退出。用于验证通义/OpenAI/文心等配置与 API Key 是否可用。当前为 DummyLLM 时仅返回占位文案，不会请求网络。

---

## 四、运行结果说明

- **当前（壳 + dummy LLM）**：角色与范围 Agent 输出固定占位文案（如「（壳）暂无内心独白」「（壳）本回合无事件摘要」），事件簿中会看到由这些内容裁决后的摘要。用于验证流程、配置与作者在环是否正常。
- **接入真实 LLM 且 Agent 接 LLM 后**：事件簿与记忆中将出现模型生成的内容（需完成第 13 项）。

程序结束时会打印本轮执行的回合数与当前范围事件簿条数，例如：
`已执行 2 回合，scope=capital，事件簿共 2 条。`

**正文的持久化与展示（单一数据源）**

- 若配置了 `runtime.storage.data_root`（默认示例为 `data`），回合写回后会把该 scope 的事件落盘到 `data/book/events/<scope_id>/events/turn_NNNN.md`，同一文件包含 `## 摘要` 与 `## 正文`。
- 运行时展示正文与后续检索均从“主线事件簿”的事件条目读取正文（`body`），避免正文多处存储产生不一致。

---

## 五、配置项速查

| 配置项 | 文件 | 说明 |
|--------|------|------|
| runtime.novel_run | example_runtime.yaml | 开局 scope_id / time / place |
| agents.characters.enabled_ids | example_runtime.yaml | 启用的角色 ID 列表 |
| agents.scopes.enabled_ids | example_runtime.yaml | 启用的范围 ID 列表 |
| framework.llm | system_config.yaml（合并后） | dummy（默认）或 tongyi / openai 等 |
| framework.llm_options | system_config.yaml（合并后） | model、api_key_env、base_url（可选） |
| debug.* | system_config.yaml | startup / design_phase 等 DEBUG 日志开关 |
| scopes | example_world.yaml | 范围列表，每项含 id、name、description 等 |
| characters | example_characters.yaml | 关键角色列表（仅主角/核心配角），每项含 id、name、traits、goals 等；其余角色可动态写入存储的次要角色列表供 Agent 查阅 |

---

## 六、常见问题

- **配置文件不存在**：确认 `config/example_runtime.yaml`、`config/example_world.yaml`、`config/example_characters.yaml` 存在；建议同时提供 `config/system_config.yaml`（LLM/debug）。路径相对项目根 `config/`。
- **存在未定义角色 id / 范围 id**：检查 runtime 中 `enabled_ids` 的每个值是否在 world 的 `scopes[].id` 或 characters 的 `characters[].id` 中出现。
- **scope_id 未启用或不存在**：`initial_scope_id` 或运行时的 scope_id 必须在 `agents.scopes.enabled_ids` 中，且对应 scope 在 example_world.yaml 中有定义。

更多实现细节见 [TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md)、[WORKLOG.md](../../WORKLOG.md)。
