"""入口 classify_intent（M3）：白名单、Dummy/规则兜底、design_main_menu_key。"""
from unittest.mock import MagicMock, patch

from src.author_loop.author_interaction_state import AuthorPhaseState, LastRoundDigest
from src.author_loop.classify_intent import (
    INTENT_DESIGN_COMPLETE,
    INTENT_FALLBACK,
    INTENT_INPUT_IDEA_DISCUSS,
    INTENT_REVIEW_CONFIRM,
    INTENT_REVIEW_EDIT,
    INTENT_REVIEW_REJECT,
    INTENT_REVIEW_REVISE,
    INTENT_REVIEW_SUPPLEMENT,
    INTENT_SAVE_PROGRESS,
    classify_intent,
    design_main_menu_key,
    heuristic_design_main_menu_key,
    looks_like_menu_freeform_design_input,
    intent_llm_enabled,
    main_review_intent_to_cli_action,
)


def _ps(phase: str = "DESIGN_MAIN"):
    return AuthorPhaseState(phase=phase)


def _dg():
    return LastRoundDigest(interaction="主菜单: y", system_response="—", execution="—")


def test_heuristic_single_letters():
    assert heuristic_design_main_menu_key("y") == "y"
    assert heuristic_design_main_menu_key("E") == "e"
    assert heuristic_design_main_menu_key("p") == "p"


def test_heuristic_keywords():
    assert heuristic_design_main_menu_key("先保存一下") == "p"
    assert heuristic_design_main_menu_key("我要编辑yaml") == "e"
    assert heuristic_design_main_menu_key("想讨论境界体系") == "c"
    assert heuristic_design_main_menu_key("设定完成了") == "y"


def test_heuristic_long_freeform_treated_as_discuss():
    s = "小说名定为苟道长手，主角张凡，是一个谨慎小心、但是又处事果决的角色"
    assert looks_like_menu_freeform_design_input(s)
    assert heuristic_design_main_menu_key(s) == "c"


def test_heuristic_single_c_not_freeform():
    assert not looks_like_menu_freeform_design_input("c")
    assert heuristic_design_main_menu_key("c") == "c"


def test_heuristic_empty_defaults_y():
    assert heuristic_design_main_menu_key("") == "y"


def test_classify_dummy_runtime_maps_y():
    rt = {"runtime": {"author_interaction": {}}}
    cl = classify_intent("y", _ps(), _dg(), rt)
    assert cl.intent_id == INTENT_DESIGN_COMPLETE
    assert design_main_menu_key(cl, "y") == "y"


def test_classify_non_design_phase_is_fallback():
    rt = {"runtime": {}}
    cl = classify_intent("y", _ps("MAIN_WRITING"), _dg(), rt)
    assert cl.intent_id == INTENT_FALLBACK


def test_main_writing_review_rules_match_legacy_review_intent():
    """R7b：MAIN_WRITING_REVIEW 规则与 understand_author_review_intent 历史行为一致。"""
    from src.author_loop.turn_planning import understand_author_review_intent

    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    for raw, legacy in [
        ("", "confirm"),
        ("n", "reject"),
        ("e", "edit"),
        ("s", "supplement"),
        ("y", "confirm"),
        ("没问题", "confirm"),
        ("把第三段改短一点", "revise"),
    ]:
        assert understand_author_review_intent(raw, rt) == legacy
        cl = classify_intent(raw, _ps("MAIN_WRITING_REVIEW"), _dg(), rt)
        assert main_review_intent_to_cli_action(cl.intent_id) == legacy


def test_main_review_revise_carries_retrieval_query():
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    cl = classify_intent("加强对话冲突", _ps("MAIN_WRITING_REVIEW"), _dg(), rt)
    assert cl.intent_id == INTENT_REVIEW_REVISE
    assert "对话" in cl.retrieval_query


def test_classify_design_discussion_maps_to_input_idea_discuss():
    """R5：自由讨论子流程固定走设定向检索链。"""
    rt = {"runtime": {}}
    cl = classify_intent("境界体系再确认一下", _ps("DESIGN_DISCUSSION"), _dg(), rt)
    assert cl.intent_id == INTENT_INPUT_IDEA_DISCUSS
    assert "境界" in cl.retrieval_query


def test_classify_intent_llm_disabled_uses_rules():
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    cl = classify_intent("保存进度", _ps(), _dg(), rt)
    assert cl.intent_id == INTENT_SAVE_PROGRESS
    assert design_main_menu_key(cl, "保存进度") == "p"


@patch("src.llm.get_llm_provider")
def test_classify_llm_success(mock_get):
    mock_get.return_value = MagicMock()
    mock_get.return_value.__class__.__name__ = "OpenAICompat"
    mock_get.return_value.generate.return_value = (
        '{"intent_id":"save_progress","confidence":0.9,"retrieval_query":"存档",'
        '"needs_clarification":false}'
    )
    rt = {"runtime": {}}
    cl = classify_intent("帮我存一下", _ps(), _dg(), rt)
    assert cl.intent_id == INTENT_SAVE_PROGRESS
    assert design_main_menu_key(cl, "帮我存一下") == "p"


@patch("src.llm.get_llm_provider")
def test_classify_llm_invalid_id_falls_back_to_rules(mock_get):
    mock_get.return_value = MagicMock()
    mock_get.return_value.__class__.__name__ = "OpenAICompat"
    mock_get.return_value.generate.return_value = '{"intent_id":"bogus","confidence":1}'
    rt = {"runtime": {}}
    cl = classify_intent("p", _ps(), _dg(), rt)
    assert cl.intent_id == INTENT_SAVE_PROGRESS
    assert design_main_menu_key(cl, "p") == "p"


def test_intent_llm_enabled_default():
    assert intent_llm_enabled({}) is True
    assert intent_llm_enabled({"runtime": {"author_interaction": {"intent_classify_llm": False}}}) is False


def test_design_discussion_internet_signals_explicit():
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    text = "请帮我必应检索一下修仙文金手指的常见套路模版"
    cl = classify_intent(text, _ps("DESIGN_DISCUSSION"), _dg(), rt)
    assert cl.intent_id == INTENT_INPUT_IDEA_DISCUSS
    assert cl.internet_search_needed is True


def test_design_discussion_internet_signals_creative_template():
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    text = "想参考商业化网文套路，爽点模版怎么铺在卷一"
    cl = classify_intent(text, _ps("DESIGN_DISCUSSION"), _dg(), rt)
    assert cl.intent_id == INTENT_INPUT_IDEA_DISCUSS
    assert cl.internet_search_needed is True


def test_design_discussion_internet_signals_generic_xianxia_levels():
    """对齐常见修仙等级 / 常规写法时：规则兜底应触发联网，便于拉通用条目再给作者删。"""
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    text = "请按常规玄幻小说，把修仙等级先对齐练气、筑基、金丹这种市面常见划分，我再改"
    cl = classify_intent(text, _ps("DESIGN_DISCUSSION"), _dg(), rt)
    assert cl.internet_search_needed is True
    assert len((cl.internet_query or "").strip()) >= 8


def test_design_discussion_internet_augment_respects_design_session_genre(tmp_path):
    """非修仙作品：design_session.genre 参与检索尾缀，勿默认贴『修仙』用语。"""
    (tmp_path / "design_session.yaml").write_text(
        "genre: 星际科幻\ntheme: 流浪星舰\n",
        encoding="utf-8",
    )
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    text = "想按常规做一下等级档位，对齐市面写法，方便读者入门"
    cl = classify_intent(
        text,
        _ps("DESIGN_DISCUSSION"),
        _dg(),
        rt,
        config_dir=tmp_path,
    )
    assert cl.internet_search_needed is True
    q = (cl.internet_query or "")
    assert "修仙" not in q
    assert "科幻" in q or "星际" in q


def test_design_discussion_internet_signals_off_smalltalk():
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    cl = classify_intent("先把境界名字叫什么定一下", _ps("DESIGN_DISCUSSION"), _dg(), rt)
    assert cl.internet_search_needed is False


def test_design_main_dummy_explicit_internet():
    rt = {"runtime": {"author_interaction": {"intent_classify_llm": False}}}
    text = "想补充设定，并请上网检索商业化写法参考模版"
    cl = classify_intent(text, _ps(), _dg(), rt)
    assert cl.intent_id == INTENT_INPUT_IDEA_DISCUSS
    assert cl.internet_search_needed is True
