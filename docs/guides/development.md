# 开发环境说明

本项目在 **Windows** 下开发，以下说明保证与 Linux 的差异得到兼容处理。

---

## 一、Windows 与 Linux 差异及处理

| 项目 | Windows 情况 | 处理方式 |
|------|----------------|----------|
| **路径分隔符** | 使用 `\` | 代码中统一用 `pathlib.Path`，配置里路径建议用正斜杠 `src/`、`config/`，Path 会自动适配当前系统。 |
| **换行符** | 默认 CRLF | 仓库内建议统一 LF；若为 CRLF，Python/YAML 读写正常。Git 可设 `core.autocrlf true` 按需转换。 |
| **测试命令** | 同 Linux | 在项目根目录执行：`python -m pytest tests/ -v` 或 `pytest tests/ -v`（需已安装 pytest）。 |
| **入口脚本** | 无 bash | 使用 Python 入口（如 `python run_novel.py`），跨平台。若有 shell 脚本，可额外提供 `.bat` 或 PowerShell。 |
| **文件系统大小写** | 不区分大小写 | 模块与文件名建议与文档一致（如 `TurnContext`、`character_id`），便于将来在 Linux 部署。 |

**结论**：按本文档开发即可，无需切换到 Linux；后续在 Linux 部署时同一套代码可直接使用。

---

## 二、Windows 下建议环境

- **Python**：3.10 或以上，从 [python.org](https://www.python.org/downloads/) 安装，安装时勾选 “Add Python to PATH”。
- **若命令行中 `python` 不可用**：可使用 Windows 自带的 Python 启动器 `py`，例如：`py -m venv .venv`、`py -m pytest tests/ -v`。
- **终端**：PowerShell 或 Windows Terminal；在项目根目录执行命令时路径使用项目根即可。

---

## 三、虚拟环境与依赖（Windows）

在项目根目录（如 `f:\learn\min-autobook`）执行：

```powershell
# 创建虚拟环境（若 python 不可用则用 py）
python -m venv .venv
# 或：py -m venv .venv

# 激活（PowerShell）
.venv\Scripts\Activate.ps1
# 若执行策略限制，可先：Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 安装依赖（不激活也可用 .venv\Scripts\pip.exe）
pip install -r requirements.txt
# 或：.venv\Scripts\pip.exe install -r requirements.txt
```

激活后，命令行前会显示 `(.venv)`，之后所有 `pip install` 与 `pytest` 均在该环境中。

---

## 四、常用命令（Windows）

| 操作 | 命令 |
|------|------|
| 进入项目根 | `cd f:\learn\min-autobook`（或你的实际路径） |
| 激活虚拟环境 | `.venv\Scripts\Activate.ps1` |
| 运行测试 | `python -m pytest tests/ -v` 或 `pytest tests/ -v` |
| 运行主程序 | 待实现后为 `python run_novel.py` 等 |

---

## 五、环境检查清单

搭建完成后可自检：

| 检查项 | 命令 | 预期 |
|--------|------|------|
| Python 版本 | `py --version` 或 `python --version` | 3.10 或以上 |
| 虚拟环境 | 存在目录 `.venv` | 项目根下已有 `.venv` |
| 依赖安装 | `.venv\Scripts\pip.exe list` | 含 pytest |
| 测试可运行 | `.venv\Scripts\python.exe -m pytest tests/ -v` | 能执行（当前 0 条用例也属正常） |

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
