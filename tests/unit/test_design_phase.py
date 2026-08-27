"""
开书前设定阶段单元测试：run_design_phase 的 y/e/c/p 分支与返回值（DESIGN §6.6 输入想法与讨论）。
"""
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

from src.config import is_world_config_empty
from src.author_loop.design_phase import (
    _design_exit_blocked_by_incomplete_world,
    _direction_to_md,
    _format_characters_summary,
    _format_scopes_summary,
    _format_special_summary,
    _format_world_summary,
    run_design_phase,
)


def _ensure_bound_novel(config_dir: Path) -> Path:
    """设定研究产出要求已绑定 current_novel；测试中在配置目录下挂接最小作品目录。"""
    novel_root = config_dir / "_test_novel"
    (novel_root / "config").mkdir(parents=True, exist_ok=True)
    (config_dir / "current_novel.yaml").write_text(
        yaml.dump({"root": str(novel_root.resolve())}, allow_unicode=True),
        encoding="utf-8",
    )
    return novel_root


def _minimal_runtime():
    """单测关闭入口分类与 digest 的 LLM，避免误调真实 API 卡住。"""
    return {
        "runtime": {
            "setting_research": {"enabled": True, "trigger": "design_only"},
            "author_interaction": {
                "intent_classify_llm": False,
                "digest_llm_compress": False,
            },
        },
        "agents": {
            "characters": {"enabled_ids": ["a"]},
            "scopes": {"enabled_ids": ["s1"]},
        },
    }


def _minimal_world():
    return {
        "world": {"name": "测试世界", "era": "测试时代", "rules": []},
        "time": {"start": "测试元年"},
        "scopes": [{"id": "s1", "name": "范围1", "description": "描述", "locations": [], "links": []}],
    }


def _empty_name_world():
    """世界名为空（初稿占位），触发设定前题材引导。"""
    return {
        "world": {"name": "", "era": "", "rules": []},
        "time": {"start": ""},
        "scopes": [{"id": "s1", "name": "范围1", "description": "描述", "locations": [], "links": []}],
    }


def _minimal_characters():
    return {
        "characters": [
            {"id": "a", "name": "角色A", "role": "主角", "traits": [], "background": "背景", "goals": {"short": "", "long": ""}},
        ],
    }


def test_design_phase_confirm_returns_false(tmp_path):
    """输入 y 确认时返回 False（未编辑）。"""
    _ensure_bound_novel(tmp_path)
    runtime = _minimal_runtime()
    world = _minimal_world()
    chars = _minimal_characters()
    edited = run_design_phase(
        tmp_path, runtime, world, chars,
        input_fn=lambda _: "y",
    )
    assert edited is False


def test_design_phase_supplement_then_confirm_returns_false(tmp_path):
    """选 c 输入想法、选 n 不讨论，再 y 时返回 False（仅补充，下一轮会重生成）。"""
    _ensure_bound_novel(tmp_path)
    inputs = ["c", "末法时代战力崩坏", "n", "y"]
    it = iter(inputs)
    input_fn = lambda _: next(it, "y")
    runtime = _minimal_runtime()
    world = _minimal_world()
    chars = _minimal_characters()
    edited = run_design_phase(tmp_path, runtime, world, chars, input_fn=input_fn)
    assert edited is False


def test_design_phase_edit_then_confirm_returns_true(tmp_path):
    """输入 e 编辑后继续再 y 时返回 True。"""
    _ensure_bound_novel(tmp_path)
    (tmp_path / "example_world.yaml").write_text(yaml.dump(_minimal_world(), allow_unicode=True), encoding="utf-8")
    (tmp_path / "example_characters.yaml").write_text(yaml.dump(_minimal_characters(), allow_unicode=True), encoding="utf-8")
    inputs = ["e", "", "y"]
    it = iter(inputs)
    input_fn = lambda _: next(it, "y")
    runtime = _minimal_runtime()
    world = _minimal_world()
    chars = _minimal_characters()
    edited = run_design_phase(tmp_path, runtime, world, chars, input_fn=input_fn)
    assert edited is True


def test_design_phase_direction_then_confirm_returns_false(tmp_path):
    """选 c 输入想法、选 y 多轮讨论，输入 满意 后归纳，再 y 设定完成时返回 False（未选 e 编辑）。"""
    novel_root = _ensure_bound_novel(tmp_path)
    inputs = ["c", "境界体系相关想法", "y", "满意", "y"]
    it = iter(inputs)
    input_fn = lambda _: next(it, "y")
    with patch("src.author_loop.design_phase.discuss_freely", return_value="（测试回复）"):
        with patch("src.author_loop.design_phase.summarize_and_extract_by_directions", return_value={"power_system": {"name": "测试战力", "description": "测试"}}):
            edited = run_design_phase(
                tmp_path, _minimal_runtime(), _minimal_world(), _minimal_characters(), input_fn=input_fn
            )
    assert edited is False
    # 讨论归纳后应写回小说 config 下设定文件
    assert (novel_root / "config" / "setting_research_output.yaml").is_file()


def test_design_exit_blocked_when_world_name_empty():
    assert _design_exit_blocked_by_incomplete_world("y", _empty_name_world()) is True
    assert _design_exit_blocked_by_incomplete_world("other", _empty_name_world()) is True
    assert _design_exit_blocked_by_incomplete_world("y", _minimal_world()) is False
    assert _design_exit_blocked_by_incomplete_world("c", _empty_name_world()) is False


def test_format_special_summary_includes_chapter_outline():
    """章节大纲类 dict 在摘要中展示章数与示例标题。"""
    special = {
        "genre": "架空",
        "章节大纲": {
            "name": "第一卷",
            "description": "进村阶段",
            "chapters": [
                {"chapter_number": 1, "title": "入山", "summary": "落地"},
                {"chapter_number": 2, "title": "认路", "summary": "熟识"},
            ],
        },
    }
    lines = _format_special_summary(special)
    assert any("章节大纲" in ln and "入山" in ln for ln in lines)


def test_direction_to_md_renders_chapters():
    """大纲方向写入 .md 时带出章节列表。"""
    md = _direction_to_md(
        {
            "name": "全书大纲",
            "description": "总览",
            "chapters": [{"chapter_number": 1, "title": "开场", "summary": "钩子"}],
        }
    )
    assert "## 章节要点" in md
    assert "开场" in md


def test_collect_setting_intent_updates_genre_and_reference(tmp_path):
    """世界名为空时，题材引导函数把说明与 genre 交给 agent（不跑完整 design_phase 主循环）。"""
    from src.author_loop.author_session import AuthorSession
    from src.author_loop import design_phase as dp

    config_dir = tmp_path / "c"
    config_dir.mkdir()
    inputs = iter(["近未来太空悬疑", "科幻"])
    session = AuthorSession(
        config_dir=config_dir,
        project_root=tmp_path,
        runtime_config=_minimal_runtime(),
        input_fn=lambda _: next(inputs),
    )
    ref, g = dp._prompt_author_intent_for_setting_research(
        session, genre="架空", theme="未命名世界"
    )
    assert "太空悬疑" in ref
    assert g == "科幻"


def test_format_world_scopes_chars_use_special_when_yaml_placeholder():
    """world.name 为空时标【待填写】并附设定研究预览；占位 scope/char 标【待填写】且附 reference 预览。"""
    world = {
        "world": {"name": "", "era": "", "rules": []},
        "scopes": [
            {
                "id": "main",
                "name": "主线",
                "description": "（绑定小说目录后由小说级 config 覆盖）",
            }
        ],
    }
    chars = {
        "characters": [
            {
                "id": "protagonist",
                "name": "主角",
                "role": "（绑定小说目录后完善）",
                "background": "（绑定小说目录后完善）",
            }
        ]
    }
    special = {
        "genre": "架空",
        "theme": "青石村物语",
        "reference": "主角穿越到山村，学采药与避雷。",
    }
    wlines = _format_world_summary(world, special)
    assert any("青石村物语" in ln for ln in wlines)
    assert any("架空" in ln for ln in wlines)
    assert any("设定研究" in ln for ln in wlines)
    assert is_world_config_empty(world)

    slines = _format_scopes_summary(world, ["main"], special)
    assert any("主角穿越" in ln for ln in slines)

    clines = _format_characters_summary(chars, ["protagonist"], special)
    assert any("主角穿越" in ln for ln in clines)
    assert any("【待填写】" in ln for ln in clines)


def test_format_scopes_chars_replace_minimal_bootstrap_placeholders():
    """novel_bootstrap._minimal_world / _minimal_characters 的「待设定…」占位也可用 reference 预览。"""
    world = {
        "world": {"name": "", "era": "", "rules": []},
        "scopes": [{"id": "main", "name": "main", "description": "（待设定阶段完善）"}],
    }
    chars = {
        "characters": [
            {
                "id": "a",
                "name": "a",
                "role": "（待设定）",
                "background": "（待设定阶段完善）",
            }
        ]
    }
    ref = "梗概：山村与穿越者。"
    slines = _format_scopes_summary(world, ["main"], {"reference": ref})
    assert any("山村" in ln for ln in slines)
    clines = _format_characters_summary(chars, ["a"], {"reference": ref})
    assert any("山村" in ln for ln in clines)
