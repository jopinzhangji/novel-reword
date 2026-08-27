# DevAgent 输出目录

本目录由 **DevAgent** 写入，供 **Cursor（与用户）** 读取并据此实现/修复/审查，实现协同自我迭代。**定时运行 DevAgent** 后，此处会产出「要 Cursor 干的活」清单，供你在 Cursor 里说「根据 dev_agent/output/cursor_tasks 处理一下」让 Cursor 干活。

- **next_plan.md**：**由 Cursor 产出**的「下一步计划」；DevAgent 再次运行时读取并写入 cursor_tasks 转述给 Cursor，形成闭环直到功能完成。
- **cursor_tasks.md**：**由 DevAgent 产出**的「要 Cursor 干的活」（含 Cursor 上次的下一步计划 + 本次运行待办），Cursor 按此执行并再写 next_plan.md
- **latest_run.json**：最近一次运行摘要（测试是否通过、建议条数、失败报告路径等）
- **failures/**：测试或运行失败时的报告
- **suggestions/**：改进建议（功能、重构、测试补充等）
- **patches/**：DevAgent 生成的补丁与摘要（可选）
- **search_ideas/**：搜索与联想产出的改进点

详见 [docs/guides/cursor-and-devagent-workflow.md](../../docs/guides/cursor-and-devagent-workflow.md)（含「如何定时运行 DevAgent」）。
