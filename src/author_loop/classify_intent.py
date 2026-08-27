"""
入口意图分类（docs/design/author-interaction.md §8、§13 M3）。

在「当前阶段 + 合法意图白名单 + 上一轮摘要」约束下输出 intent_id；DummyLLM / 失败时走规则兜底（单字母菜单与少量中文关键词）。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.author_loop.author_interaction_state import AuthorPhaseState, LastRoundDigest

logger = logging.getLogger(__name__)

# —— 与设定主菜单对齐的稳定 ID（供 Handler / 路由表使用）——
INTENT_DESIGN_COMPLETE = "design_complete"
INTENT_EDIT_SETTING_FILES = "edit_setting_files"
INTENT_INPUT_IDEA_DISCUSS = "input_idea_discuss"
INTENT_SAVE_PROGRESS = "save_progress"
INTENT_FALLBACK = "intent_fallback"

# —— 阶段一正篇审阅（R7b，与 turn_planning.understand_author_review_intent 对拍）——
INTENT_REVIEW_CONFIRM = "review_confirm"
INTENT_REVIEW_REJECT = "review_reject"
INTENT_REVIEW_EDIT = "review_edit"
INTENT_REVIEW_SUPPLEMENT = "review_supplement"
INTENT_REVIEW_REVISE = "review_revise"

MAIN_REVIEW_INTENT_IDS: frozenset[str] = frozenset(
    {
        INTENT_REVIEW_CONFIRM,
        INTENT_REVIEW_REJECT,
        INTENT_REVIEW_EDIT,
        INTENT_REVIEW_SUPPLEMENT,
        INTENT_REVIEW_REVISE,
    }
)

# 与 turn_planning.CONFIRM_KEYWORDS 一致（避免 turn_planning→classify 循环 import）
_MAIN_REVIEW_CONFIRM_KEYWORDS = (
    "y",
    "yes",
    "是",
    "没问题",
    "满意",
    "通过",
    "可以",
    "好",
    "确认",
    "行",
    "ok",
)

DESIGN_MAIN_INTENT_IDS: frozenset[str] = frozenset(
    {
        INTENT_DESIGN_COMPLETE,
        INTENT_EDIT_SETTING_FILES,
        INTENT_INPUT_IDEA_DISCUSS,
        INTENT_SAVE_PROGRESS,
        INTENT_FALLBACK,
    }
)

_CONFIDENCE_LOW = 0.45

_INTERNET_HEURISTIC_EXPLICIT_REGEX = re.compile(
    r"联网检索|联网搜索|联网查|上网查|上网搜|上网检索|上网搜索|网上检索|网上搜索"
    r"|必应|bing\b|百度搜索|谷歌搜索|帮我搜|帮我检索|外链资料|站点外|google\b",
    re.IGNORECASE,
)
_INTERNET_HEURISTIC_CREATIVE_REGEX = re.compile(
    r"套路|模版|模板|范式|爽点模版|写法参考|网文套路|商业化套路|可参考.*流行|拆书对照|模版化|类型文",
)
# 「对齐市面常见写法」类讨论：宜用搜索拿通用条目，再由作者删减（避免模型独白发明小众体系）
_INTERNET_HEURISTIC_GENERIC_CONVENTION_REGEX = re.compile(
    r"(常规|通用|常见|经典|主流|流行|大众化|读者熟悉|业内常见|网文常见|类型文惯例)"
    r"|((参照|对标|对齐)\s{0,6}(主流|市面|流行|大众|常见|一般))"
    r"|((修仙|玄幻|仙侠|修真)(\s|的|：|:|[\,\，]){0,4}(等级|境界))"
    r"|你可(以)?搜索|可查[一下]|查查.*一般|搜索参考|百科|维基|词条"
    r"|((炼气|练气|筑基|金丹|元婴|化神|渡劫|凝气))",
    re.UNICODE,
)


def _internet_signals_heuristic(user_input: str) -> tuple[bool, str]:
    """
    规则判断「本轮设定讨论是否要联网检索」及建议搜索词句。
    显式用语（上网/搜/Bing…）或与套路/模版/范式等强相关时再触发，减少闲聊误搜。
    """
    s = (user_input or "").strip()
    if not s:
        return False, ""
    explicit = _INTERNET_HEURISTIC_EXPLICIT_REGEX.search(s) is not None
    creative = len(s) >= 6 and _INTERNET_HEURISTIC_CREATIVE_REGEX.search(s) is not None
    need = explicit or creative
    iq = s[:380].strip() if need else ""
    return need, iq


def _load_design_session_genre_theme(config_dir: Path | None) -> tuple[str, str]:
    """从编排目录下 design_session.yaml 读取本轮类型标签（可与用户句一起推断检索域）。"""
    if config_dir is None:
        return "", ""
    p = Path(config_dir) / "design_session.yaml"
    if not p.is_file():
        return "", ""
    try:
        import yaml

        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return "", ""
    if not isinstance(data, dict):
        return "", ""
    g = str(data.get("genre") or "").strip()
    t = str(data.get("theme") or "").strip()
    return g, t


def _internet_query_type_augment(genre: str, theme: str, user_text: str) -> str:
    """
    根据 **用户本轮用语 + design_session 类型** 拼接短搜索尾缀，避免修仙专用词贴到西幻/都市等非修仙作品上。
    优先级：正文关键词 → session genre/theme 关键词 → 泛化兜底。
    """
    blob = f"{genre} {theme} {(user_text or '')[:520]}"
    if any(k in blob for k in ("西幻", "奇幻", "魔幻", "巫师", "魔法师", "法师", "骑士", "精灵", "龙族", "DND", "dnd")):
        return "西幻网文 等级阶位 常见设定 参考"
    if any(k in blob for k in ("网游", "游戏", "职业等级", "技能树")):
        return "网游小说 等级体系 常见设定 参考"
    if any(k in blob for k in ("都市", "异能", "系统流", "重生", "娱乐")):
        return "都市网文 异能等级体系 常见写法 参考"
    if any(k in blob for k in ("科幻", "星际", "机甲", "末世", "末日", "废土")):
        return "科幻网文 进化阶位等级 常见设定 参考"
    if any(k in blob for k in ("无限流", "诸天", "副本", "轮回空间")):
        return "无限流网文 强化体系 常见设定 参考"
    if any(k in blob for k in ("历史", "古代", "朝堂", "权谋")):
        return "历史网文 官阶武阶 地位体系 常见写法 参考"
    if any(
        k in blob
        for k in (
            "修仙",
            "修真",
            "仙侠",
            "炼气",
            "练气",
            "筑基",
            "金丹",
            "元婴",
            "化神",
            "渡劫",
            "凝气",
        )
    ):
        return "修仙 境界划分 常见档位 参考"
    if any(k in blob for k in ("武侠", "江湖", "内功", "内力", "侠客", "剑客", "经脉")):
        return "武侠小说 武学内力境界层级 常见设定 参考"
    # 玄幻泛称（可能与斗气等非修仙并存）
    if any(k in blob for k in ("斗气", "魂力", "武魂", "魂环", "魂技")):
        return "玄幻升级文 魂力等级阶位 常见写法 参考"
    if "玄幻" in blob:
        return "玄幻小说 力量体系 等级划分 常见设定 参考"
    gg = (genre or "").strip()
    if gg:
        return f"{gg} 网络小说 常见设定 等级划分 参考"
    return "网文 常见类型 设定范式 参考"


def _internet_signals_generic_convention_heuristic(
    user_input: str,
    *,
    genre: str = "",
    theme: str = "",
) -> tuple[bool, str]:
    """
    作者希望贴近**常见类型文等级与惯例**时的粗规则联网信号（不限修仙）。
    与显式「上网搜」并列，供讨论阶段兜底（LLM 判路由失败仍可用）。
    """
    s = (user_input or "").strip()
    if len(s) < 8:
        return False, ""
    if _INTERNET_HEURISTIC_GENERIC_CONVENTION_REGEX.search(s) is None:
        return False, ""
    blob = f"{genre} {theme} {s}"
    # 弱化误触：仅「想个境界名叫啥」不匹配；须有常见写法意图、题材+等级、多档并列或搜索语气之一
    has_convention_tone = bool(
        re.search(r"常规|通用|主流|常见|对标|参照|对齐|典型|市面|流行|大众化|写法", s)
    )
    has_genre_stack = bool(
        re.search(
            r"(修仙|玄幻|仙侠|修真|奇幻|魔幻|都市|异能|科幻|星际|机甲|末世|武侠|西幻)"
            r"[\s\S]{1,42}(等级|境界|段位|体系|划分)",
            blob,
        )
    )
    cultivation_tokens = ("练气", "炼气", "筑基", "金丹", "元婴", "化神", "渡劫", "凝气")
    stage_hits = sum(1 for k in cultivation_tokens if k in s)
    has_multi_stage = stage_hits >= 2 or ("、" in s and stage_hits >= 1)
    has_search_tone = bool(re.search(r"搜索|检索|查查|可查|维基|百科|词条|必应|bing|百度", s, flags=re.IGNORECASE))
    if not (has_convention_tone or has_genre_stack or has_multi_stage or has_search_tone):
        return False, ""

    base = s[:380].strip()
    # 类型化检索尾缀统一在 `_internet_signals_design_discussion._merge_type_augment_into_query` 合并，避免双重拼接。
    return True, base[:440].strip()


def _internet_signals_design_discussion(
    user_input: str,
    runtime_config: dict,
    *,
    config_dir: Path | None = None,
) -> tuple[bool, str]:
    """自由讨论子阶段：可选 LLM 判定；失败或非 LLM 时走规则。"""
    g_sess, th_sess = _load_design_session_genre_theme(config_dir)

    def _merge_type_augment_into_query(raw_iq: str) -> str:
        """检索短句后缀按『用户输入 + design_session』类型收窄（非修仙作品勿默认贴修仙词）。"""
        iq0 = (raw_iq or "").strip()
        if len((user_input or "").strip()) >= 4 and not iq0:
            iq0 = (user_input or "").strip()[:280]
        aug = _internet_query_type_augment(g_sess, th_sess, user_input or "")
        if not aug:
            return iq0[:440].strip()
        if aug not in iq0:
            iq0 = (iq0 + " " + aug).strip() if iq0 else aug
        return iq0[:440].strip()

    if intent_llm_enabled(runtime_config):
        try:
            from src.llm import get_llm_provider

            provider = get_llm_provider(runtime_config)
            if provider.__class__.__name__ != "DummyLLM":
                clip = ((user_input or "").strip())[:2800]
                ctx_extra = ""
                if g_sess or th_sess:
                    ctx_extra = f"\n（已知类型标签：genre={g_sess or '未知'} theme={th_sess or '未知'} ，用于斟酌 internet_query 检索域）\n"
                prompt = (
                    "你是检索路由辅助。仅在「设定/创意讨论」场景下判断是否要**联网检索**（非写作正文）。\n"
                    "输出**仅** JSON，无其它文字：\n"
                    '{"internet_search_needed":false,'
                    '"internet_query":"适合搜索引擎的中文或英文短语，可无"}\n\n'
                    "规则：internet_search_needed 为 true **当且仅当**满足其一——\n"
                    "① 作者**明确要求**联网/搜索/Bing/Google/查找资料；\n"
                    "② 作者在要**套路/模版/范式/写法参考/流行结构/商业向拆书对照**等，且明显需要站外资料而非只看本地 YAML；\n"
                    "③ 作者希望设定**对齐常见/主流的等级或类型文惯例**（须按语境区分：修仙/西幻/都市/科幻等不同检索域），"
                    "需要从站外拉可查的通用条目列表再给作者删减，而非臆造。**internet_query** 应尽量带上与作品类型匹配的检索词。\n"
                    "**不要**在正常归纳设定、校对已有文档、寒暄时设为 true。\n"
                    "若 true 且无合适短查询，internet_query 可填空字符串（程序会按类型补后缀）。\n\n"
                    f"作者本轮输入：\n{clip}"
                    + ctx_extra
                )
                raw = provider.generate(prompt)
                data = _extract_json_object(raw) or {}
                need = bool(data.get("internet_search_needed", False))
                iq = str(data.get("internet_query") or "").strip()
                if need:
                    iq = _merge_type_augment_into_query(iq)
                return need, iq
        except Exception as e:
            logger.warning("自由讨论互联网意图 LLM 失败，规则兜底: %s", e)
    need, iq = _internet_signals_heuristic(user_input)
    if not need:
        need, iq = _internet_signals_generic_convention_heuristic(
            user_input,
            genre=g_sess,
            theme=th_sess,
        )
    if need:
        iq = _merge_type_augment_into_query(iq if (iq or "").strip() else "")
    return need, iq


def _extract_json_object(s: str) -> dict[str, Any] | None:
    s = (s or "").strip()
    if "```" in s:
        parts = re.split(r"```(?:json)?\s*", s, flags=re.IGNORECASE)
        for p in parts:
            p = p.strip()
            if p.startswith("{"):
                s = p
                break
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _digest_snippet(dg: LastRoundDigest, max_chars: int = 400) -> str:
    parts = [
        (dg.interaction or "").strip(),
        (dg.system_response or "").strip(),
        (dg.execution or "").strip(),
    ]
    text = " | ".join(p for p in parts if p)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def intent_llm_enabled(runtime_config: dict) -> bool:
    """默认开启入口分类 LLM；可在 runtime.author_interaction.intent_classify_llm 设为 false 以始终规则兜底。"""
    rt = runtime_config.get("runtime") if isinstance(runtime_config.get("runtime"), dict) else {}
    if not isinstance(rt, dict):
        rt = {}
    ai = rt.get("author_interaction")
    if not isinstance(ai, dict):
        return True
    if "intent_classify_llm" in ai:
        return bool(ai["intent_classify_llm"])
    return True


@dataclass
class IntentClassification:
    """与专题 §8.2 对齐的结构化输出。"""

    intent_id: str
    confidence: float
    retrieval_query: str
    needs_clarification: bool
    #: 按需联网（设定讨论）：作者明确要求外链检索，或为创意/模板/范式等需站外参考资料
    internet_search_needed: bool = False
    #: 写给搜索引擎的短查询；为空则沿用 retrieval_query（见 retrieve_for_intent）
    internet_query: str = ""


def _intent_from_menu_key(key: str) -> str:
    return {
        "y": INTENT_DESIGN_COMPLETE,
        "e": INTENT_EDIT_SETTING_FILES,
        "c": INTENT_INPUT_IDEA_DISCUSS,
        "p": INTENT_SAVE_PROGRESS,
    }.get(key, INTENT_FALLBACK)


def looks_like_menu_freeform_design_input(text: str) -> bool:
    """
    主菜单单行：未选单字母 y/e/c/p，但内容像直接陈述书名/主角/设定等时，视为「直接进入讨论」的补充说明。
    与 heuristic_design_main_menu_key 的 other 分支衔接，避免长段描述被当作「其他→结束设定」。
    """
    s = (text or "").strip()
    if len(s) < 10:
        return False
    sl = s.lower()
    if sl in {"c", "y", "e", "p"}:
        return False
    if len(s) == 1 and sl in "yecp":
        return False
    # 较短且明显是菜单指令的，不当作「已写好的讨论稿」
    if len(s) < 22 and any(
        k in s
        for k in ("保存", "存档", "进度", "编辑", "yaml", "改文件", "完成", "正篇", "结束设定")
    ):
        return False
    if "，" in s or "。" in s or "：" in s or "；" in s:
        return True
    return len(s) >= 24


def heuristic_design_main_menu_key(text: str) -> str:
    """
    规则兜底：返回 y / e / c / p / other（与现 CLI 主菜单一致；other 对应原「其他输入→视为进入正篇」）。
    """
    s = (text or "").strip().lower()
    if not s:
        return "y"
    if len(s) == 1 and s in "yecp":
        return s
    # 中文关键词（轻量，避免与正文混淆；整句短输入优先）
    if any(k in s for k in ("保存", "存档", "进度")):
        return "p"
    if any(k in s for k in ("编辑", "yaml", "改文件", "手动改")):
        return "e"
    if any(k in s for k in ("讨论", "想法", "补充", "设定交流", "多轮")):
        return "c"
    if any(k in s for k in ("完成", "进入正篇", "结束设定", "满意了", "可以写了")):
        return "y"
    # 未按键而直接描述设定：等价于选 c 进入讨论（见 looks_like_menu_freeform_design_input）
    if looks_like_menu_freeform_design_input(text):
        return "c"
    return "other"


def classify_intent(
    user_input: str,
    phase_state: AuthorPhaseState,
    last_round_digest: LastRoundDigest,
    runtime_config: dict,
    *,
    config_dir: Path | None = None,
) -> IntentClassification:
    """
    对作者本轮输入做阶段内意图分类。当前完整实现 **DESIGN_MAIN** 白名单；其余 phase 仅规则兜底为 FALLBACK。
    """
    text = (user_input or "").strip()
    phase = (phase_state.phase or "DESIGN_MAIN").strip() or "DESIGN_MAIN"

    # R5：自由讨论子流程与主菜单共用 retrieve_for_intent 工具链（INPUT_IDEA_DISCUSS）
    if phase == "DESIGN_DISCUSSION":
        need_d, iq_d = _internet_signals_design_discussion(
            text, runtime_config, config_dir=config_dir
        )
        rq_d = text[:500] if text else ""
        if need_d and not iq_d.strip():
            iq_d = rq_d.strip()[:380]
        return IntentClassification(
            intent_id=INTENT_INPUT_IDEA_DISCUSS,
            confidence=1.0,
            retrieval_query=rq_d,
            needs_clarification=False,
            internet_search_needed=need_d,
            internet_query=iq_d,
        )

    # R7b：正篇阶段一审阅 — 分类结果供 Handler 路由；revise 时携带 retrieval_query
    if phase == "MAIN_WRITING_REVIEW":
        if not intent_llm_enabled(runtime_config):
            return _classify_main_review_dummy(text)
        try:
            from src.llm import get_llm_provider

            provider = get_llm_provider(runtime_config)
            if provider.__class__.__name__ == "DummyLLM":
                return _classify_main_review_dummy(text)
            prompt = _build_main_review_prompt(text, phase_state, last_round_digest)
            raw = provider.generate(prompt)
            data = _extract_json_object(raw) or {}
            iid = str(data.get("intent_id") or "").strip()
            conf = float(data.get("confidence", 0.0))
            rq = str(data.get("retrieval_query") or "").strip()
            clarify = bool(data.get("needs_clarification", False))
            if iid not in MAIN_REVIEW_INTENT_IDS or conf < _CONFIDENCE_LOW:
                return _classify_main_review_dummy(text)
            if iid == INTENT_REVIEW_REVISE and not rq and text:
                rq = text[:500]
            if iid != INTENT_REVIEW_REVISE and not rq and text:
                rq = text[:120]
            return IntentClassification(
                intent_id=iid,
                confidence=max(0.0, min(1.0, conf)),
                retrieval_query=rq,
                needs_clarification=clarify,
            )
        except Exception as e:
            logger.warning("classify_intent MAIN_WRITING_REVIEW LLM 失败，规则兜底: %s", e)
            return _classify_main_review_dummy(text)

    if phase != "DESIGN_MAIN":
        return IntentClassification(
            intent_id=INTENT_FALLBACK,
            confidence=0.0,
            retrieval_query=text[:120] if text else "",
            needs_clarification=True,
        )

    if not intent_llm_enabled(runtime_config):
        return _classify_design_main_dummy(text)

    try:
        from src.llm import get_llm_provider

        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return _classify_design_main_dummy(text)
        prompt = _build_design_main_prompt(text, phase_state, last_round_digest)
        raw = provider.generate(prompt)
        data = _extract_json_object(raw) or {}
        iid = str(data.get("intent_id") or "").strip()
        conf = float(data.get("confidence", 0.0))
        rq = str(data.get("retrieval_query") or "").strip()
        clarify = bool(data.get("needs_clarification", False))
        if iid not in DESIGN_MAIN_INTENT_IDS:
            iid = INTENT_FALLBACK
        if conf < _CONFIDENCE_LOW:
            iid = INTENT_FALLBACK
        if iid == INTENT_FALLBACK and looks_like_menu_freeform_design_input(text):
            iid = INTENT_INPUT_IDEA_DISCUSS
            conf = max(conf, 0.78)
        if iid == INTENT_FALLBACK:
            return _classify_design_main_dummy(text)
        if not rq and text:
            rq = (text or "")[:500] if iid == INTENT_INPUT_IDEA_DISCUSS else (text or "")[:80]
        need_net = bool(data.get("internet_search_needed", False))
        iq_net = str(data.get("internet_query") or "").strip()
        if need_net and not iq_net:
            iq_net = ((rq or text or "").strip())[:280]
        return IntentClassification(
            intent_id=iid,
            confidence=max(0.0, min(1.0, conf)),
            retrieval_query=rq,
            needs_clarification=clarify,
            internet_search_needed=need_net,
            internet_query=iq_net if need_net else "",
        )
    except Exception as e:
        logger.warning("classify_intent LLM 失败，规则兜底: %s", e)
        return _classify_design_main_dummy(text)


def _heuristic_main_review_intent_id(raw: str) -> str:
    """与 understand_author_review_intent 规则分支一致，返回 MAIN_REVIEW 稳定 intent_id。"""
    t = (raw or "").strip().lower()
    if not t:
        return INTENT_REVIEW_CONFIRM
    if t in ("n", "no", "否"):
        return INTENT_REVIEW_REJECT
    if t in ("e", "edit", "修改"):
        return INTENT_REVIEW_EDIT
    if t in ("s", "补充", "设定"):
        return INTENT_REVIEW_SUPPLEMENT
    if t in _MAIN_REVIEW_CONFIRM_KEYWORDS or t == "y":
        return INTENT_REVIEW_CONFIRM
    return INTENT_REVIEW_REVISE


def _classify_main_review_dummy(text: str) -> IntentClassification:
    iid = _heuristic_main_review_intent_id(text)
    rq = (text or "").strip()[:500] if iid == INTENT_REVIEW_REVISE else (text or "").strip()[:120]
    return IntentClassification(
        intent_id=iid,
        confidence=0.95,
        retrieval_query=rq,
        needs_clarification=False,
    )


def main_review_intent_to_cli_action(intent_id: str) -> str:
    """将 R7b 稳定 id 映射为 review_turn_result 沿用的动作名。"""
    return {
        INTENT_REVIEW_CONFIRM: "confirm",
        INTENT_REVIEW_REJECT: "reject",
        INTENT_REVIEW_EDIT: "edit",
        INTENT_REVIEW_SUPPLEMENT: "supplement",
        INTENT_REVIEW_REVISE: "revise",
    }.get(intent_id, "revise")


def _build_main_review_prompt(
    user_input: str,
    phase_state: AuthorPhaseState,
    last_round_digest: LastRoundDigest,
) -> str:
    whitelist = (
        f'"{INTENT_REVIEW_CONFIRM}"：满意 / 通过 / 写回本回合（y、没问题、满意等）\n'
        f'"{INTENT_REVIEW_REJECT}"：驳回本回合（n、否）\n'
        f'"{INTENT_REVIEW_EDIT}"：先导出到文件再编辑（e、修改）\n'
        f'"{INTENT_REVIEW_SUPPLEMENT}"：补充设定（s、补充）\n'
        f'"{INTENT_REVIEW_REVISE}"：自由文本，作为对本回合正文的修改意见，需修订后再次展示'
    )
    flags = phase_state.flags if isinstance(phase_state.flags, dict) else {}
    snap = json.dumps(
        {"phase": "MAIN_WRITING_REVIEW", "subphase": phase_state.subphase, "flags": flags},
        ensure_ascii=False,
    )
    digest = _digest_snippet(last_round_digest)
    return (
        "你是小说项目在环审阅路由。根据「作者输入」在下列合法 intent_id 中选一个（必须逐字使用下列英文 id）：\n"
        f"{whitelist}\n\n"
        f"当前阶段快照（JSON）：{snap}\n"
        f"上一轮摘要（短）：{digest or '（无）'}\n\n"
        "仅输出一个 JSON 对象，不要其它文字：\n"
        '{"intent_id":"...",'
        '"confidence":0.0,'
        '"retrieval_query":"若为 revise 则填作者修改要点供检索，否则可简短或空",'
        '"needs_clarification":false}\n\n'
        f"作者输入：\n{user_input}\n"
    )


def _classify_design_main_dummy(text: str) -> IntentClassification:
    net_need, iq = _internet_signals_heuristic(text or "")
    k = heuristic_design_main_menu_key(text)
    if k == "other":
        return IntentClassification(
            intent_id=INTENT_FALLBACK,
            confidence=0.35,
            retrieval_query=(text or "")[:120],
            needs_clarification=False,
            internet_search_needed=net_need,
            internet_query=iq if net_need else "",
        )
    iid = _intent_from_menu_key(k)
    rq_cap = 500 if iid == INTENT_INPUT_IDEA_DISCUSS else 120
    rq = (text or "")[:rq_cap]
    if net_need and not iq.strip():
        iq = rq.strip()[:380]
    return IntentClassification(
        intent_id=iid,
        confidence=0.95,
        retrieval_query=rq,
        needs_clarification=False,
        internet_search_needed=net_need,
        internet_query=iq if net_need else "",
    )


def _build_design_main_prompt(
    user_input: str,
    phase_state: AuthorPhaseState,
    last_round_digest: LastRoundDigest,
) -> str:
    whitelist = (
        f'"{INTENT_DESIGN_COMPLETE}"：设定完成，进入正篇\n'
        f'"{INTENT_EDIT_SETTING_FILES}"：编辑设定相关 YAML 后返回\n'
        f'"{INTENT_INPUT_IDEA_DISCUSS}"：输入想法或进入多轮讨论/归纳\n'
        f'"{INTENT_SAVE_PROGRESS}"：保存进度（会话与封面简介等）\n'
        f'"{INTENT_FALLBACK}"：无法归入以上任一类，或作者意图不明'
    )
    flags = phase_state.flags if isinstance(phase_state.flags, dict) else {}
    snap = json.dumps(
        {"phase": "DESIGN_MAIN", "subphase": phase_state.subphase, "flags": flags},
        ensure_ascii=False,
    )
    digest = _digest_snippet(last_round_digest)
    return (
        "你是写作项目在环路由。根据「作者输入」在下列合法 intent_id 中选一个（必须逐字使用下列英文 id）：\n"
        f"{whitelist}\n\n"
        "特别规则：作者**未**输入单个菜单字母 y/e/c/p，而是用**一段较长文字**描述书名、主角人设、世界观、剧情设想等写作信息时，"
        "**必须**归类为 **`input_idea_discuss`**（等价于选了 c），不要把这种输入判为 **`intent_fallback`**。\n\n"
        "另请判断是否要**按需联网检索**（仅摘要注入讨论，不写正文）：\n"
        "• internet_search_needed=true：作者**明确要求上网/搜索/查必应等**，或本轮明显需要站外「套路/模板/范式/写法参考」。\n"
        "• 普通设定归纳、校对已有 YAML、不涉及外部参考资料时必须为 false。\n"
        "• internet_query：给搜索引擎用的短语句；若为 true 可留空，系统会沿用 retrieval_query。\n\n"
        f"当前阶段快照（JSON）：{snap}\n"
        f"上一轮摘要（短）：{digest or '（无）'}\n\n"
        "仅输出一个 JSON 对象，不要其它文字：\n"
        '{"intent_id":"...",'
        '"confidence":0.0,'
        '"retrieval_query":"供后续检索的短关键词句（中文或英文均可）",'
        '"needs_clarification":false,'
        '"internet_search_needed":false,'
        '"internet_query":""}\n\n'
        f"作者输入：\n{user_input}\n"
    )


def design_main_menu_key(classification: IntentClassification, raw_input: str) -> str:
    """
    将 IntentClassification 映射为设计主菜单分支键 y/e/c/p/other。
    intent_fallback 时用规则再次解析 raw_input（与旧版单字母/关键词行为一致）。
    """
    m = {
        INTENT_DESIGN_COMPLETE: "y",
        INTENT_EDIT_SETTING_FILES: "e",
        INTENT_INPUT_IDEA_DISCUSS: "c",
        INTENT_SAVE_PROGRESS: "p",
    }
    iid = classification.intent_id
    if iid in m:
        return m[iid]
    return heuristic_design_main_menu_key(raw_input)
