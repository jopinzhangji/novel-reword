# 文档中心（min-autobook）

本目录按 **通用软件文档术语** 组织：**specifications**（规约入口）、**design**（专题设计 / SDD）、**planning**（路线图与 MVP）、**guides**（操作手册）、**framework**（文档元体系）、**examples**（示例素材）。

**产品与核心技术规约**仍在仓库根目录：[DESIGN.md](../DESIGN.md)、[TECH_IMPLEMENTATION.md](../TECH_IMPLEMENTATION.md)。

---

## 规约驱动 + SDD（摘要）

- **Specifications**：L0/L1 见根目录 **DESIGN**、**TECH_IMPLEMENTATION**；入口说明见 [specs/README.md](./specs/README.md)。  
- **Design（SDD）**：`design/` 下各专题，描述子域结构与代码挂载点。  
- **Planning**：`planning/` 下迭代清单与 MVP 执行说明。  
- **Guides**：环境、用法、协作、Git。

**分层定义、登记表、推荐开发流程**：[framework/SPEC_SDD.md](./framework/SPEC_SDD.md)。

---

## 目录结构

```
docs/
├── README.md                 # 本文件
├── specs/                    # 规约入口（根目录 DESIGN / TECH 的索引）
├── design/                   # 专题设计（SDD）
├── planning/                 # 迭代与 MVP
├── guides/                   # 操作与协作手册
├── framework/                # SPEC + SDD 元文档
└── examples/                 # YAML 等示例
```

---

## 按角色入口

| 角色 | 建议阅读顺序 |
|------|----------------|
| **新加入开发** | [DESIGN.md](../DESIGN.md) → [TECH_IMPLEMENTATION.md](../TECH_IMPLEMENTATION.md) → [framework/SPEC_SDD.md](./framework/SPEC_SDD.md) → [guides/development.md](./guides/development.md) |
| **实现某一功能** | [design/](#design专题设计) 对应专题 → TECH → [planning/next-iteration.md](./planning/next-iteration.md) |
| **Cursor / DevAgent** | [guides/cursor-and-devagent-workflow.md](./guides/cursor-and-devagent-workflow.md) + [SPEC_SDD](./framework/SPEC_SDD.md) §5 |
| **使用者** | [guides/usage.md](./guides/usage.md) + 根目录 [README.md](../README.md) |

---

## `specs/` 规约入口

| 文件 | 说明 |
|------|------|
| [specs/README.md](./specs/README.md) | L0/L1 规约在根目录的路径说明 |
| [specs/author-in-loop-spec.md](./specs/author-in-loop-spec.md) | 作者在环 **L1 行为规约**（MUST/SHOULD；与 `design/` 中 SDD 分工） |

---

## `design/` 专题设计

| 文件 | 说明 |
|------|------|
| [design/author-agent-harness.md](./design/author-agent-harness.md) | 作者在环统一入口与 Agent Harness（目标架构） |
| [design/novel-assistant-pm-agent-model.md](./design/novel-assistant-pm-agent-model.md) | PM / 小说项目 / 多智能体与记忆体（概念方案，讨论稿） |
| [design/author-interaction.md](./design/author-interaction.md) | 作者在环统一交互、意图与检索（状态机 M1–M6） |
| [design/memory-storage-and-retrieval.md](./design/memory-storage-and-retrieval.md) | 记忆、双写、检索 |
| [design/outline-and-beats.md](./design/outline-and-beats.md) | 大纲、节拍、主角轴、多线 |
| [design/character-growth-state-machine.md](./design/character-growth-state-machine.md) | 成长状态机（规划） |
| [design/llm-and-agents.md](./design/llm-and-agents.md) | LLM 与 Agent 抽象 |
| [design/context-compression-adaptive-layered.md](./design/context-compression-adaptive-layered.md) | 组装后上下文压缩（自适应分层任务锚定，**D8**） |
| [design/novel-reader-ui.md](./design/novel-reader-ui.md) | **作者在环工作台**（阅览 + 设定/章节交互，**D9**） |

---

## `planning/` 计划与 MVP

| 文件 | 说明 |
|------|------|
| [planning/next-iteration.md](./planning/next-iteration.md) | 迭代清单、已完成勾选 |
| [planning/outline-mvp-plan.md](./planning/outline-mvp-plan.md) | 大纲 MVP 分阶段与验收 |

---

## `guides/` 手册

| 文件 | 说明 |
|------|------|
| [guides/usage.md](./guides/usage.md) | 使用说明 |
| [guides/development.md](./guides/development.md) | 开发环境（Windows 等） |
| [guides/cursor-and-devagent-workflow.md](./guides/cursor-and-devagent-workflow.md) | Cursor 与 DevAgent |
| [guides/agent-and-llm-setup.md](./guides/agent-and-llm-setup.md) | 可选 Agent 框架 / API |
| [guides/git-commit.md](./guides/git-commit.md) | 提交说明 |

---

## `framework/` 元文档

| 文件 | 说明 |
|------|------|
| [framework/SPEC_SDD.md](./framework/SPEC_SDD.md) | 规约分层、登记表、SDD 流程 |
| [framework/README.md](./framework/README.md) | 本目录说明 |

---

## `examples/`

| 路径 | 说明 |
|------|------|
| [examples/outline.yaml](./examples/outline.yaml) | 大纲 YAML 示例 |
| [examples/outline_progress.yaml](./examples/outline_progress.yaml) | 进度示例 |
| [examples/relationship_graph.yaml](./examples/relationship_graph.yaml) | 关系图示例 |

---

## 过程纪要（非规约）

| 文档 | 说明 |
|------|------|
| [WORKLOG.md](../WORKLOG.md) | 工作日程与决策记录（根目录） |

---

## 维护约定（摘要）

- 新增横切能力：先 **design/** 或 **planning/** 文稿，再对齐 **TECH**，最后改代码与测试。  
- 详见 [framework/SPEC_SDD.md](./framework/SPEC_SDD.md) §4–§6。

---

*修订：2026-03-29 子目录化（specs / design / planning / guides）。*
