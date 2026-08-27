"""
DevAgent 入口：python -m src.agents.dev
执行一次自我迭代（运行测试 → 写 output → 供 Cursor 读取）。
"""
import sys
from .agent import run_once
from .config import PROJECT_ROOT


def main() -> int:
    ok = run_once(project_root=PROJECT_ROOT)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
