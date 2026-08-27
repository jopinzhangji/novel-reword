# min-autobook — 多 Agent 自动写小说助手

基于多 Agent 协作的自动写小说实验项目：**角色独立演进** + **世界演进**。

## 设计概要

- **编排器**：调度场景与回合，协调各 Agent，裁决冲突。
- **角色 Agent**：每个主要角色一个 Agent，拥有独立记忆、目标与“思考”，随剧情演进。
- **世界 Agent**：维护设定、时间线、事件与因果，保证世界一致性并随剧情演进（多范围时可有多世界层 Agent）。
- **设定研究 Agent**：设计期/按需调用；联网搜索、分析历史小说与网文，产出**战力、等级、境界**等配套特殊设定的完整模型，写入世界设定供全书一致引用。
- **开发程序 Agent**：与主程序**保持耦合**，专为小说主程序的**自我迭代**服务；在保证运行成功与测试通过的前提下，通过搜索与联想“小说可能涉及的内容”持续完善主程序与自身（见 [TECH_IMPLEMENTATION.md](./TECH_IMPLEMENTATION.md) §3.4–§3.6）。

- 产品与协作设计见 [DESIGN.md](./DESIGN.md)。
- **写代码前请阅读** [TECH_IMPLEMENTATION.md](./TECH_IMPLEMENTATION.md)（技术实现框架与方案）。
- **文档体系（规约 / SDD / 索引）**：[docs/README.md](./docs/README.md)；流程说明 [docs/framework/SPEC_SDD.md](./docs/framework/SPEC_SDD.md)。
- **用 Cursor 开发时**：见 [docs/guides/cursor-and-devagent-workflow.md](./docs/guides/cursor-and-devagent-workflow.md)（Cursor 与 DevAgent 协同自我迭代）；待办任务见 [docs/planning/next-iteration.md](./docs/planning/next-iteration.md)。
- **Windows 开发环境**：见 [docs/guides/development.md](./docs/guides/development.md)（路径、虚拟环境、常用命令等）。
- **Agent 框架与大模型 API**：当前**未使用**任何 Agent 框架或 LLM API，智能部分**直接使用 Cursor 能力**；可选接入方式见 [docs/guides/agent-and-llm-setup.md](./docs/guides/agent-and-llm-setup.md)。

## 项目结构（规划）

```
min-autobook/
├── DESIGN.md          # 设计文档（已写）
├── README.md
├── src/
│   ├── orchestrator/  # 编排器
│   ├── agents/
│   │   ├── character/      # 角色 Agent
│   │   ├── world/          # 世界 Agent（协调者 + 范围 Agent）
│   │   └── setting_research/ # 设定研究 Agent（特殊设定完整模型）
│   │   └── dev/        # 开发程序 Agent（持续优化代码，依赖 tests/ 回归）
│   ├── context/       # 共享上下文与记忆
│   └── runtime/       # 运行与存储
├── tests/             # 配套测试程序（单元 + 集成），供 DevAgent 与 CI 使用
├── dev_agent/         # 开发程序 Agent 输出与说明（output/ 供 Cursor 读取，见 docs/guides/cursor-and-devagent-workflow.md）
│   └── output/        # failures/ suggestions/ patches/ search_ideas/
└── config/            # 设定与配置
    ├── system_config.yaml              # 系统级：LLM、debug、dev_agent（与小说内容分离）
    ├── novel_writing.yaml              # 小说写作基础：流程、设定研究、作者在环、storage 等（并入 runtime）
    ├── example_world.yaml
    ├── example_characters.yaml
    ├── example_runtime.yaml            # （可选）开局 novel_run + agents；缺失则使用内置默认
    └── example_special_settings.yaml   # 战力/等级/境界/阶级等（设定研究 Agent 产出示例）
```

## 当前状态

- 设计文档已就绪。
- 代码结构为占位，待实现。
- 工作进度与每日计划见 [WORKLOG.md](./WORKLOG.md)（工作日程纪要，每日追加更新）。

## 版本控制（Git）

- 项目已执行 **`git init`**，便于回溯与版本管理。
- 当前文件已纳入暂存区（`git add -A`）。**请在系统终端执行提交**（Cursor 内可能因 `--trailer` 报错）：
  ```bash
  cd f:\learn\min-autobook
  git commit -m "Initial commit: config, storage, context, agent shells, orchestrator, run_n_turns, resolve_turn_conflict, run_novel, tests 56 passing"
  ```
- 若在 Cursor 内执行 `git commit` 时出现 **unknown option `trailer`**，多为环境为 commit 自动加了 `--trailer` 而本机 Git 版本不支持。请在**系统终端**（PowerShell / cmd）中进入项目根目录执行上述命令完成首次提交。
- 日常：`git add` → `git commit` → 按需 `git push`（若已配置远程仓库）。

## 如何开始

1. 阅读 **DESIGN.md** 了解整体架构与协作流程。
2. 阅读 **TECH_IMPLEMENTATION.md** 确定技术栈、配置与接口，作为写代码前的参考。
3. 按技术文档建议顺序：配置与存储 → Context → 单 Agent 壳 → 编排器与回合循环 → 冲突裁决 → LLM/检索 → 设定研究。
