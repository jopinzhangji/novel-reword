"""G3 运行时镜头（SDD D12 §4）：override>配置期、校验切换+持久化、镜头提示块重建。"""
from src.runtime.protagonist_switch import (
    ProtagonistContext,
    effective_protagonist,
    format_lens_snippet,
    load_protagonist_context,
    save_protagonist_context,
    switch_protagonist,
)

CHARS = {"characters": [{"id": "li", "name": "李逍", "role": "少主"}, {"id": "mo", "name": "墨音"}]}


def test_effective_config_time_when_no_override():
    pid, name = effective_protagonist({}, CHARS, None)
    assert pid is None and name is None


def test_effective_override_beats_config():
    ctx = ProtagonistContext(protagonist_id="mo", display_name="墨音")
    pid, name = effective_protagonist({"runtime": {"novel_run": {"protagonist_id": "li"}}}, CHARS, ctx)
    assert pid == "mo"  # 运行时 override > 配置期


def test_switch_valid_and_persist(tmp_path):
    ctx = ProtagonistContext()
    pid, name = switch_protagonist(ctx, {}, CHARS, "mo")
    assert ctx.is_override()
    assert pid == "mo" and name == "墨音"
    p = save_protagonist_context(tmp_path, ctx)
    assert p is not None and p.exists()
    loaded = load_protagonist_context(tmp_path)
    assert loaded.protagonist_id == "mo" and loaded.display_name == "墨音"


def test_switch_invalid_noop(tmp_path):
    ctx = ProtagonistContext()
    pid, name = switch_protagonist(ctx, {}, CHARS, "nobody")
    assert pid is None and name is None and not ctx.is_override()
    # 未 override → 不写盘
    assert save_protagonist_context(tmp_path, ctx) is None


def test_format_lens_snippet():
    s = format_lens_snippet("mo", "墨音", CHARS)
    assert "叙事主角：墨音" in s
    assert "李逍" in s and "少主" in s
    assert "不得虚构或替换主角姓名" in s
    assert format_lens_snippet(None, None, CHARS) == ""
    assert format_lens_snippet("mo", "墨音", None) != ""  # 无角色配置仍能生成主角行