"""
DevAgent 搜索与联想扩展点：产出「小说可能涉及的内容」与改进点，供完善主程序或自身。
与 TECH_IMPLEMENTATION §3.6（2）一致。可基于设定研究产出（读 YAML 或调用设定研究 Agent）产出真实条目。
"""
import yaml
from pathlib import Path

from .output_writer import get_output_root


def run_search_ideas(project_root: Path, config: dict) -> list[dict]:
    """
    执行搜索与联想。config 为 dev_agent 配置段。
    - 若 config 含 setting_research_output_path：读取该 YAML，从 power_system/level_system 产出 search_ideas 下真实条目。
    - 若含 theme 与 runtime_config_path：调用设定研究 Agent 产出 YAML 再同上。
    - 否则写占位说明到 search_ideas/ 并返回占位条目。
    返回 [{"title": str, "path": str}, ...]，path 为相对 dev_agent/output 的路径。
    """
    root = get_output_root(project_root)
    ensure_search_ideas_readme(project_root)
    ideas_dir = root / "search_ideas"

    # 1) 已有设定研究产出：直接读 YAML 生成条目
    setting_yaml_path = _resolve_setting_research_output_path(project_root, config)
    if setting_yaml_path and setting_yaml_path.is_file():
        entries = _ideas_from_setting_yaml(setting_yaml_path, ideas_dir)
        if entries:
            return entries

    # 2) 配置了 theme + runtime_config_path：调用设定研究 Agent 再生成条目
    theme = (config.get("search_ideas_theme") or config.get("theme") or "").strip()
    runtime_config_path = config.get("runtime_config_path") or config.get("search_ideas_runtime_config_path")
    if theme and runtime_config_path:
        path = _run_setting_research_and_get_yaml_path(project_root, config, ideas_dir)
        if path and path.is_file():
            entries = _ideas_from_setting_yaml(path, ideas_dir)
            if entries:
                return entries

    # 3) 占位
    return _write_placeholder_ideas(ideas_dir)


def _resolve_setting_research_output_path(project_root: Path, config: dict) -> Path | None:
    """解析 config 中的 setting_research_output_path，返回绝对路径；未配置或不存在返回 None。"""
    raw = config.get("setting_research_output_path") or config.get("search_ideas_setting_yaml")
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = project_root / p
    return p if p.is_file() else None


def _ideas_from_setting_yaml(yaml_path: Path, ideas_dir: Path) -> list[dict]:
    """
    从设定研究产出 YAML 读取 power_system、level_system，写入 ideas_dir 下 md 文件，返回条目列表。
    """
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return []
    if not isinstance(data, dict):
        return []

    entries = []
    # power_system
    ps = data.get("power_system")
    if isinstance(ps, dict):
        md = _format_power_system_md(ps)
        out_path = ideas_dir / "power_system.md"
        out_path.write_text(md, encoding="utf-8")
        entries.append({"title": "战力体系（设定研究）", "path": "search_ideas/power_system.md"})
    elif isinstance(ps, str):
        out_path = ideas_dir / "power_system.md"
        out_path.write_text(f"# 战力体系\n\n{ps}", encoding="utf-8")
        entries.append({"title": "战力体系（设定研究）", "path": "search_ideas/power_system.md"})

    # level_system
    ls = data.get("level_system")
    if isinstance(ls, dict):
        md = _format_level_system_md(ls)
        out_path = ideas_dir / "level_system.md"
        out_path.write_text(md, encoding="utf-8")
        entries.append({"title": "境界/等级体系（设定研究）", "path": "search_ideas/level_system.md"})
    elif isinstance(ls, str):
        out_path = ideas_dir / "level_system.md"
        out_path.write_text(f"# 境界/等级体系\n\n{ls}", encoding="utf-8")
        entries.append({"title": "境界/等级体系（设定研究）", "path": "search_ideas/level_system.md"})

    if not entries:
        return []
    return entries


def _format_power_system_md(ps: dict) -> str:
    """将 power_system 转为 markdown 摘要。"""
    lines = ["# 战力体系（设定研究）", ""]
    lines.append(f"**{ps.get('name', '战力体系')}**")
    if ps.get("description"):
        lines.append("")
        lines.append(ps["description"])
    if ps.get("levels"):
        lines.append("")
        lines.append("## 层级/等级")
        for i, lv in enumerate(ps.get("levels", []) if isinstance(ps.get("levels"), list) else []):
            if isinstance(lv, dict):
                lines.append(f"- {lv.get('name', lv.get('id', str(i)))}")
            else:
                lines.append(f"- {lv}")
    return "\n".join(lines)


def _format_level_system_md(ls: dict) -> str:
    """将 level_system 转为 markdown 摘要。"""
    lines = ["# 境界/等级体系（设定研究）", ""]
    lines.append(f"**{ls.get('name', '境界体系')}**")
    if ls.get("description"):
        lines.append("")
        lines.append(ls["description"])
    levels = ls.get("levels")
    if isinstance(levels, list) and levels:
        lines.append("")
        lines.append("## 境界列表")
        for lv in levels:
            if isinstance(lv, dict):
                name = lv.get("name") or lv.get("id") or ""
                order = lv.get("order", "")
                lines.append(f"- {name}" + (f" (order={order})" if order != "" else ""))
            else:
                lines.append(f"- {lv}")
    return "\n".join(lines)


def _run_setting_research_and_get_yaml_path(
    project_root: Path, config: dict, ideas_dir: Path
) -> Path | None:
    """调用设定研究 Agent 产出 YAML，返回产出文件路径；失败返回 None。"""
    runtime_config_path = config.get("runtime_config_path") or config.get("search_ideas_runtime_config_path")
    if not runtime_config_path:
        return None
    path = Path(runtime_config_path)
    if not path.is_absolute():
        path = project_root / path
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            full = yaml.safe_load(f) or {}
    except Exception:
        return None
    runtime_config = {**full.get("framework", {}), **full.get("runtime", {})}
    theme = (config.get("search_ideas_theme") or config.get("theme") or "").strip()
    genre = (config.get("search_ideas_genre") or config.get("genre") or "").strip()
    reference = config.get("search_ideas_reference") or config.get("reference")

    from src.agents.setting_research.agent import SettingResearchAgent

    agent = SettingResearchAgent()
    out_dir = ideas_dir.parent / "setting_research_cache"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        result_path = agent.run(
            theme=theme, genre=genre, reference=reference, output_dir=out_dir, runtime_config=runtime_config
        )
        return result_path
    except Exception:
        return None


def _write_placeholder_ideas(ideas_dir: Path) -> list[dict]:
    """写占位说明到 search_ideas/，返回占位条目。"""
    placeholder_path = ideas_dir / "placeholder.md"
    content = """# 搜索与联想（占位）

- **说明**：此处为 DevAgent §3.6「搜索与联想」扩展点。可配置 setting_research_output_path 或 theme + runtime_config_path，从设定研究产出战力/境界等真实条目。
- **当前**：未配置设定研究来源，仅占位；Cursor 可忽略或据此补充 tests/ 与文档。
"""
    placeholder_path.write_text(content, encoding="utf-8")
    return [{"title": "搜索与联想占位（可接入设定研究）", "path": "search_ideas/placeholder.md"}]


def ensure_search_ideas_readme(project_root: Path) -> Path:
    """确保 search_ideas 目录下有 README.md（可被 git 保留），说明目录用途。"""
    root = get_output_root(project_root)
    ideas_dir = root / "search_ideas"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    readme = ideas_dir / "README.md"
    if not readme.is_file():
        readme.write_text(
            "# search_ideas\n\nDevAgent 搜索与联想产出目录（§3.6）。可放置类型套路、设定要素等改进点，供 Cursor 完善主程序或自身。\n",
            encoding="utf-8",
        )
    return readme
