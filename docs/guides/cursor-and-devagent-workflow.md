# Cursor 与 DevAgent 协同自我迭代方案

你在用 **Cursor** 辅助开发，项目里设计了 **DevAgent（开发程序 Agent）** 专为主程序自我迭代。本文档说明：**二者如何配合**、**谁做什么**、**共享接口与流程**，便于持续迭代开发。

---

## 一、能否协同完成自我迭代？——可以

| 角色 | 能力 | 在自我迭代中的分工 |
|------|------|---------------------|
| **Cursor（我）** | 与你对话、读文档与代码、编辑文件、运行命令、运行测试、修复错误、更新文档。**强项**：按你的意图做具体实现与审查，人机协同、即时反馈。 | **执行与审查**：根据 DESIGN/TECH/WORKLOG 实现功能、根据 DevAgent 的输出做修复或采纳建议、跑测试并确认通过、更新 WORKLOG 与文档。 |
| **DevAgent（项目内）** | 按 §3.6 设计：跑测试、搜索联想“小说可能涉及的内容”、分析代码与文档、产出修改建议或补丁。**强项**：无人值守或定时运行、批量回归、结构化建议。 | **提议与回归**：产出“待办建议/失败报告/补丁”写到约定目录；运行测试并只保留通过的修改；为 Cursor 提供“下一步可做什么”的输入。 |
| **你** | 提需求、做决策、确认是否采纳、在 Cursor 里发起“处理 DevAgent 建议”等。 | **决策与触发**：决定迭代优先级、让我“按 DevAgent 最新输出”实现或审查、确认后合并/关闭建议。 |

结论：**可以**。Cursor 负责“在你面前把事做完、保证能跑”，DevAgent 负责“自动发现可改进点、写出建议、保证测试通过才保留”；你居中决策与触发，二者通过**约定好的输出目录与文件格式**协同。

**当前实现**：项目内**未使用**任何 Agent 框架（LangGraph/AutoGen 等）或大模型 API；DevAgent 只做「跑测试 + 写输出」，**分析与改代码直接使用 Cursor 的能力**。若要接入框架与 API，见 [agent-and-llm-setup.md](./agent-and-llm-setup.md)。

**自我迭代 = 定时让 Cursor 干活**：自我迭代不仅是「跑测试」，而是**定时运行 DevAgent**（跑测试 + 产出/更新「要 Cursor 干的活」清单 `cursor_tasks.md`）；你**定期在 Cursor 里**根据 cursor_tasks 让 Cursor 干活。**第一个任务开始后**，后续所有任务形成闭环：**Cursor 完成本批后产出「下一步计划」**（写入 `next_plan.md`）→ **DevAgent 再次运行时读取 next_plan，将该计划写入 cursor_tasks 告诉 Cursor** → Cursor 按「下一步计划」+ 本次运行待办执行，并再产出下一步计划 → **循环直到功能测试通过、所有功能完成**。

---

## 二、协同原则

1. **单一事实来源**：主程序行为以 **tests/** 与 **DESIGN/TECH** 为准；DevAgent 与 Cursor 的修改都以“运行成功、测试通过”为准入门槛。
2. **DevAgent 写、Cursor 读**：DevAgent 把“建议、失败报告、补丁摘要”写到约定目录（见下），不强制直接改主代码；Cursor 读取后由**你和我**决定是否实现、如何实现，避免无人审查的自动改码。
3. **可逆与可追溯**：DevAgent 若自动应用补丁，应先写补丁文件与摘要，你可在 Cursor 里让我审查再应用；或 DevAgent 只写建议不应用，全部由 Cursor 实现。
4. **当前无 DevAgent 时**：由 Cursor + 你按 TECH_IMPLEMENTATION 与 WORKLOG 逐步实现，并维护一份“迭代清单”（见下），相当于先把“人+Cursor”的迭代流程跑通，再接入 DevAgent。

---

## 三、共享接口：DevAgent 输出目录与格式

建议在仓库中约定 DevAgent 的**输出目录**与**文件约定**，便于 Cursor 识别并处理。

### 3.1 目录结构（建议）

```
dev_agent/
├── output/                    # DevAgent 写入；Cursor 读取并据此行动
│   ├── next_plan.md           # 【Cursor 产出】下一步计划；DevAgent 再次运行时读取并写入 cursor_tasks 转述给 Cursor
│   ├── cursor_tasks.md        # 【DevAgent 产出】当前「要 Cursor 干的活」（含 Cursor 上次的下一步计划 + 本次运行待办），供 Cursor 执行
│   ├── latest_run.json        # 最近一次运行摘要：测试是否通过、建议条数等
│   ├── failures/              # 测试失败或运行失败时的报告
│   │   └── YYYY-MM-DD_HH-mm.md
│   ├── suggestions/           # 改进建议（功能、重构、测试补充等）
│   │   └── YYYY-MM-DD_HH-mm.md
│   ├── patches/               # 可选：DevAgent 生成的补丁与摘要
│   │   ├── suggested_001.patch
│   │   └── suggested_001_summary.md
│   └── search_ideas/          # 搜索与联想产出的“小说可能涉及的内容”与改进点
│       └── YYYY-MM-DD.md
├── config/                    # DevAgent 自身配置（若与主 config 分离）
└── README.md                  # 说明 output 含义及 Cursor 如何消费
```

### 3.2 建议的文件约定（供实现时用）

- **latest_run.json** 示例：`{ "ok": false, "test_summary": "2 failed, 3 passed", "suggestions_count": 1, "failure_report": "failures/2026-02-11_10-00.md" }`
- **suggestions/*.md**：每条建议可含：标题、类型（fix/feature/refactor/test）、描述、涉及文件或模块、可选优先级。
- **patches/*_summary.md**：补丁的简短说明、影响范围、建议审查点。

这样 Cursor 侧只需：读 `dev_agent/output/cursor_tasks.md` 或 `latest_run.json` 及对应 failures/suggestions，按类型（失败报告 / 建议 / 补丁）决定是“先修失败”还是“实现某条建议”或“审查并应用补丁”。

---

## 三之一、自我迭代 = 定时让 Cursor 干活（如何定时运行 DevAgent）

自我迭代**不仅是跑测试**，而是：**定时运行 DevAgent**（跑测试 + 产出/更新「要 Cursor 干的活」），你**定期在 Cursor 里**根据这些待办让 Cursor 干活。

### 1. 每次 DevAgent 运行会做什么

- 跑 `test_command`（如 pytest）；
- 写 `latest_run.json`、失败时写 `failures/*.md` 与 `suggestions/*.md`；
- **写 `cursor_tasks.md`**：当前「要 Cursor 干的活」清单（先修失败、再跑测试、或查看 suggestions 等）。  
你在 Cursor 里说「根据 dev_agent/output/cursor_tasks 处理一下」，我就按这份清单执行。

### 2. 如何定时运行 DevAgent

| 方式 | 说明 |
|------|------|
| **cron（Linux/macOS）** | 例如每小时：`0 * * * * cd /path/to/novel-reword && .venv/bin/python run_dev_agent.py` |
| **按需** | 在项目根执行 `python3 run_dev_agent.py`（或 `.venv/bin/python run_dev_agent.py`）；或配置 `trigger: on_demand` 由 CI/脚本触发。 |
| **continuous（可选）** | 若配置 `trigger: continuous`，可后续实现「循环：run_once + sleep(interval)」，在后台定时跑；当前未实现，可用系统计划任务代替。 |

### 3. 第一个任务开始后的闭环：Cursor 产出下一步计划 → DevAgent 转述 → 循环直到功能完成

- **第一轮**：DevAgent 跑测试，写 cursor_tasks（先修失败、再跑测试等）；你在 Cursor 里说「根据 dev_agent/output/cursor_tasks 处理一下」，Cursor 按清单执行。
- **Cursor 完成本批后**：必须**产出「下一步计划」**，写入 **`dev_agent/output/next_plan.md`**（例如：下一项要实现的功能、要补充的测试、要修的点等）。这是后续所有任务的输入。
- **下一轮**：定时或按需再次运行 DevAgent；DevAgent **读取 next_plan.md**，将该计划写入 **cursor_tasks.md**（转述给 Cursor），并追加本次运行待办（若测试失败则先修失败等）。Cursor 打开后读 cursor_tasks，**先按「下一步计划」推进，再处理本次运行待办**；完成后再次写入 next_plan.md。
- **循环**：重复上述步骤，**直到功能测试通过、所有功能完成**。结束时可在 next_plan.md 写「全部完成」或留空，DevAgent 仍会转述，Cursor 可据此收尾。

### 4. 你在 Cursor 里怎么做（定时让 Cursor 干活）

- **定期**（如每天或每次打开项目）：打开 `dev_agent/output/cursor_tasks.md`，在 Cursor 里说「根据 dev_agent/output/cursor_tasks 处理一下」。
- 我会读 cursor_tasks（含「下一步计划」+ 本次运行待办）、failures、suggestions，**先按下一步计划执行，再修失败、跑测试、实现建议**，更新 `WORKLOG.md` 与 [planning/next-iteration.md](../planning/next-iteration.md)。
- **完成后**：请产出新的「下一步计划」写入 **`dev_agent/output/next_plan.md`**，供下一轮 DevAgent 转述给 Cursor。循环直到功能测试通过、所有功能完成。

---

## 四、协同流程（分阶段）

### 阶段 0：当前（仅有 Cursor，DevAgent 未实现）

- **你**：在 Cursor 里说“按 TECH_IMPLEMENTATION 下一步”或“实现配置加载与 Storage”。
- **我（Cursor）**：按 WORKLOG 与 TECH_IMPLEMENTATION §10 顺序，实现一小步（如配置加载），运行测试（若已有），更新 WORKLOG 或 迭代清单。
- **迭代清单**：在仓库中维护一份 **`docs/planning/next-iteration.md`**（或 在 WORKLOG 末尾写“下一步”），记录：已完成、进行中、待办。每次会话可从“待办”里取一项由 Cursor 完成。
- 这样已经是在做**持续的、有记录的迭代**；等 DevAgent 实现后，它的输出会变成“待办”的重要来源。

### 阶段 1：DevAgent 已实现，只产出建议不自动改主代码

- **DevAgent**：按配置定时或按需运行；跑测试；若失败则写 `dev_agent/output/failures/xxx.md` 并更新 `latest_run.json`；若做搜索联想则写 `dev_agent/output/search_ideas/xxx.md`；若有改进想法则写 `dev_agent/output/suggestions/xxx.md`。
- **你**：在 Cursor 里说“根据 DevAgent 最新输出处理一下”或“先修失败再实现第一条建议”。
- **我（Cursor）**：读取 `dev_agent/output/latest_run.json` 及对应 failures/suggestions；先修失败（保证运行成功、测试通过），再按你选的建议实现；实现后跑测试，更新 WORKLOG；可选在建议文件末尾写“已由 Cursor 于 YYYY-MM-DD 处理”。

### 阶段 2：DevAgent 可生成补丁，仍由 Cursor 审查后应用

- **DevAgent**：在建议基础上可生成 `patches/suggested_xxx.patch` 与 `suggested_xxx_summary.md`。
- **你**：在 Cursor 里说“审查并应用 dev_agent/output/patches 下最新补丁”。
- **我（Cursor）**：读补丁与摘要，解释影响范围；若你同意则应用补丁，跑测试；通过则保留，否则回滚并可在 failures 或 suggestions 中留记录供 DevAgent 下一轮参考。

### 阶段 3：闭环（Cursor 产出下一步计划 → DevAgent 转述 → 循环直到功能完成）

- **第一个任务开始后**：Cursor 完成本批任务后**产出「下一步计划」**，写入 **`dev_agent/output/next_plan.md`**。
- DevAgent 再次运行（定时或按需）：跑测试；**读取 next_plan.md**，将该计划写入 **cursor_tasks.md**（转述给 Cursor）；并追加本次运行待办（先修失败等）。
- Cursor 打开后读 cursor_tasks：**先按「下一步计划」执行，再处理本次运行待办**；完成后再次写入 next_plan.md。**循环直到功能测试通过、所有功能完成**。

---

## 五、你可以怎么用（一句话版）

- **现在**：在 Cursor 里说“按 WORKLOG 和 TECH_IMPLEMENTATION 的下一步，实现配置加载”或“维护一份 [planning/next-iteration.md](../planning/next-iteration.md) 并完成第一项”，我会按文档实现并跑测试，实现**和你一起的自我迭代**。
- **第一个任务开始后**：你说“根据 dev_agent/output/cursor_tasks 处理一下”，我会**先按「下一步计划」推进，再处理本次运行待办**；完成后请产出新的「下一步计划」写入 **`dev_agent/output/next_plan.md`**，供下一轮 DevAgent 转述。**循环直到功能测试通过、所有功能完成**。

---

## 六、建议的下一步（立即可做）

1. **创建 `dev_agent/output/` 目录结构**（含 README 说明用途），并加入 `.gitignore` 中可选条目（若不想把每次运行报告都提交，可忽略 `output/failures/` 等；若想留痕则提交）。
2. **创建 `docs/planning/next-iteration.md`**：按 TECH_IMPLEMENTATION §10 把“配置与存储 → Context → 单 Agent 壳 → …”拆成可勾选的小任务，第一项即“实现配置加载（YAML）与 Storage 抽象（内存版）”。
3. **本会话或下一句**：你直接说“按 `docs/planning/next-iteration.md` 第一项开始实现”，我从配置加载与 Storage 抽象做起，并在完成后更新迭代清单与 WORKLOG。

这样你就有了“Cursor + 迭代清单”的即时自我迭代；等 DevAgent 实现后，只需让它把输出写到 `dev_agent/output/`，我们就可以在 Cursor 里按同一套流程处理它的建议，完成**Cursor 与 DevAgent 协同的自我迭代**。
