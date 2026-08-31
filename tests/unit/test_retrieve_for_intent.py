"""M4 retrieve_for_intent：两类意图、长度预算、格式化。"""
import yaml
from pathlib import Path

from src.author_loop.classify_intent import (
    INTENT_DESIGN_COMPLETE,
    INTENT_EDIT_SETTING_FILES,
    INTENT_INPUT_IDEA_DISCUSS,
    INTENT_REVIEW_REVISE,
    INTENT_SAVE_PROGRESS,
)
from src.author_harness.retrieval_registry import (
    DESIGN_MAIN_SETTING_TOOLS,
    INTENT_RETRIEVAL_TOOL_CHAINS,
    MAIN_WRITING_REVIEW_TOOLS,
)
from src.author_harness.prompt_assembler import assemble_retrieval_prompt_block
from src.author_loop.retrieve_for_intent import (
    RETRIEVAL_PROFILE_DESIGN_DISCUSSION,
    RetrievalSnippet,
    compress_retrieval_snippets,
    format_snippets_for_prompt,
    load_compress_settings,
    retrieve_for_intent,
    retrieve_max_total_chars,
)


# --- CC-c：契约驱动确定性结构保留压缩（SDD D8 §6.1） ---
def _snippets_small():
    return [
        RetrievalSnippet("world.yaml",
                         "## 世界设定\n一个很长的世界背景描述会一直延续直到超过阈值触发压缩它要占不少字符好让总量超限被裁剪\n* 特性甲 内容\n* 特性乙 内容"),
        RetrievalSnippet("book/setting#摘要",
                         "## 关键要点\n第二块内容也比较长用来确保总长超阈并验证多块各自被结构保留裁剪兼顾来源标签拿捏到位"),
        RetrievalSnippet("internet/todo", "## 外网摘要\n第三块较短的摘录"),
    ]


def _on_settings(proj: dict | None = None) -> dict:
    cc = proj or {}
    return {"runtime": {"author_interaction": {"context_compress": {"enabled": True, **cc}}}}


def test_compress_enabled_over_threshold_reduces_and_keeps_chunks():
    snips = _snippets_small()
    settings = load_compress_settings(_on_settings({"threshold_ratio": 0.75, "target_ratio": 0.5}))
    cap = 60
    contract = None
    out = compress_retrieval_snippets(snips, cap, contract=contract, settings=settings)
    # 语料总量 150 > 0.75×60=45 → 触发；压到 ≤ 0.5×60=30（硬保险后亦 ≤cap）
    assert sum(len(s.text) for s in out) <= cap
    # 仍分块、来源标签保留
    assert len(out) == 3
    assert [s.source for s in out] == ["world.yaml", "book/setting#摘要", "internet/todo"]
    # 每块都保留标题骨架（非单段结论）
    assert out[0].text.startswith("## 世界设定")
    assert out[1].text.startswith("## 关键要点")
    assert out[0].truncated and out[1].truncated


def test_compress_disabled_is_identity():
    snips = _snippets_small()
    settings = load_compress_settings({})  # enabled 默认 false
    out = compress_retrieval_snippets(snips, 60, contract=None, settings=settings)
    assert out is snips


def test_compress_under_threshold_is_identity_even_enabled():
    snips = _snippets_small()
    settings = load_compress_settings(_on_settings())
    out = compress_retrieval_snippets(snips, 10000, contract=None, settings=settings)
    assert out == snips  # 未超阈：无阈行为不变


def test_load_compress_settings_defaults_and_override():
    d = load_compress_settings({})
    assert d == {"enabled": False, "threshold_ratio": 0.75, "target_ratio": 0.5}
    o = load_compress_settings(_on_settings({"threshold_ratio": 0.6, "target_ratio": 0.4}))
    assert o["enabled"] is True and o["threshold_ratio"] == 0.6 and o["target_ratio"] == 0.4


def _bind_novel(config_dir: Path) -> Path:
    novel_root = config_dir / "_novel"
    (novel_root / "config").mkdir(parents=True, exist_ok=True)
    (config_dir / "current_novel.yaml").write_text(
        yaml.dump({"root": str(novel_root.resolve())}, allow_unicode=True),
        encoding="utf-8",
    )
    (novel_root / "config" / "world.yaml").write_text(
        yaml.dump(
            {"world": {"name": "测", "era": "古"}, "brief": "简介一行"},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (novel_root / "config" / "setting_research_output.yaml").write_text(
        "power_system:\n  name: 测战力\n  description: 短\n",
        encoding="utf-8",
    )
    return novel_root


def test_design_discussion_profile_uses_yaml_digest_and_compact_md(tmp_path):
    """design_discussion：结构化 YAML 提要 + 多归档 .md 行级压缩，不整块照搬 YAML。"""
    _bind_novel(tmp_path)
    dr = tmp_path / "data" / "book" / "setting"
    dr.mkdir(parents=True)
    (dr / "note.md").write_text(
        "# 注\n\n- **空壳占位**：\n\n- **有内容**：这是一条说明。\n",
        encoding="utf-8",
    )
    rt = {"runtime": {"storage": {"data_root": "data"}}}

    snips = retrieve_for_intent(
        INTENT_INPUT_IDEA_DISCUSS,
        "境界",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
        max_total_chars=2400,
        retrieval_profile=RETRIEVAL_PROFILE_DESIGN_DISCUSSION,
    )
    blob = format_snippets_for_prompt(snips)
    assert any("#摘要" in s.source or s.source.endswith("#摘要") for s in snips)
    assert "book/setting" in blob and ("压缩摘要" in blob or "#压缩摘要" in blob)
    assert "有内容" in blob and "这是一条说明" in blob
    # 空壳「- **空壳占位**：」行应被压缩掉
    assert "空壳占位" not in blob
    layered = assemble_retrieval_prompt_block(snips, layout="design_discussion")
    assert "「归档摘录」" in layered and "① 世界配置摘要" in layered


def test_retrieve_setting_intents_include_world_and_setting_file(tmp_path):
    _bind_novel(tmp_path)
    rt = {"runtime": {"storage": {"data_root": "data"}}}
    for iid in (INTENT_INPUT_IDEA_DISCUSS, INTENT_EDIT_SETTING_FILES):
        snips = retrieve_for_intent(
            iid,
            "境界",
            config_dir=tmp_path,
            project_root=tmp_path,
            runtime_config=rt,
        )
        assert snips
        srcs = [s.source for s in snips]
        assert any("world" in x for x in srcs)
        assert any("setting_research" in x for x in srcs)
    blob = format_snippets_for_prompt(snips)
    assert "测" in blob or "power_system" in blob


def test_retrieve_save_progress_has_digest_and_design_session(tmp_path):
    _bind_novel(tmp_path)
    novel_root = Path(
        yaml.safe_load((tmp_path / "current_novel.yaml").read_text(encoding="utf-8"))["root"]
    )
    ai_path = novel_root / "config" / "author_interaction_state.yaml"
    ai_path.write_text(
        yaml.dump(
            {
                "phase_state": {"phase": "DESIGN_MAIN"},
                "last_round_digest": {
                    "interaction": "p",
                    "system_response": "ok",
                    "execution": "save",
                    "open_issues": [],
                    "updated_at": "2026-01-01T00:00:00Z",
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (tmp_path / "design_session.yaml").write_text("theme: t\ngenre: g\n", encoding="utf-8")
    snips = retrieve_for_intent(
        INTENT_SAVE_PROGRESS,
        "",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config={},
    )
    blob = format_snippets_for_prompt(snips)
    assert "interaction" in blob or "p" in blob
    assert "theme" in blob or "design_session" in blob


def test_retrieve_design_complete_empty(tmp_path):
    snips = retrieve_for_intent(
        INTENT_DESIGN_COMPLETE,
        "",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config={},
    )
    assert snips == []


def test_intent_retrieval_tool_registry_matches_design_main():
    assert INTENT_RETRIEVAL_TOOL_CHAINS[INTENT_INPUT_IDEA_DISCUSS] == DESIGN_MAIN_SETTING_TOOLS
    assert INTENT_RETRIEVAL_TOOL_CHAINS[INTENT_EDIT_SETTING_FILES] == DESIGN_MAIN_SETTING_TOOLS
    assert len(DESIGN_MAIN_SETTING_TOOLS) == 3
    assert INTENT_RETRIEVAL_TOOL_CHAINS[INTENT_REVIEW_REVISE] == MAIN_WRITING_REVIEW_TOOLS
    assert len(MAIN_WRITING_REVIEW_TOOLS) == 2


class _FakeScopeStorage:
    """最小 storage：供 R7c scope_recent_events 单测。"""

    def __init__(self, events: list[dict]):
        self._events = events

    def get_recent_events(self, scope_id: str, k: int = 10):
        return self._events[-k:]


def test_retrieve_review_revise_scope_events_and_digest(tmp_path):
    """R7c：review_revise + storage/scope_id 拉最近事件摘要与 digest。"""
    _bind_novel(tmp_path)
    novel_root = Path(
        yaml.safe_load((tmp_path / "current_novel.yaml").read_text(encoding="utf-8"))["root"]
    )
    ai_path = novel_root / "config" / "author_interaction_state.yaml"
    ai_path.write_text(
        yaml.dump(
            {
                "last_round_digest": {
                    "interaction": "审阅",
                    "system_response": "展示正文",
                    "execution": "—",
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    st = _FakeScopeStorage(
        [
            {"summary": "第一回合"},
            {"summary": "第二回合摘要较长", "body": "正文略"},
        ]
    )
    snips = retrieve_for_intent(
        INTENT_REVIEW_REVISE,
        "改对话",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config={},
        storage=st,
        scope_id="main",
    )
    blob = format_snippets_for_prompt(snips)
    assert "scope_events:main" in blob or "main" in "".join(s.source for s in snips)
    assert "第二回合" in blob or "第一回合" in blob
    assert "interaction" in blob or "审阅" in blob


def test_retrieve_review_revise_without_storage_falls_back_digest_only(tmp_path):
    _bind_novel(tmp_path)
    novel_root = Path(
        yaml.safe_load((tmp_path / "current_novel.yaml").read_text(encoding="utf-8"))["root"]
    )
    (novel_root / "config" / "author_interaction_state.yaml").write_text(
        yaml.dump({"last_round_digest": {"interaction": "x", "system_response": "", "execution": ""}}),
        encoding="utf-8",
    )
    snips = retrieve_for_intent(
        INTENT_REVIEW_REVISE,
        "",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config={},
    )
    assert snips
    assert any("author_interaction" in s.source for s in snips)


def test_retrieval_query_boosts_matching_snippet_length(tmp_path):
    """R4：query 命中某源时，该源片段预算加权，文本应不短于无 query 时同源的采样。"""
    _bind_novel(tmp_path)
    novel_root = Path(
        yaml.safe_load((tmp_path / "current_novel.yaml").read_text(encoding="utf-8"))["root"]
    )
    (novel_root / "config" / "world.yaml").write_text(
        yaml.dump(
            {
                "world": {"name": "短", "era": "短"},
                "brief": ("无关填充 " * 400),
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    pad = "line\n" * 80
    (novel_root / "config" / "setting_research_output.yaml").write_text(
        f"marker_key: UNIQUEBOOSTMARK99\n{pad}",
        encoding="utf-8",
    )
    rt = {"runtime": {"storage": {"data_root": "data"}}}

    def _sr_len(snips):
        for s in snips:
            if "setting_research" in s.source:
                return len(s.text)
        return 0

    snips_baseline = retrieve_for_intent(
        INTENT_INPUT_IDEA_DISCUSS,
        "",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
        max_total_chars=1600,
    )
    snips_boosted = retrieve_for_intent(
        INTENT_INPUT_IDEA_DISCUSS,
        "UNIQUEBOOSTMARK99",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
        max_total_chars=1600,
    )
    assert _sr_len(snips_boosted) >= _sr_len(snips_baseline)
    assert "UNIQUEBOOSTMARK99" in format_snippets_for_prompt(snips_boosted)


def test_retrieve_max_total_chars_config(tmp_path):
    _bind_novel(tmp_path)
    long_snips = retrieve_for_intent(
        INTENT_INPUT_IDEA_DISCUSS,
        "",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config={"runtime": {"author_interaction": {"retrieve_max_total_chars": 900}}},
        max_total_chars=None,
    )
    total = sum(len(s.text) for s in long_snips)
    assert total <= 950
    assert retrieve_max_total_chars({"runtime": {"author_interaction": {"retrieve_max_total_chars": 900}}}) == 900


def test_retrieve_setting_intents_optional_internet_playwright(monkeypatch, tmp_path):
    _bind_novel(tmp_path)

    def fake_search(q, **kwargs):
        assert q
        return [{"title": "套路标题", "url": "https://example.com/x", "snippet": "摘要一句"}]

    monkeypatch.setattr(
        "src.author_harness.playwright_search.search_web_bing_sync",
        fake_search,
    )
    rt = {
        "runtime": {
            "storage": {"data_root": "data"},
            "author_harness": {
                "internet_search": {
                    "enabled": True,
                    "provider": "playwright",
                    "min_query_tokens": 1,
                },
            },
        }
    }
    snips = retrieve_for_intent(
        INTENT_INPUT_IDEA_DISCUSS,
        "写作套路",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
        internet_search_needed=True,
    )
    srcs = [s.source for s in snips]
    assert any("internet:playwright:bing" in x for x in srcs)
    blob = format_snippets_for_prompt(snips)
    assert "套路标题" in blob or "摘要一句" in blob


def test_retrieve_setting_intents_internet_disabled_no_playwright_source(tmp_path):
    _bind_novel(tmp_path)
    rt = {
        "runtime": {
            "author_harness": {
                "internet_search": {
                    "enabled": False,
                    "provider": "playwright",
                },
            },
        }
    }
    snips = retrieve_for_intent(
        INTENT_INPUT_IDEA_DISCUSS,
        "写作套路 足够长的查询",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
    )
    assert not any("internet:playwright" in s.source for s in snips)


def test_retrieve_setting_intents_internet_classifier_gate_blocks(monkeypatch, tmp_path):
    """按需联网：require_classifier_signal 默认开启时若无分类器同意则不调用 Bing。"""
    _bind_novel(tmp_path)
    called: list[str] = []

    def fake_search(q, **kwargs):
        called.append(q)
        return [{"title": "不该出现", "url": "", "snippet": ""}]

    monkeypatch.setattr(
        "src.author_harness.playwright_search.search_web_bing_sync",
        fake_search,
    )
    rt = {
        "runtime": {
            "storage": {"data_root": "data"},
            "author_harness": {
                "internet_search": {
                    "enabled": True,
                    "provider": "playwright",
                    "min_query_tokens": 1,
                },
            },
        }
    }
    retrieve_for_intent(
        INTENT_INPUT_IDEA_DISCUSS,
        "写作套路比较长的一句用于 token",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
        internet_search_needed=False,
    )
    assert called == []


def test_retrieve_internet_uses_internet_query_over_retrieval(monkeypatch, tmp_path):
    _bind_novel(tmp_path)
    captured: dict[str, str] = {}

    def fake_search(q, **kwargs):
        captured["q"] = q
        return [{"title": "OK", "url": "", "snippet": ""}]

    monkeypatch.setattr(
        "src.author_harness.playwright_search.search_web_bing_sync",
        fake_search,
    )
    rt = {
        "runtime": {
            "storage": {"data_root": "data"},
            "author_harness": {
                "internet_search": {
                    "enabled": True,
                    "provider": "playwright",
                    "min_query_tokens": 1,
                },
            },
        }
    }
    retrieve_for_intent(
        INTENT_INPUT_IDEA_DISCUSS,
        "世界观本地检索用语",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
        internet_search_needed=True,
        internet_query="网文 金手指 套路",
    )
    assert "金手指" in captured.get("q", "")
