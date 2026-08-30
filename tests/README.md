# 配套测试程序

供 **DevAgent（开发程序 Agent）** 与 CI 使用：优化前后运行测试以验证行为、避免回归。

- **unit/**：单元测试
  - **test_dev_agent_config.py**：DevAgent 配置契约（dev_agent.enabled/trigger/test_command/scope 等）
  - **test_dev_agent_output.py**：DevAgent 输出目录契约（output 结构存在、可写、latest_run.json 格式）
  - 其他：配置加载、Storage、Context、单 Agent 壳等（待补充）
- **integration/**：集成测试（编排器 + 单回合/多回合流程）
- 运行：`python3 -m pytest tests/ -v`（或 `.venv/bin/python -m pytest tests/ -v`；激活虚拟环境后 `pytest tests/ -v` 亦可）
