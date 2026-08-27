"""
DevAgent 输出写入：写 latest_run.json、failures/*.md、suggestions/*.md。
与 docs/guides/cursor-and-devagent-workflow.md §3.1、§3.2 一致，供 Cursor 读取。
"""
import json
from pathlib import Path
from datetime import datetime


def get_output_root(project_root: Path) -> Path:
    return project_root / "dev_agent" / "output"


def write_latest_run(
    project_root: Path,
    ok: bool,
    test_summary: str,
    suggestions_count: int = 0,
    failure_report: str | None = None,
) -> Path:
    """写入 dev_agent/output/latest_run.json。"""
    root = get_output_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    data = {
        "ok": ok,
        "test_summary": test_summary,
        "suggestions_count": suggestions_count,
        "failure_report": failure_report,
    }
    path = root / "latest_run.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def write_failure_report(project_root: Path, content: str) -> Path:
    """写入 dev_agent/output/failures/YYYY-MM-DD_HH-mm.md，返回相对 output 的路径（供 latest_run.json 引用）。"""
    root = get_output_root(project_root)
    failures_dir = root / "failures"
    failures_dir.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("%Y-%m-%d_%H-%M") + ".md"
    path = failures_dir / name
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return Path("failures") / name


def write_suggestion(
    project_root: Path,
    title: str,
    type_: str,
    description: str,
    files_or_modules: list[str] | None = None,
    priority: str | None = None,
) -> Path:
    """写入 dev_agent/output/suggestions/YYYY-MM-DD_HH-mm.md，与 Cursor 约定格式一致。"""
    root = get_output_root(project_root)
    suggestions_dir = root / "suggestions"
    suggestions_dir.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("%Y-%m-%d_%H-%M") + ".md"
    path = suggestions_dir / name
    lines = [
        f"# {title}",
        "",
        f"- **类型**: {type_}",
        f"- **描述**: {description}",
    ]
    if files_or_modules:
        lines.append(f"- **涉及文件/模块**: {', '.join(files_or_modules)}")
    if priority:
        lines.append(f"- **优先级**: {priority}")
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def read_next_plan(project_root: Path) -> str | None:
    """
    读取 dev_agent/output/next_plan.md：Cursor 上次产出的「下一步计划」。
    若不存在或为空则返回 None。
    """
    root = get_output_root(project_root)
    path = root / "next_plan.md"
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8").strip()
        return content if content else None
    except Exception:
        return None


def write_cursor_tasks(
    project_root: Path,
    tasks: list[dict],
    plan_content: str | None = None,
) -> Path:
    """
    写入 dev_agent/output/cursor_tasks.md：当前「要 Cursor 干的活」清单。
    若 plan_content 存在（Cursor 上次产出的下一步计划），则写在最前，由 DevAgent 转述给 Cursor；
    再写本次运行待办（先修失败、再跑测试等）。持续循环直到功能测试通过、所有功能完成。
    tasks: [{"action": "fix_failures", "path": "failures/xxx.md", "title": "先修失败"}, ...]
    """
    root = get_output_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "cursor_tasks.md"
    lines = [
        "# 待 Cursor 处理（DevAgent 转述：含 Cursor 上次产出的下一步计划 + 本次运行待办）",
        "",
        "**自我迭代原则**：只有运行成功、测试通过的修改才保留；若本次修改导致测试未通过，请根据 failures 修复或回滚后再继续。",
        "",
        "请按顺序执行：**先按「下一步计划」推进，再处理本次运行待办**；完成后请产出新的「下一步计划」写入 `dev_agent/output/next_plan.md`，供下一轮 DevAgent 转述。循环直到功能测试通过、所有功能完成。",
        "",
        "---",
        "",
    ]
    if plan_content:
        lines.append("## 下一步计划（由 Cursor 上次产出，DevAgent 转述）")
        lines.append("")
        lines.append(plan_content)
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## 本次运行待办")
    lines.append("")
    for i, t in enumerate(tasks, 1):
        title = t.get("title", t.get("action", ""))
        rel_path = t.get("path", "")
        lines.append(f"### {i}. {title}")
        if rel_path:
            lines.append(f"- 路径: `dev_agent/output/{rel_path}`")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
