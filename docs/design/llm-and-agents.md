# LLM 接入与 Agent 框架底层设计方案

本文档针对**第 12 项 LLM 接入**及后续 Agent 框架选型，约定底层设计、国内托管 API 与代理、框架对比与选型建议。与 [TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md)、[WORKLOG.md](../../WORKLOG.md) §三.5 一致；实现前请与产品/开发对齐本方案。

---

## 一、文档定位与本阶段目标

- **阅读对象**：开发、选型决策者；与 Cursor/DevAgent 协同时可作为实现依据。
- **编排决策**：**维持现有自研编排**（`src/orchestrator/`），不引入 LangGraph/AutoGen 等替代；LLM 层**直接使用 OpenAI 官方接口**（`openai` 包）对接调用，不在此阶段引入 LangChain 等框架。
- **本阶段目标（方案 B）**：
  - **LLM 层**：`get_llm_provider(runtime_config)` 能返回可真实调用的 Provider（OpenAI 或兼容端点），`generate(prompt, **kwargs)` 通过 OpenAI Chat Completions API 发起请求并返回字符串。
  - **配置与约定**：明确 `framework.llm`（如 `dummy` | `openai`）、`framework.llm_options`（model、api_key_env、base_url）；API Key 仅从环境变量读取。
  - **本阶段不**：不修改 Character/Scope Agent 的 `turn()` 逻辑（留待第 13 项）；不实现 prompt 设计与输出解析。

**上下文与检索约定**（与 DESIGN §6.5 一致）：设定与各类记忆体量可能很大，Agent 必须**按需检索**（片段/摘要/最近 N 条），不得每回合将全部设定或全部记忆全量注入 prompt，否则会超出上下文上限。实现上沿用并扩展 `retrieve_character_memory`、`format_scope_events_snippet` 等限长接口；设定若注入回合内 prompt，也需提供设定检索（摘要或按主题取用），而非整份 YAML 全量塞入。

---

## 二、托管 API 与国内代理

### 2.1 国内 OpenAI 兼容代理（托管 API，按量计费）

适用于希望使用 GPT/Claude 等模型、且需国内支付或直连的场景。接入方式一般为：**将 API Base URL 改为代理地址，API Key 使用代理平台发放的 Key**。

| 类型 | 代表 | 计费与支付 | 说明 |
|------|------|------------|------|
| 综合代理 | **LLMHub** | 按量计费；微信/支付宝/信用卡；约 2 万 token 免费额度 | 支持 GPT-3.5/4 全系列、Claude 3；国内直连 |
| 综合代理 | **API 易** | 按量计费；约官网八折（约 ¥5.8/美元） | 高并发、快速接入、7×24 客服 |
| 按量代理 | **openai-asia 等** | 如 GPT-3.5-turbo 约 ¥0.028/1k tokens（约官网 2 倍）；支付宝、低起充 | 适合小规模试用 |
| 企业代理 | 部分企业级代理商 | 月消耗分级打折（如 <$10k 约 6 折，>$50k 面议） | 发票、专属客服、稳定性保障 |

**价格粗览（代理层）**：代理通常按「美元消耗」或「按 token 加价」计费；具体以各平台最新定价为准。优势为国内支付、无封号风险由平台承担、改 URL+Key 即可使用。

### 2.2 国内厂商直连 API（托管 API）

直接使用国内大模型厂商的开放 API，按 token 计费，无需代理。

| 厂商 | 代表模型 | 价格量级（参考，以官网为准） | 说明 |
|------|----------|------------------------------|------|
| **阿里云 通义千问** | qwen-turbo / qwen-plus / qwen-max | 输入 ￥2～40/百万 tokens，输出 ￥6～120/百万 tokens；有免费额度 | 性价比常被提及，适合开发与中小规模 |
| **百度 文心一言** | ERNIE-Speed / ERNIE-4.0 | 约 ￥4～120/百万 tokens（视模型） | 按量后付，可扩展 QPS |
| **智谱 AI** | GLM-4 | 约 ￥0.1/千 token（入）、￥0.2/千 token（出） | 需按官网最新价格核对 |
| **百川等** | — | 与通义等有对比测评，可按需查阅 | 多用于对比选型 |

**建议**：若优先「国内直连 + 成本可控」，可先选**通义千问**（qwen-turbo/qwen-plus）或**代理 + OpenAI 兼容**；若需 Claude/GPT-4 能力且接受代理，则选国内代理 + 同一套 OpenAI 兼容接口。

### 2.3 与本程序的关系

- 本程序**底层**通过统一的 `LLMProvider.generate()` 调用，**不绑定**具体厂商。
- 配置层区分「提供商类型」（如 `openai_compatible` / `tongyi` / `wenxin` 等），由对应 Provider 实现里使用各自 SDK 或 HTTP 调用。
- **API Key**：一律不提交进仓库；通过**环境变量**或（可选）本地/运维侧配置文件注入，见 § 五。

---

## 三、Agent 框架选型（含 Flow 类说明）

### 3.1 候选框架概览

本程序当前**已有自研 Orchestrator**（`src/orchestrator/`）：回合内并行调用 Character/Scope Agent，回合结束写回 Storage，不依赖第三方编排框架。选型讨论集中在两类：

- **开发层框架**：LangChain、LangGraph、AutoGen、CrewAI 等，用于**封装 LLM 调用、工具、可选的多 Agent 协作**，可与现有 Orchestrator 并存或部分替代。
- **平台/低代码**：Dify、扣子（Coze）等，偏向可视化编排与托管；与本仓「代码优先、同仓一体」的定位有差异，本节仅作对比参考。

**关于 Flow / iFlow**：检索到的「Flow」多为学术/工业界的**工作流范式**（如模块化 Agent 工作流、信息流编排多 Agent），而非单一可安装的“iFlow”产品名。若你指的是某款具体产品（如某厂商的 Flow 平台），可单独补充产品名与文档链接，再纳入对比。下文将「与现有 Orchestrator 的集成方式」作为选型重点。

### 3.2 开发层框架对比

| 维度 | LangChain | LangGraph | AutoGen | CrewAI |
|------|-----------|-----------|---------|--------|
| **定位** | 组件库与集成层 | 基于 LangChain 的图编排与状态机 | 多智能体对话与协作 | 角色-任务-流程的 AI 团队 |
| **控制力** | 高（需自写流程） | 很高（图、分支、检查点） | 高（多 Agent 消息传递） | 中（自动任务委派） |
| **与本程序 Orchestrator** | 适合做 **LLM 调用层**（不替代编排） | 可做复杂子流程或**替代**编排（代价大） | 多 Agent 协作强，与现有「回合内并行」需对接 | 上手快，定制与深度控制弱 |
| **学习成本** | 中高 | 高 | 中（概念多） | 低 |
| **依赖** | langchain-core + 各厂商适配 | 依赖 LangChain 生态 | 独立生态 | 独立生态 |
| **适用** | LLM 调用、Prompt、RAG、Tool | 复杂有状态工作流、人工节点 | 多专家协作、代码生成 | 角色分工明确的自动化、快速 Demo |

### 3.3 平台类（参考）

| 维度 | Dify | 扣子 Coze |
|------|------|-----------|
| **使用方式** | 低代码/可视化 + API | 零代码/可视化 |
| **私有化/部署** | 支持私有化部署 | 多为托管，不支持私有化 |
| **与本程序** | 可将「单次 LLM 调用」委托给 Dify 工作流，本程序仍负责回合与存储 | 适合快速验证想法，与当前代码仓「底层自控」定位不同 |

### 3.4 选型建议（针对本程序底层）

- **第 12 项（LLM 接入）**：建议**仅引入「LLM 调用层」**，不强制绑定整条 Agent 框架。
  - **优先方案**：在 `src/llm/` 内实现 1～2 个真实 Provider（如 **OpenAI 兼容**、**通义**），通过 HTTP/SDK 直接调用；保留 `LLMProvider` 抽象与 `get_llm_provider(config)`。这样依赖最小、行为清晰，后续若需要再引入 LangChain 作为**可选**封装（例如统一 Tool/RAG）。
  - **可选方案**：若希望与 LangChain 生态统一（Prompt 模板、后续 RAG/Agent 扩展），可增加 **LangChain 版 Provider**：内部使用 `langchain-openai` / `langchain 通义` 等，对外仍实现本仓的 `LLMProvider.generate()`。
- **Orchestrator**：建议**维持现有自研编排**（回合内并行、写回 Storage、作者在环），不在此阶段用 LangGraph/AutoGen 替代；若未来要做「子图/人工审批」等，再评估 LangGraph 与现有 Orchestrator 的融合方式。
- **iFlow/Flow**：若指具体产品，请提供名称与文档，可补充进本文「候选框架」一节并更新选型结论。

---

## 四、底层设计：LLM 层与配置

### 4.1 LLM 层职责（方案 B）

- **编排**：维持自研 Orchestrator；**LLM 调用**：直接使用 **OpenAI 官方 `openai` 包**（Chat Completions API），不经过 LangChain 等框架。
- **接口保持不变**：`LLMProvider.generate(prompt: str, **kwargs) -> str`；现有 `DummyLLM`、测试用 mock 均保留。
- **新增**：`OpenAICompatibleLLM`（`src/llm/openai_provider.py`）：使用 `openai.OpenAI(api_key=..., base_url=...)` 与 `client.chat.completions.create()`，支持 `base_url` 以对接国内代理或自建兼容端点。
- **获取方式**：`get_llm_provider(runtime_config) -> LLMProvider` 根据 `framework.llm` 返回对应 Provider；**通义千问** 使用 `tongyi` / `qwen` 预设，复用 OpenAI 兼容层 + DashScope 默认端点。

### 4.2 配置约定

**推荐：通义千问（阿里云 DashScope）**

国内直连、OpenAI 兼容接口，本程序提供 **tongyi** 预设，无需手写 base_url，只需环境变量与模型名：

- `framework.llm`：设为 **`tongyi`**（或 `qwen`）。
- `framework.llm_options`（可选，以下为默认）：
  - `api_key_env`: `DASHSCOPE_API_KEY`（从该环境变量读取 Key）
  - `base_url`: `https://dashscope.aliyuncs.com/compatible-mode/v1`（北京；新加坡/美国见阿里云文档）
  - `model`: `qwen-turbo`（可改为 `qwen-plus`、`qwen3-max` 等）
- 环境变量：在运行前设置 **`DASHSCOPE_API_KEY`**（阿里云百炼/ DashScope 控制台获取）。

**通用 OpenAI 兼容（openai / 国内代理）**

```yaml
framework:
  llm: openai   # 或 openai_compatible
  llm_options:
    model: "gpt-3.5-turbo"
    api_key_env: "OPENAI_API_KEY"
    base_url: "https://api.openai.com/v1"   # 国内代理时改为代理 URL
```

- **API Key**：**仅从环境变量读取**；键名由各 Provider 的 `api_key_env` 指定。
- **国内代理**：使用 `llm: openai` 时，将 `base_url` 设为代理地址、环境变量设为代理 Key 即可。

### 4.3 与 Agent 框架的关系（后续）

- **本阶段**：仅 LLM 层；Character/Scope Agent 仍为壳，不调用 LLM。
- **第 13 项**：在 `turn()` 内获取 `get_llm_provider(config)`，拼 prompt（含 `retrieve_character_memory`、`format_scope_events_snippet`），调用 `generate()`，解析为 `CharacterTurnOutput` / `ScopeTurnOutput`。此时仍可不引入 LangChain，仅用本仓 Provider。
- **若引入 LangChain**：可增加 `framework.llm: langchain`，内部用 LangChain 的 ChatModel 封装，对外仍实现 `LLMProvider`，便于后续 Prompt 模板、RAG、Tool 统一到 LangChain 生态。

### 4.4 测试策略

- **单元测试**：使用 **mock**（如 `unittest.mock` 或 `responses`）模拟 HTTP，不发起真实请求；或维护 **FakeLLM**（内存固定/可配置返回），用于上层解析逻辑测试。
- **集成/真实调用**：不纳入 CI 默认流程；本地通过环境变量或 pytest 标记（如 `@pytest.mark.live_api`）可选执行，用于人工验证。

---

## 五、国内代理与价格小结（便于选型）

| 方式 | 典型价格量级 | 适用 |
|------|--------------|------|
| 国内 OpenAI 代理 | 约官网 1～2 倍或按美元八折等；各平台不同 | 需 GPT/Claude、国内支付、改 URL+Key |
| 通义千问 | ￥2～40/百万 tokens（入），有免费额度 | 国内直连、性价比、开发与中小规模 |
| 文心 / 智谱等 | 按官网最新；文心按量后付 | 多模型选型、合规与地域要求 |

**建议**：**首选通义千问**（`llm: tongyi` + `DASHSCOPE_API_KEY`），国内直连、按量计费、有免费额度；同一套 OpenAI 兼容层也支持官方 OpenAI 与国内代理（`llm: openai` + `base_url`）。

---

## 六、后续步骤（与 NEXT_ITERATION 对齐）

- **第 12 项**：按本方案实现 LLM 层（OpenAI 兼容 + 可选通义）、配置扩展、环境变量约定、单测 mock/FakeLLM。
- **第 13 项**：Character/Scope Agent 在 `turn()` 中接 LLM（prompt + 检索 + 解析），可先 mock LLM。
- **第 14～15 项**：设定研究充实、DevAgent search_ideas 充实，可复用同一套 `get_llm_provider`。

选型或配置有变更时，请更新本文档与 `config/system_config.yaml`（LLM 等）、`config/example_runtime.yaml`、WORKLOG。
