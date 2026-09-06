"""§6.9 设定讨论种子（synopsis）注入单测：`_prompt_author_intent_for_setting_research` 带 seed。"""
import pytest

from src.author_loop.design_phase import _prompt_author_intent_for_setting_research


class _Session:
    def __init__(self, replies):
        self._replies = list(replies)
        self.digests = []

    def read_line(self, prompt):
        return self._replies.pop(0) if self._replies else ""

    def record_round_digest(self, **kw):
        self.digests.append(kw)


def test_seed_merged_when_author_gives_idea():
    s = _Session(["硬科幻，火星官场斗争", ""])  # idea 后跟 genre 输入
    ref, genre = _prompt_author_intent_for_setting_research(
        s, genre="", theme="未命名世界", seed="近未来火星殖民从严"
    )
    assert "近未来火星殖民从严" in ref
    assert "硬科幻，火星官场斗争" in ref  # 作者 idea 并入 seed


def test_seed_used_when_author_skips_idea():
    s = _Session(["", ""])  # idea 空 + genre 空
    ref, genre = _prompt_author_intent_for_setting_research(
        s, genre="", theme="未命名世界", seed="近未来火星殖民从严"
    )
    assert ref == "近未来火星殖民从严"


def test_seed_none_falls_back_placeholder():
    s = _Session(["", ""])
    ref, genre = _prompt_author_intent_for_setting_research(
        s, genre="科幻", theme="未命名世界", seed=None
    )
    assert "作者暂未逐条说明剧情" in ref


def test_run_design_phase_reference_initialized_from_synopsis(tmp_path, monkeypatch):
    """run_design_phase(synopsis=...) 首轮 agent.run 的 reference 含该 synopsis（经 seed 并入）。"""
    from src.author_loop import design_phase as dp

    captured = {}

    class _Agent:
        def __init__(self, output_dir):  # noqa: D401
            pass

        def run(self, **kw):
            captured["reference"] = kw.get("reference")
            raise SystemExit("seed-ref")  # 中断主循环（不被 except Exception 捕获）

    monkeypatch.setattr(dp, "SettingResearchAgent", _Agent)
    monkeypatch.setattr(
        dp, "_prompt_author_intent_for_setting_research", lambda s, *, genre, theme, seed=None: ("SEED-LINE", "科幻")
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    novel_root = tmp_path / "data" / "novels" / "alpha"
    novel_root.mkdir(parents=True, exist_ok=True)
    (novel_root / "config").mkdir(parents=True, exist_ok=True)
    # special_settings_config_dir 要求已绑定 current_novel
    import yaml

    (config_dir / "current_novel.yaml").write_text(
        yaml.safe_dump({"slug": "alpha", "title": "火星", "root": str(novel_root), "provisional": False}, allow_unicode=True),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit):
        dp.run_design_phase(
            config_dir,
            {"agents": {"characters": {"enabled_ids": []}, "scopes": {"enabled_ids": []}}},
            {"world": {}},  # 空 world → 触发首轮意图询问（带 seed）
            {"characters": []},
            input_fn=lambda _: "",
            synopsis="近未来火星殖民从严",
        )
    assert "近未来火星殖民从严" in captured.get("reference", "")