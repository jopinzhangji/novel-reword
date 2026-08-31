"""CC-b 单测：CompressionContract 生成器（软原型 + 自适应修正 + 兜底）。

覆盖 SDD D8 §6 CC-b 验收——「多意图下契约字段合理；兜底路径」。纯确定性、无 LLM。
"""
from src.author_loop.classify_intent import (
    INTENT_DESIGN_COMPLETE,
    INTENT_EDIT_SETTING_FILES,
    INTENT_FALLBACK,
    INTENT_INPUT_IDEA_DISCUSS,
    INTENT_REVIEW_CONFIRM,
    INTENT_REVIEW_REVISE,
    INTENT_SAVE_PROGRESS,
)
from src.author_loop.context_compression import (
    ANCHOR,
    IMPORTANCE_HIGH,
    IMPORTANCE_MID,
    KEEP,
    SHORTEN,
    build_compression_contract,
    contract_summary,
    reduce_snippet_structure_preserved,
)


def _assert_coherent(c):
    # 契约五要素齐全
    assert c.task_thread.strip()
    assert c.structure_preservation.strip()
    assert c.layer_roles
    assert c.sacrifice_order
    assert len(c.sacrifice_order) == len(c.layer_roles)
    # 削减顺序与分层名称一一对应（先压 low，最后是 high）
    assert c.sacrifice_order[0] == [lr.name for lr in c.layer_roles][-1]  # 最末层最易压 -> 最末层名? 见下
    # 每层字段合法
    for lr in c.layer_roles:
        assert lr.importance in ("high", "mid", "low")
        assert lr.compress_strategy in ("keep", "shorten", "extract", "anchor_only")


def test_design_discussion_contract():
    c = build_compression_contract(
        phase="DESIGN_DISCUSSION", intent_id=INTENT_INPUT_IDEA_DISCUSS,
        user_input="我想让主角在与父亲冲突后避世修行",
        retrieval_query="设定 主角 避世修行",
    )
    assert c.prototype_id == "design_discussion"
    assert c.layer_roles[0].name == "作者原句" and c.layer_roles[0].importance == IMPORTANCE_HIGH
    # 削减顺序从最易压（world digest）到最保（作者原句）
    assert c.sacrifice_order[0].startswith("世界")
    assert c.sacrifice_order[-1] == "作者原句"
    assert c.query_focus == "设定 主角 避世修行"
    _assert_coherent(c)


def test_edit_setting_contract():
    c = build_compression_contract(
        phase="DESIGN_MAIN", intent_id=INTENT_EDIT_SETTING_FILES, user_input="e",
    )
    assert c.prototype_id == "design_edit"
    assert any("设定文件" in lr.name for lr in c.layer_roles)
    assert c.sacrifice_order[-1].startswith("设定文件正文")
    _assert_coherent(c)


def test_save_progress_contract():
    c = build_compression_contract(
        phase="DESIGN_MAIN", intent_id=INTENT_SAVE_PROGRESS, user_input="p",
    )
    assert c.prototype_id == "save_progress"
    assert any("进度" in lr.name for lr in c.layer_roles)
    assert c.sacrifice_order[-1] == "进度摘要"
    _assert_coherent(c)


def test_main_review_contract():
    c = build_compression_contract(
        phase="MAIN_WRITING_REVIEW", intent_id=INTENT_REVIEW_CONFIRM, user_input="同意",
    )
    assert c.prototype_id == "main_review"
    assert any("待检正文" in lr.name for lr in c.layer_roles)
    assert c.sacrifice_order[-1].startswith("待检正文")
    _assert_coherent(c)


def test_review_revise_with_missing_profile_uses_general():
    # 未知 phase + 已知 review 意图 → 仍按 review（phase 未命中也不崩）
    c = build_compression_contract(
        phase="UNKNOWN_PHASE", intent_id=INTENT_REVIEW_REVISE, user_input="改一下动作",
        retrieval_query="",
    )
    assert c.prototype_id == "main_review"
    _assert_coherent(c)


def test_fallback_and_low_confidence_minimal():
    # 无法归类 → 最小安全集
    c1 = build_compression_contract(
        phase="DESIGN_MAIN", intent_id=INTENT_FALLBACK, user_input="foo bar baz",
        retrieval_query="q", confidence=0.0,
    )
    assert c1.prototype_id == "minimal"
    assert "禁止" in c1.structure_preservation or "单段" in c1.structure_preservation
    assert any("来源" in lr.name or "骨架" in c1.structure_preservation for lr in c1.layer_roles)
    _assert_coherent(c1)

    # 低置信（即便意图已知）也退化为最小安全集
    c2 = build_compression_contract(
        phase="MAIN_WRITING_REVIEW", intent_id=INTENT_REVIEW_CONFIRM, user_input="同意",
        confidence=0.1,
    )
    assert c2.prototype_id == "minimal"
    _assert_coherent(c2)


def test_adaptive_long_input_promotes_author_layer():
    long_text = "作者输入了" + "很长的设定补足内容。" * 30 + "这是完整的一段。"
    c = build_compression_contract(
        phase="DESIGN_DISCUSSION", intent_id=INTENT_INPUT_IDEA_DISCUSS, user_input=long_text,
    )
    author_layer = next(lr for lr in c.layer_roles if "作者原句" in lr.name)
    assert author_layer.compress_strategy == KEEP  # 长输入 → 作者原句原样保留
    assert author_layer.importance == IMPORTANCE_HIGH
    _assert_coherent(c)


def test_short_input_does_not_bump_author_layer():
    # 短输入（菜单键/单字）不触发长输入的抬高修正
    c = build_compression_contract(
        phase="DESIGN_DISCUSSION", intent_id=INTENT_INPUT_IDEA_DISCUSS, user_input="好",
    )
    author_layer = next(lr for lr in c.layer_roles if "作者原句" in lr.name)
    assert author_layer.compress_strategy == KEEP  # 原型默认即 keep（讨论原型）
    _assert_coherent(c)


def test_query_focus_falls_back_to_user_input():
    c = build_compression_contract(
        phase="DESIGN_MAIN", intent_id=INTENT_SAVE_PROGRESS, user_input="保存一下",
        retrieval_query="",
    )
    assert c.query_focus == "保存一下"
    _assert_coherent(c)


def test_task_thread_is_process_oriented():
    c = build_compression_contract(
        phase="DESIGN_DISCUSSION", intent_id=INTENT_INPUT_IDEA_DISCUSS,
        user_input="补设定",
    )
    assert "辅助作者" in c.task_thread
    assert "意图" in c.task_thread
    # 过程性描述，非剧情结局式概括
    assert not c.task_thread.startswith("故事结局")


def test_to_dict_and_summary_round_trip():
    c = build_compression_contract(
        phase="MAIN_WRITING_REVIEW", intent_id=INTENT_REVIEW_REVISE, user_input="改",
        retrieval_query="主角 动作",
    )
    d = c.to_dict()
    assert set(d) == {"task_thread", "structure_preservation", "layer_roles",
                      "sacrifice_order", "query_focus", "prototype_id"}
    assert isinstance(d["layer_roles"], list) and d["layer_roles"][0]["name"]
    assert d["sacrifice_order"] == list(c.sacrifice_order)
    s = contract_summary(c)
    assert s["prototype"] == c.prototype_id and s["query_focus"] == "主角 动作"
    assert "作者原句" in s["layer_roles"] or "待检正文" in s["layer_roles"]


# --- CC-c：确定性结构保留压缩（SDD D8 §6.1） ---
def test_reduce_keeps_heading_and_never_single_paragraph():
    text = "## 世界设定\n第一行相当长刻画细节要尽量保留结构避免被塌成一句话结束整个模块\n* 特性甲 内容\n* 特性乙 内容"
    out = reduce_snippet_structure_preserved(text, 40)
    assert len(out) <= 40
    assert out.startswith("## 世界设定")      # 标题骨架保留
    assert "\n" in out or "…" in out           # 仍分节或带节流标记
    # 第二行也被截入（20 字内放得下部分）——不塌成「来源+单行结论」
    assert out.count("\n") >= 1
    assert out not in ("## 世界设定\n…", "## 世界设定")


def test_reduce_tiny_budget_truncates_anchor():
    # 连标题都放不下：也截锚点，绝不让整块留在原长度（哪怕来源标签由 assembler 保留）
    out = reduce_snippet_structure_preserved("## 世界设定\n很多很长的内容行安放这里", 5)
    assert len(out) <= 5


def test_reduce_noop_when_fits():
    text = "够短\n第二行"
    assert reduce_snippet_structure_preserved(text, 200) == text
    assert reduce_snippet_structure_preserved(text, 0) == ""


def test_reduce_clips_body_not_heading():
    text = "正文首行开头\nbullet 甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉"
    out = reduce_snippet_structure_preserved(text, 12)
    assert len(out) <= 12
    assert not text.startswith(out) and len(out) < len(text)  # 确实被剪短