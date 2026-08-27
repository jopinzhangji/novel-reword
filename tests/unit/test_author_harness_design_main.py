"""R6：主菜单 ingress 与 AuthorHarness 委托。"""
import yaml
from pathlib import Path

from src.author_harness.author_harness import (
    AuthorHarness,
    apply_design_main_menu_ingress,
    apply_main_writing_review_ingress,
)
from src.author_loop.author_session import AuthorSession
from src.author_loop.classify_intent import INTENT_INPUT_IDEA_DISCUSS, INTENT_REVIEW_REVISE


def _bind_novel(config_dir: Path) -> None:
    novel_root = config_dir / "_novel"
    (novel_root / "config").mkdir(parents=True, exist_ok=True)
    (config_dir / "current_novel.yaml").write_text(
        yaml.dump({"root": str(novel_root.resolve())}, allow_unicode=True),
        encoding="utf-8",
    )
    (novel_root / "config" / "world.yaml").write_text(
        yaml.dump({"world": {"name": "测", "era": "古"}, "brief": "简介"}, allow_unicode=True),
        encoding="utf-8",
    )


def test_apply_design_main_menu_ingress_freeform_long_text_is_discuss(tmp_path):
    """作者未按键 c，直接描述书名/主角时，等价于讨论。"""
    _bind_novel(tmp_path)
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    session = AuthorSession.for_design_phase(
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
    )
    long_line = (
        "小说名定为苟道长手，主角张凡，是一个谨慎小心、但是又处事果决，心狠手辣的角色"
    )
    r = apply_design_main_menu_ingress(
        long_line,
        session=session,
        config_dir=tmp_path,
        runtime_config=rt,
    )
    assert r.menu_key == "c"
    assert r.classification.intent_id == INTENT_INPUT_IDEA_DISCUSS


def test_apply_design_main_menu_ingress_sets_extra_and_returns_menu_c(tmp_path):
    _bind_novel(tmp_path)
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    session = AuthorSession.for_design_phase(
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
    )
    r = apply_design_main_menu_ingress(
        "c",
        session=session,
        config_dir=tmp_path,
        runtime_config=rt,
    )
    assert r.menu_key == "c"
    assert r.classification.intent_id == INTENT_INPUT_IDEA_DISCUSS
    assert session.extra.get("intent_retrieval") == r.retrieval_block
    assert session.extra.get("intent_retrieval_snippets") == r.retrieval_snippets


class _FakeStorage:
    def __init__(self, events: list[dict]):
        self._events = events

    def get_recent_events(self, scope_id: str, k: int = 10):
        return self._events[-k:]


def test_apply_main_writing_review_ingress_revise(tmp_path):
    """R7d/R8：审阅 revise 路径；分类→检索源→组装块关键字可断言。"""
    _bind_novel(tmp_path)
    novel_root = Path(
        yaml.safe_load((tmp_path / "current_novel.yaml").read_text(encoding="utf-8"))["root"]
    )
    (novel_root / "config" / "author_interaction_state.yaml").write_text(
        yaml.dump({"last_round_digest": {"interaction": "x", "system_response": "", "execution": ""}}),
        encoding="utf-8",
    )
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    st = _FakeStorage([{"summary": "前文摘要一句"}])
    ing = apply_main_writing_review_ingress(
        "把结尾改紧凑",
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
        storage=st,
        scope_id="main",
    )
    assert ing.intent_cli == "revise"
    assert ing.classification.intent_id == INTENT_REVIEW_REVISE
    srcs = [s.source for s in ing.retrieval_snippets]
    assert any(x.startswith("scope_events:") for x in srcs)
    assert any("author_interaction_state" in x for x in srcs)
    assert "前文摘要" in ing.retrieval_block or "author_interaction" in ing.retrieval_block


def test_author_harness_class_delegates(tmp_path):
    _bind_novel(tmp_path)
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    session = AuthorSession.for_design_phase(
        config_dir=tmp_path,
        project_root=tmp_path,
        runtime_config=rt,
    )
    h = AuthorHarness(session=session, config_dir=tmp_path, runtime_config=rt)
    r = h.apply_design_main_menu_ingress("y")
    assert r.menu_key == "y"
