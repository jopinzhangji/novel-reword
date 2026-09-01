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
- **Linux 开发环境**：见 [docs/guides/development.md](./docs/guides/development.md)（虚拟环境、依赖、常用命令等；本项目最初在 Windows 下开发，代码跨平台，现以 Linux 为主）。
- **Agent 框架与大模型 API**：智能部分默认用 **LLM**（OpenAI 兼容端点，火山方舟 `deepseek-v4`）；**不配置密钥时自动回退到内置 dummy**（确定性、无 LLM），本地跑通不影响测试。密钥与切换见下文「启用：配置大模型」。可选接入方式见 [docs/guides/agent-and-llm-setup.md](./docs/guides/agent-and-llm-setup.md)。

## 项目结构（规划）

```
min-autobook/
├── README.md
├── run_novel.py                 # 主流程（自动写回）
├── run_novel_with_author.py     # 主流程（作者在环：以作者显式指令驱动边界决策）
├── src/
│   ├── orchestrator/            # 编排器（回合循环、冲突裁决、跨层协调）
│   ├── agents/                  # 角色/世界/设定研究等 Agent 壳
│   ├── author_loop/             # 作者在环：意图分类、检索注入、上下文压缩(CC)
│   ├── author_harness/          # 在环输入桥、prompt 拼装、联网搜索(playwright)
│   ├── retrieval/               # 信息视野、语义关系、角色成长、大纲 store
│   ├── workbench/               # 工作台确定性服务层（纯 Py、无 LLM/Web 依赖）
│   └── runtime/                 # Storage、事件簿、进度写回、系统配置
├── web/
│   ├── api/                     # FastAPI 后端(create_app) + session 作者在环 + 鉴权
│   └── static/index.html        # 无构建静态仪表盘（进度卡/关系谱/人物/节拍/控制台）
├── data/novels/<slug>/          # 落地数据：book/、config/、meta.yaml（多小说）
├── config/                      # 系统/小说/Web 配置 + example_*
└── tests/                       # 单元 + 集成（458 通过 + 1 跳过）
```

## 当前状态

- 核心链路已落地：配置加载、Storage、编排器与回合循环、冲突裁决、作者在环（两阶段审阅 + 工作台 Web Session 在环）、开书前设定阶段、LLM 接入（OpenAI 兼容 / 通义）、记忆与内容双写、检索注入、**大纲 MVP（读侧 + 进度写回）**、**角色独立成长状态机**、**上下文压缩（CC-b/c，确定性）**、**工作台本地仪表盘（G4 / GG-W 面板）** 等；`tests/` **458 用例通过 + 1 跳过**。
- 详细进度与待办见 [docs/planning/next-iteration.md](./docs/planning/next-iteration.md) 与 [WORKLOG.md](./WORKLOG.md)（工作日程纪要）。

## 启用（环境 / 大模型 / 运行）

### 1. 环境与依赖

```bash
cd /root/novel-reword/novel-reword
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # PyYAML / pytest / openai / playwright 等
```

详见 [docs/guides/development.md](./docs/guides/development.md)。

### 2. 配置大模型（可选；不配则自动回退 dummy）

- 配置文件：`config/system_config.yaml` → `framework.llm`。现默认 `openai_compatible`，指向**火山方舟（Volcengine Ark）** OpenAI 兼容端点：
  ```yaml
  framework:
    llm: openai_compatible
    llm_options:
      api_key_env: "DASHSCOPE_API_KEY"
      model: "deepseek-v4"
      base_url: "https://ark.cn-beijing.volces.com/api/coding/v3"
  ```
- 密钥：从环境变量 `DASHSCOPE_API_KEY` 或项目根 `.env`（已 gitignore）读取，**不会写入仓库**。未配置密钥时自动回退内置 **dummy（确定性、无 LLM）**，跑通本地链路与测试不受影响。
- 实际运行的 LLM 提供方由密钥/`.env` 驱动；工作台「系统」面板的 LLM 仅**只读**展示。

### 3. 运行测试

```bash
python3 -m pytest tests/ -p no:cacheprovider    # 全量：458 通过 + 1 跳过
LLM_E2E=1 python3 -m pytest tests/integration/test_llm_live_e2e.py -p no:cacheprovider   # 真实 LLM 一回合联调
```

未设 `.env` 的机器、跑本地开发时，默认用 dummy，无需真实密钥。

### 4. 启动主流程（写小说）

```bash
python3 run_novel.py                # 自动写回
python3 run_novel_with_author.py    # 作者在环（以作者显式指令驱动节拍/进度决策）
```

## 部署（工作台 Web / 远程访问）

### 本地仪表盘（Novel-Data Workbench）

静态 + FastAPI 面板，展示多小说进度卡、关系谱、人物成长/记忆、节拍与控制台：

```bash
python -m web.api.server                      # 读 config/web_api.yaml，默认 127.0.0.1:8000
# 或：
python -m uvicorn web.api.app:app             # 快速起（工厂 create_app）
```

- 浏览器打开 http://127.0.0.1:8000/ 。
- 「作者在环」页可开 Web Session 跑 `run_novel_with_author.main`（后端线程 + 互斥），也可单独启用 CLI 终端作者在环（见下）。

### 作者在环（Author Workbench）开关

`config/novel_writing.yaml` → `runtime.author_workbench.enabled`（默认 `false`）：

- `false`（默认）：CLI 直接读终端 stdin，传统交互。
- `true`：走 Web Session 桥；CLI 直跑时经 `LogOnlyAuthorIngress` **不读 stdin、仅打日志**，避免终端读到另一进程的输入。`/system` 面板可在线改（下一会话生效）。

### 远程访问与鉴权

`config/web_api.yaml`（默认仅本机、无鉴权，**适合本地自用**）：

```yaml
server:
  host: "127.0.0.1"   # 默认仅本机
  port: 8000
auth:
  enabled: false
  username: ""
  password: ""
```

- **仅本机**：保持默认即可（最简单、最安全）。
- **局域网/公网**：把 `server.host` 改为 `"0.0.0.0"`，并**必须** `auth.enabled: true` + 填 `username`/`password`。空口令时启动会 **fail-fast 报错**（绝不静默无鉴权裸奔）；Basic Auth 走常量时间比较。
- **公网建议**：不要用明文口令直接对公网，前置**反向代理 / SSH 隧道**（如 `ssh -L` 则 0 暴露写口），或后续接更强制认证。
- 远程安全强化（OAuth/锁文件/CORS 等）见排期 **#31，刻意放到工作序列最后**。

### 上下文压缩（CC-b/c，可选）

`runtime.author_interaction.context_compress.enabled`（默认 `false`，无阈行为不变）：

```yaml
runtime:
  author_interaction:
    context_compress:
      enabled: true            # 开
      threshold_ratio: 0.75    # 检索总量超过 0.75×预算 才触发
      target_ratio: 0.5        # 压到 0.5×预算（滞回）
```

确定性结构保留削减、来源标签由拼装层保留、不塌成单段结论；关掉即恢复原检索行为。

## 版本控制（Git）

- 项目已执行 **`git init`**，便于回溯与版本管理。
- 日常提交（在项目根目录）：`git add` -> `git commit -m "<提交说明>"` -> 按需 `git push`（远程仓库已配置 `origin/main`）。

## 如何开始

1. 阅读 **DESIGN.md** 了解整体架构与协作流程。
2. 阅读 **TECH_IMPLEMENTATION.md** 确定技术栈、配置与接口，作为写代码前的参考。
3. 按技术文档建议顺序：配置与存储 → Context → 单 Agent 壳 → 编排器与回合循环 → 冲突裁决 → LLM/检索 → 设定研究。
4. **上手试跑**：先按上文「启用」配好虚拟环境（无密钥可先跑 dummy），本地起 `python3 run_novel_with_author.py` 走一个作者在环回合；再 `python -m web.api.server` 打开仪表盘看进度与人物。全部可离线验证。
