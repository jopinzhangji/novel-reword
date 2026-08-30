"""
DevAgent 主逻辑：加载配置 → 运行测试 → 写输出（latest_run、失败报告、建议、cursor_tasks）→ 供 Cursor 消费。
自我迭代 = 定时运行本逻辑（跑测试 + 产出「要 Cursor 干的活」cursor_tasks.md），用户定期在 Cursor 里根据 cursor_tasks 让 Cursor 干活。
与 TECH_IMPLEMENTATION §3.6、`docs/guides/cursor-and-devagent-workflow.md` 一致。
"""
from pathlib import Path

from .config import load_dev_agent_config, PROJECT_ROOT
from .runner import run_test_command, RunResult
from .output_writer import (
    get_output_root,
    write_latest_run,
    write_failure_report,
    write_suggestion,
    read_next_plan,
    write_cursor_tasks,
)
from . import search_ideas as search_ideas_mod


def run_once(config_path: Path | None = None, project_root: Path | None = None) -> bool:
    """
    执行一次自我迭代循环：
    1. 加载 dev_agent 配置；
    2. 若未启用则直接返回 True；
    3. 在项目根下执行 test_command；
    4. 写 latest_run.json（ok=退出码==0）；
    5. 若失败则写 failures/*.md 与 suggestions/*.md，供 Cursor 处理。
    返回：测试是否通过（exit_code == 0）。
    """
    root = project_root or PROJECT_ROOT
    cfg = load_dev_agent_config(config_path)
    if not cfg.get("enabled", False):
        return True
    cmd = (cfg.get("test_command") or "").strip()
    if not cmd:
        write_latest_run(root, False, "no test_command configured", 0, None)
        return False

    result = run_test_command(cmd, root)
    ok = result.exit_code == 0
    failure_report_rel: str | None = None
    suggestions_count = 0
    cursor_tasks: list[dict] = []

    if not ok:
        # 失败报告：stdout + stderr，便于 Cursor 定位
        report_content = _build_failure_report(result)
        rel = write_failure_report(root, report_content)
        failure_report_rel = str(rel)
        # 建议：请 Cursor 先修失败
        write_suggestion(
            root,
            title="修复失败测试",
            type_="fix",
            description="测试未通过，请根据 dev_agent/output/failures/ 下最新报告修复后重新运行测试。",
            files_or_modules=["tests/"],
            priority="high",
        )
        suggestions_count = 1
        cursor_tasks.append({
            "action": "fix_failures",
            "path": failure_report_rel,
            "title": "先修失败：见 failures 下最新报告",
        })
        cursor_tasks.append({
            "action": "run_tests_after_fix",
            "path": "",
            "title": "修复后重新运行测试：python -m pytest tests/ -v",
        })
    else:
        cursor_tasks.append({
            "action": "check_suggestions",
            "path": "suggestions/",
            "title": "可选：查看 suggestions 下是否有待实现的建议",
        })
        if cfg.get("search_ideas_enabled"):
            ideas = search_ideas_mod.run_search_ideas(root, cfg)
            for idea in ideas:
                cursor_tasks.append({
                    "action": "search_ideas",
                    "path": idea.get("path", ""),
                    "title": idea.get("title", "可选：根据 search_ideas 完善主程序或自身"),
                })

    write_latest_run(
        root,
        ok=ok,
        test_summary=result.summary,
        suggestions_count=suggestions_count,
        failure_report=failure_report_rel,
    )
    # 读取 Cursor 上次产出的下一步计划（若有），将该计划 + 本次运行待办 写入 cursor_tasks，由 DevAgent 转述给 Cursor；循环直到功能测试通过、全部完成
    plan_content = read_next_plan(root)
    write_cursor_tasks(root, cursor_tasks, plan_content=plan_content)
    return ok


def _build_failure_report(result: RunResult) -> str:
    lines = [
        "# 测试运行失败",
        "",
        f"**摘要**: {result.summary}",
        "",
        "## stdout",
        "```",
        result.stdout.strip() or "(空)",
        "```",
        "",
        "## stderr",
        "```",
        result.stderr.strip() or "(空)",
        "```",
    ]
    return "\n".join(lines)
