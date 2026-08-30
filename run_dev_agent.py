"""
DevAgent 入口脚本：在项目根执行 python run_dev_agent.py（Linux：python3；或 .venv/bin/python）
执行一次自我迭代（运行测试 -> 写 dev_agent/output -> 供 Cursor 读取）。
"""
import sys
from pathlib import Path

# 项目根 = 本文件所在目录
PROJECT_ROOT = Path(__file__).resolve().parent

# 将 src 加入 path 以便 import
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.dev.agent import run_once

if __name__ == "__main__":
    ok = run_once(project_root=PROJECT_ROOT)
    sys.exit(0 if ok else 1)
