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


def test_bootstrap_idea_persist_when_no_synopsis(tmp_path):
    """无简介种子而作者在首次设定引导补填核心 → 持久化为 meta.yaml synopsis（供面板/建议读取）。"""
    import yaml

    from src.author_loop.novel_identity import read_synopsis

    novel_root = tmp_path / "data" / "novels" / "alpha"
    novel_root.mkdir(parents=True, exist_ok=True)
    # 已有 meta.yaml 但尚无 synopsis（相当于"未填简介"）
    (novel_root / "meta.yaml").write_text(
        yaml.safe_dump({"slug": "alpha", "title": "火星"}, allow_unicode=True), encoding="utf-8"
    )

    s = _Session(["硬科幻，火星官场斗争", ""])  # idea 后跟 genre 输入
    ref, _genre = _prompt_author_intent_for_setting_research(
        s, genre="", theme="未命名世界", seed=None, novel_root=novel_root
    )
    assert "硬科幻，火星官场斗争" in ref
    assert read_synopsis(novel_root) == "硬科幻，火星官场斗争"


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
        dp, "_prompt_author_intent_for_setting_research", lambda s, *, genre, theme, seed=None, **kw: ("SEED-LINE", "科幻")
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


def test_run_design_phase_regen_without_synopsis_prompts_seed(tmp_path, monkeypatch):
    """作者确认重新生成（覆盖现有设定）且无 synopsis 时，先引导填一句简介作种子并持久化。"""
    import yaml

    from src.author_loop import design_phase as dp

    captured = {}
    replies = iter(["n", "近未来火星殖民从严"])  # 覆盖确认=n(重新生成), 再填简介种子

    class _Agent:
        def __init__(self, output_dir):  # noqa: D401
            pass

        def run(self, **kw):
            captured["reference"] = kw.get("reference")
            raise SystemExit("regen-ref")  # 中断主循环

    monkeypatch.setattr(dp, "SettingResearchAgent", _Agent)
    # 让「检测已有设定」成立，从而触发「是否保留现有设定」覆盖确认
    monkeypatch.setattr(dp, "_has_existing_setting_output", lambda config_dir: True)
    monkeypatch.setattr(
        dp, "_prompt_author_intent_for_setting_research", lambda s, *, genre, theme, seed=None: ("SEED-LINE", "科幻")
    )

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    novel_root = tmp_path / "data" / "novels" / "alpha"
    novel_root.mkdir(parents=True, exist_ok=True)
    (novel_root / "config").mkdir(parents=True, exist_ok=True)
    (config_dir / "current_novel.yaml").write_text(
        yaml.safe_dump({"slug": "alpha", "title": "火星", "root": str(novel_root), "provisional": False}, allow_unicode=True),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        dp.run_design_phase(
            config_dir,
            {"agents": {"characters": {"enabled_ids": []}, "scopes": {"enabled_ids": []}}},
            {"world": {"name": "火星", "era": "近未来"}},  # 世界已填 → 不触发意图询问，直接核对重建种子
            {"characters": []},
            input_fn=lambda _: next(replies),
            synopsis=None,  # 无简介种子
        )
    assert captured.get("reference") == "近未来火星殖民从严"
    # 简介应已持久化到 meta.yaml，供「设定讨论/设定情况」面板读取
    from src.author_loop.novel_identity import read_synopsis

    assert read_synopsis(novel_root) == "近未来火星殖民从严"