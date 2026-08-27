

"""
独立脚本：使用合并后的 runtime 配置中的 LLM（默认 system_config.yaml + example_runtime.yaml）进行简单对话测试。
在项目根目录执行：python test_llm_chat.py
支持单轮问答；输入空行发送，输入 quit/exit 退出。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_runtime_config
from src.llm import get_llm_provider


def main() -> None:
    config_dir = PROJECT_ROOT / "config"
    runtime = load_runtime_config(config_dir)
    framework = runtime.get("framework") or {}
    llm_key = (framework.get("llm") or "dummy").strip().lower()

    print("加载配置 LLM:", llm_key)
    try:
        provider = get_llm_provider(runtime)
        print("Provider:", type(provider).__name__)
    except Exception as e:
        print("获取 LLM 失败:", e)
        sys.exit(1)

    if type(provider).__name__ == "DummyLLM":
        print("当前为 DummyLLM，不会调用真实 API。如需通义等，请修改 config/example_runtime.yaml 中 framework.llm 并设置对应环境变量。")
    print("-" * 40)
    print("输入内容后回车发送，输入 quit 或 exit 退出。")
    print("-" * 40)

    while True:
        try:
            line = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break
        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            print("再见。")
            break
        try:
            reply = provider.generate(line)
            print("LLM:", reply)
        except Exception as e:
            print("LLM 调用异常:", e)
        print()


if __name__ == "__main__":
    main()
