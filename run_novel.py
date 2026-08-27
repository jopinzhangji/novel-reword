"""
小说主流程入口：加载配置 → 创建 Orchestrator → 多回合循环（默认 2 回合）。
在项目根执行：python run_novel.py 或 .venv\\Scripts\\python.exe run_novel.py
可选环境变量：MIN_AUTOBOOK_TURNS=3 指定回合数（默认 2）；MIN_AUTOBOOK_LOG_LEVEL=DEBUG 指定日志级别。
"""
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.log_config import setup_logging
from src.orchestrator import Orchestrator
from src.config import get_initial_scene
from src.llm import get_llm_provider


def main() -> None:
    log = setup_logging(PROJECT_ROOT)
    log.info("小说主流程启动（自动写回模式）")

    config_dir = PROJECT_ROOT / "config"
    log.debug("配置目录: %s", config_dir)

    orch = Orchestrator.from_config(config_dir)
    runtime = orch.runtime_config
    framework = runtime.get("framework") or {}
    llm_key = (framework.get("llm") or "dummy").strip().lower()
    try:
        provider = get_llm_provider(runtime)
        log.info("LLM 配置: framework.llm=%s, Provider=%s", llm_key, type(provider).__name__)
    except Exception as e:
        log.warning("获取 LLM Provider 失败（将不影响壳模式运行）: %s", e)

    enabled_char = list(runtime.get("agents", {}).get("characters", {}).get("enabled_ids", []))
    present = [c for c in enabled_char if c in orch.character_agents]
    scene = get_initial_scene(orch.runtime_config, orch.world_config)
    scope_id = scene["scope_id"]
    time_str = scene["time"]
    place = scene["place"]

    log.info("开局场景: scope_id=%s, time=%s, place=%s", scope_id, time_str, place)
    log.info("在场角色: %s (enabled_ids=%s)", present, enabled_char)

    n = int(os.environ.get("MIN_AUTOBOOK_TURNS", "2"))
    n = max(1, min(n, 100))
    log.info("计划执行 %s 回合", n)

    results = orch.run_n_turns(
        n=n,
        scope_id=scope_id,
        time=time_str,
        place=place,
        present_character_ids=present,
    )
    events = orch.storage.get_recent_events(scope_id, k=n)
    log.info("已执行 %s 回合，scope=%s，事件簿共 %s 条。", len(results), scope_id, len(events))


if __name__ == "__main__":
    print("小说主流程（自动写回）启动中...", flush=True)
    try:
        main()
    except Exception as e:
        print(f"运行异常: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
