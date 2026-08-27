# Agent 框架与大模型 API 配置说明

本文说明：**当前实现**是否使用 Agent 框架与 LLM、**是否直接使用 Cursor 能力**，以及**若要接入大模型/框架**如何配置。

---

## 一、当前实现：无框架、无 LLM，直接使用 Cursor 能力

| 问题 | 答案 |
|------|------|
| **有没有用 Agent 框架（LangGraph / AutoGen / CrewAI 等）？** | **没有**。当前 DevAgent 是纯 Python 脚本：读配置、跑测试命令（如 pytest）、把结果写入 `dev_agent/output/`（latest_run.json、failures、suggestions）。没有接入 LangGraph、AutoGen、CrewAI 等。 |
| **有没有配置大模型 API（OpenAI / 国产等）？** | **没有**。当前没有任何 LLM 调用，没有 API Key、base_url、model 等配置。 |
| **是直接使用 Cursor 的能力吗？** | **是**。当前流程里：**DevAgent** 只做「跑测试 + 写结构化输出」；**分析与改代码、修失败、实现建议**都由 **Cursor（我）** 在你对话时完成。你只要说「根据 DevAgent 最新输出处理一下」，我就去读 `dev_agent/output/` 并实现/修复。也就是说，**智能部分直接用的是 Cursor 的能力**，项目里没有自己接大模型。 |

**小结**：当前 = **DevAgent 跑测试 + 写输出**，**Cursor 读输出 + 改代码**。无需在项目里配置任何 Agent 框架或大模型 API，即可完成「自我迭代与 Cursor 交互」。

---

## 二、这样设计的原因

1. **先跑通流程**：先把「DevAgent 写 → Cursor 读 → 你决策」的闭环跑通，再按需加 LLM/框架。
2. **避免重复**：你在 Cursor 里开发时，**已经在使用 Cursor 自带的大模型能力**；项目里再接一套 API 属于可选增强（例如无人值守、定时跑 DevAgent 并自动生成建议）。
3. **可选扩展**：若你希望 DevAgent **自己**分析失败原因、自己生成修改建议或补丁（而不只是写「请 Cursor 修」），再在项目里配置大模型 API 并接入 Agent 框架即可（见下）。

---

## 三、若要接入 Agent 框架与大模型 API（可选）

若后续希望 DevAgent（或小说主程序里的角色/世界 Agent）**自己调用大模型**，可按以下方式配置与实现。

### 3.1 大模型 API 配置（环境变量，推荐）

不在代码里写 Key，用环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API Key | `sk-...` |
| `OPENAI_API_BASE` | 可选，兼容 OpenAI 的国产/代理 base_url | `https://api.xxx.com/v1` |
| `ANTHROPIC_API_KEY` | 若用 Claude | |
| 其他 | 按所用 SDK（如 LangChain）文档配置 | |

示例 `.env`（不要提交到 Git，已加入 .gitignore）：

```bash
OPENAI_API_KEY=sk-your-key
OPENAI_API_BASE=https://api.xxx.com/v1
```

代码中通过 `os.environ.get("OPENAI_API_KEY")` 或 `python-dotenv` 读取。

### 3.2 配置文件占位（可选）

在 `config/system_config.yaml`（推荐）或 `config/example_runtime.yaml` 中配置 `framework`，供程序读取：

```yaml
# 可选：大模型与 Agent 框架（当前未使用）
llm:
  provider: openai   # openai | anthropic | local
  model: gpt-4o-mini
  api_base: null      # 空则用默认；国产/代理可填 URL
  api_key_env: OPENAI_API_KEY

framework:
  orchestrator: langgraph   # 小说主程序编排；DevAgent 当前未用
  llm: langchain           # 统一 LLM 调用
```

当前实现**不会读这些字段**，仅为后续接入预留。

### 3.3 Agent 框架与 LLM 使用场景

| 场景 | 是否需要框架/LLM | 说明 |
|------|------------------|------|
| **DevAgent 只跑测试 + 写输出，由 Cursor 改代码** | **不需要** | 当前做法，直接使用 Cursor 能力。 |
| **DevAgent 自己分析失败、生成建议或补丁** | 需要 LLM；框架可选 | 可接 LangChain 调用 OpenAI/国产 API，读测试输出与代码，生成 suggestions/*.md 或 patches；仍由 Cursor 审查后应用。 |
| **小说主程序（角色/世界 Agent）** | 需要 LLM + 可选框架 | 见 TECH_IMPLEMENTATION §2：推荐 LangGraph 编排 + LangChain 调用 LLM；需在项目里配置 API。 |

### 3.4 依赖（仅当接入时再安装）

若后续接入 LangChain + OpenAI，可增加依赖（当前未加入 requirements.txt）：

```
langchain-core
langchain-openai
python-dotenv
```

---

## 四、总结

- **当前**：无 Agent 框架、无大模型 API 配置；**直接使用 Cursor 的能力**完成「读 DevAgent 输出 + 分析与改代码」。
- **与 Cursor 交互**：DevAgent 把「失败报告、建议」写到 `dev_agent/output/`，你在 Cursor 里说「根据 DevAgent 最新输出处理一下」，我读这些文件并执行修改，这就是当前的交互方式。
- **可选**：若要 DevAgent 或小说主程序自己调大模型，再按 §3 配置 API 与可选框架；不影响现有「DevAgent + Cursor」协同流程。
