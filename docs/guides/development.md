# 开发环境说明（Linux）

本项目最初在 Windows 下开发，现已迁移到 **Linux** 运行与开发；代码本身为纯 Python、跨平台（统一 `pathlib`、显式 `encoding="utf-8"`），无需平台分支处理。本文档为 Linux 环境指引。

---

## 一、平台差异说明（历史与现状）

| 项目 | 说明 |
|------|------|
| **路径分隔符** | 代码统一用 `pathlib.Path`；配置里路径用正斜杠 `src/`、`config/`。 |
| **换行符** | 仓库统一 LF；Python/YAML 读写均正常。 |
| **文件编码** | 所有文件 I/O 显式 `encoding="utf-8"`，无 GBK/locale 依赖；仓库文件均为 UTF-8。 |
| **测试命令** | 在项目根目录执行：`python3 -m pytest tests/ -v`（需已安装 pytest 与 pytest-timeout）。 |
| **入口脚本** | 全部为 Python 入口（`run_novel.py` 等），无 shell/bat 依赖，天然跨平台。 |
| **交互输入** | 作者在环 CLI 为中文交互，Linux 终端需 UTF-8 locale（主流发行版默认即可）。 |
| **联网搜索（I5）** | 依赖 Playwright Chromium；Linux 下首次使用前需 `playwright install chromium`（含系统依赖 `playwright install-deps`）。 |

---

## 二、Linux 下环境搭建

- **Python**：3.10 或以上（推荐 3.12），系统包管理器安装或使用 pyenv。

```bash
# 进入项目根（按实际路径调整）
cd /root/novel-reword/novel-reword

# 创建虚拟环境
python3 -m venv .venv

# 激活
source .venv/bin/activate

# 安装依赖（含 PyYAML、pytest、pytest-timeout、openai、playwright）
pip install -r requirements.txt

# 联网搜索（I5）需要浏览器内核（可选）
playwright install chromium
```

不激活虚拟环境时也可直接使用 `.venv/bin/python`、`.venv/bin/pip`。

---

## 三、常用命令（Linux）

| 操作 | 命令 |
|------|------|
| 进入项目根 | `cd /root/novel-reword/novel-reword`（或实际路径） |
| 激活虚拟环境 | `source .venv/bin/activate` |
| 运行测试 | `python3 -m pytest tests/ -v` |
| 运行主程序（自动写回） | `python3 run_novel.py` |
| 运行主程序（作者在环） | `python3 run_novel_with_author.py` |
| 运行 DevAgent | `python3 run_dev_agent.py` |
| 测试 LLM 配置 | `python3 test_llm_chat.py` |

环境变量（如回合数、日志级别）使用 `export`：

```bash
export MIN_AUTOBOOK_TURNS=3
python3 run_novel.py
```

---

## 四、环境检查清单

搭建完成后可自检：

| 检查项 | 命令 | 预期 |
|--------|------|------|
| Python 版本 | `python3 --version` | 3.10 或以上 |
| 虚拟环境 | 存在目录 `.venv` | 项目根下 |
| 依赖安装 | `.venv/bin/pip list` | 含 pytest、pytest-timeout、PyYAML、openai、playwright |
| 测试可运行 | `.venv/bin/python -m pytest tests/ -v` | 全部通过（当前 251 条） |
| LLM Key（可选） | `echo $DASHSCOPE_API_KEY` | 已设置（未设置时回退 dummy 壳模式） |
| Chromium（可选） | `ls ~/.cache/ms-playwright` | 含 chromium（联网搜索用） |

---

## 五、LLM 配置（OpenAI 兼容端点）

当前 `config/system_config.yaml` 已配置 `framework.llm: openai_compatible`，指向**火山方舟（Volcengine Ark）**的 OpenAI 兼容端点、模型 `deepseek-v4-pro`；密钥从 `DASHSCOPE_API_KEY` 环境变量（或项目根 `.env`）读取，只需：

```bash
export DASHSCOPE_API_KEY=<你的 Key>
python3 test_llm_chat.py   # 验证连通
```

如需改用**通义千问（DashScope）**，把 `framework.llm` 改为 `tongyi`（或 `qwen-plus`）并将 `base_url` 设回 `https://dashscope.aliyuncs.com/compatible-mode/v1`。Key 仅通过环境变量/`.env` 读取，不会写入仓库。详见 [design/llm-and-agents.md](../design/llm-and-agents.md) 与 [usage.md](./usage.md) §2.4。

---

## 六、与文档的对应关系

- 文档总索引与规约分层见 [README.md](../README.md)、[framework/SPEC_SDD.md](../framework/SPEC_SDD.md)。
- 技术实现与配置结构见 [TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md)。
- Cursor 与 DevAgent 协同见 [cursor-and-devagent-workflow.md](./cursor-and-devagent-workflow.md)。
- 迭代待办见 [planning/next-iteration.md](../planning/next-iteration.md)。

---

## 七、代码修改前：Spec / SDD 先行

涉及 **`src/`** 中作者在环、设定阶段、意图分类、检索注入、回合审阅等行为时：

1. 先阅读并对齐 **[specs/author-in-loop-spec.md](../specs/author-in-loop-spec.md)**（L1，含 **§1.1**）与 **[design/author-agent-harness.md](../design/author-agent-harness.md)**（L2，含 **§6.1 R0–R8**）。
2. 在动手改代码前，把「将改哪些规约条目、哪些模块、如何验收」写清楚（PR 描述或协作记录），**方案确认后再实现**。
3. 流程说明与分层见 [framework/SPEC_SDD.md](../framework/SPEC_SDD.md) **§2.1**、§4；合并后更新 [planning/next-iteration.md](../planning/next-iteration.md) 与根目录 [WORKLOG.md](../../WORKLOG.md)。
4. 使用 Cursor 时，仓库已启用 **`.cursor/rules/doc-first-spec-sdd.mdc`**（`alwaysApply`），助手应默认遵守上述顺序。
