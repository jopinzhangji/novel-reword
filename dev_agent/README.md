# 开发程序 Agent（DevAgent）

专为**小说主程序自我迭代**服务，与主程序保持耦合。职责见 [TECH_IMPLEMENTATION.md](../TECH_IMPLEMENTATION.md) §3.4–§3.6。

- **output/**：DevAgent 写入的运行摘要、失败报告、建议、补丁、搜索联想产出；供 **Cursor** 与用户读取并据此实现/修复/审查。
- **config/**（可选）：DevAgent 自身配置，若与主项目 `config/` 分离时可放此处。

与 Cursor 的协同流程见 [docs/guides/cursor-and-devagent-workflow.md](../docs/guides/cursor-and-devagent-workflow.md)。
