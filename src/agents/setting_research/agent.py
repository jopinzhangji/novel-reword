"""
设定研究 Agent：设计期/按需运行，产出战力/等级/境界等设定文件。
与 TECH_IMPLEMENTATION、DESIGN 一致。支持 LLM 抽取生成 power_system/level_system；无 LLM 或失败时写占位 YAML。
"""
import logging
import re
import yaml
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SettingResearchAgent:
    """
    设定研究 Agent。设计期或按需调用，不参与每回合并行。
    输入：题材、类型、参照；输出：写入 config 或指定目录的 YAML。
    若 run() 传入 runtime_config 且配置了真实 LLM，则用 LLM 生成战力/境界设定；否则写占位 YAML。
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        """
        output_dir: 产出设定文件的目录（默认 None 时由 run() 的 output_dir 参数或调用方指定）。
        """
        self.output_dir = output_dir

    def run(
        self,
        theme: str = "",
        genre: str = "",
        reference: str | None = None,
        output_dir: Path | None = None,
        runtime_config: dict | None = None,
    ) -> Path:
        """
        执行设定研究，产出设定文件。
        若 runtime_config 存在且 get_llm_provider 非 DummyLLM，则用 LLM 生成 power_system/level_system 并写入；
        否则写入占位 YAML。返回写入的文件路径。
        """
        out_dir = output_dir or self.output_dir
        if not out_dir:
            raise ValueError("output_dir 未设置，请传入或构造时指定")
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "setting_research_output.yaml"

        content = _generate_with_llm_if_available(
            theme=theme, genre=genre, reference=reference, runtime_config=runtime_config or {}
        )
        path.write_text(content, encoding="utf-8")
        return path

    def run_supplement(
        self,
        theme: str = "",
        genre: str = "",
        current_special: dict | None = None,
        context_snippet: str = "",
        author_input: str = "",
        output_dir: Path | None = None,
        runtime_config: dict | None = None,
    ) -> Path | None:
        """
        开篇后补充设定：在既有设定基础上仅做补充与完善，不与既有设定冲突。
        将 current_special 与 LLM 产出合并后写回；无 LLM 或失败时不写回，返回 None。
        """
        out_dir = output_dir or self.output_dir
        if not out_dir or not current_special:
            return None
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        current_yaml = yaml.dump(
            current_special,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
        prompt = _build_setting_supplement_prompt(
            theme=theme,
            genre=genre,
            current_special_yaml=current_yaml,
            context_snippet=context_snippet,
            author_input=author_input,
        )
        runtime_config = runtime_config or {}
        try:
            from src.llm import get_llm_provider
            provider = get_llm_provider(runtime_config)
            if provider.__class__.__name__ == "DummyLLM":
                return None
            raw = provider.generate(prompt)
            yaml_part = _extract_yaml_block(raw)
            data = yaml.safe_load(yaml_part)
            if not isinstance(data, dict):
                return None
            merged = _merge_supplement_into_special(current_special, data)
            path = out_dir / "setting_research_output.yaml"
            path.write_text(
                _dict_to_yaml(merged),
                encoding="utf-8",
            )
            return path
        except Exception:
            return None


def _extract_yaml_block(text: str) -> str:
    """从 LLM 返回中提取 ```yaml 或 ``` 代码块；若无则返回原文。"""
    text = (text or "").strip()
    m = re.search(r"```(?:yaml|yml)?\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


def _generate_with_llm_if_available(
    theme: str = "",
    genre: str = "",
    reference: str | None = None,
    runtime_config: dict | None = None,
) -> str:
    """有 LLM 时用 prompt 生成 power_system/level_system 并拼成完整 YAML；否则返回占位 YAML。"""
    runtime_config = runtime_config or {}
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return _placeholder_yaml(theme=theme, genre=genre, reference=reference)
        prompt = _build_setting_prompt(theme=theme, genre=genre, reference=reference)
        raw = provider.generate(prompt)
        yaml_part = _extract_yaml_block(raw)
        data = yaml.safe_load(yaml_part)
        if not isinstance(data, dict):
            return _placeholder_yaml(theme=theme, genre=genre, reference=reference)
        # 拼完整结构：world_id, version, genre, theme, reference + LLM 的 power_system, level_system
        out = {
            "world_id": data.get("world_id", "setting_research"),
            "version": data.get("version", "0.1"),
            "genre": genre or data.get("genre", ""),
            "theme": theme or data.get("theme", ""),
        }
        if reference:
            out["reference"] = reference
        if "power_system" in data:
            out["power_system"] = data["power_system"]
        else:
            out["power_system"] = {"name": "武力（占位）", "description": "LLM 未返回 power_system"}
        if "level_system" in data:
            out["level_system"] = data["level_system"]
        else:
            out["level_system"] = {"name": "境界（占位）", "description": "LLM 未返回 level_system", "levels": []}
        _skip_extra = {"world_id", "version", "genre", "theme", "reference", "power_system", "level_system"}
        for k, v in data.items():
            if k in _skip_extra or v is None:
                continue
            out[k] = v
        return _dict_to_yaml(out)
    except Exception:
        return _placeholder_yaml(theme=theme, genre=genre, reference=reference)


def _build_setting_prompt(theme: str = "", genre: str = "", reference: str | None = None) -> str:
    """拼设定研究 LLM prompt，要求输出 YAML。"""
    parts = [
        "你是一位小说设定策划。请根据以下信息，生成该题材下的「设定研究输出」。",
        f"题材：{theme or '未指定'}",
        f"类型/风格：{genre or '未指定'}",
    ]
    if reference:
        parts.append(f"参考或补充说明：{reference}")
    parts.extend([
        "",
        "**硬性要求**：内容必须与「类型/风格」和补充说明**一致**。若类型为现实/都市/言情/悬疑/历史/科幻等、"
        "且作者未要求玄幻仙侠，则 **禁止** 默认套用东方修仙式「灵力/境界/战力阶」命名；"
        "应将 power_system、level_system 设计成该题材下合理的体系（如：职业等级、社会阶层、技术代际、情感阶段、舰船职级等）。"
        "仅当作者明确玄幻、仙侠、修真、异能战斗等方向时，才可使用典型网文式境界结构。",
        "",
        "请只输出一段 YAML，包含以下结构（可简化，但需包含）：",
        "world_id: 设定世界id",
        "version: \"0.1\"",
        "power_system:",
        "  name: 战力体系名称",
        "  description: 简短说明",
        "  levels:  # 或 tiers，列表，每项含 name、order 等",
        "level_system:",
        "  name: 境界体系名称",
        "  description: 简短说明",
        "  levels:",
        "    - id: l0",
        "      name: 境界名",
        "      order: 0",
        "（可选）若依据中有剧情走向，请给出初版**章节大纲**（只写每章功能/转折一句，不写正文段落；无章则 chapters: []）：",
        "章节大纲:",
        "  name: 全书或当前卷大纲",
        "  description: 一句总览",
        "  chapters:",
        "    - chapter_number: 1",
        "      title: 章题或占位",
        "      summary: 本章剧情功能一句话（非正文）",
        "不要输出除 YAML 以外的解释文字。",
    ])
    return "\n".join(parts)


def _dict_to_yaml(data: dict) -> str:
    """将 dict 转为 YAML 字符串，含注释头。"""
    lines = [
        "# 设定研究 Agent 产出（LLM 生成）",
        f"# 生成时间: {datetime.now().isoformat()}",
        "",
    ]
    body = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    lines.append(body)
    return "\n".join(lines)


def _build_setting_supplement_prompt(
    theme: str = "",
    genre: str = "",
    current_special_yaml: str = "",
    context_snippet: str = "",
    author_input: str = "",
) -> str:
    """开篇后补充设定时的 prompt：仅可补充与完善，不得与既有设定冲突。"""
    parts = [
        "你是一位小说设定策划。当前处于**开篇后补充设定**环节：作者希望在既有设定基础上做**补充与完善**。",
        "**硬性约束**：不得与既有设定冲突，不得删除或推翻既有内容；仅可新增条目、细化描述、扩展层级，逻辑须自洽。",
        f"题材：{theme or '未指定'}",
        f"类型/风格：{genre or '未指定'}",
        "",
        "【既有设定】（请完整保留并在其基础上补充）：",
        current_special_yaml or "（空）",
        "",
        "【当前剧情上下文】",
        context_snippet or "（无）",
        "",
        "【作者补充意向】",
        author_input or "（无）",
        "",
        "请输出**完整** YAML（包含既有内容 + 你的补充），结构需包含 power_system、level_system 等既有键；只输出 YAML，不要解释。",
    ]
    return "\n".join(parts)


def _merge_supplement_into_special(current: dict, llm_output: dict) -> dict:
    """将 LLM 补充结果与既有设定合并：以 current 为底，llm_output 中存在的键覆盖或追加。"""
    merged = dict(current)
    base_keys = {"genre", "theme", "world_id", "version", "reference"}
    for k, v in (llm_output or {}).items():
        if k in base_keys:
            merged[k] = v
        elif isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


# --- 按方向讨论（DESIGN §6.6）---
#
# 上下文策略：每次 LLM 交互都注入「当前所需」的上下文，并做长度保护，避免超长导致截断或超限。
# - discuss_freely：传入「当前设定摘要」（已提炼）+「最近 N 轮对话」（有字数上限），保证连贯且可控。
# - summarize_and_extract_by_directions：传入「整段讨论」以归纳；若超长则保留最后一段并注明，保证归纳基于可见内容。

# 对话历史保留轮数；每轮（作者+Agent）单边最大字符数，超则截断并加省略
MAX_HISTORY_ROUNDS = 6
MAX_CHARS_PER_TURN_SIDE = 800
# 归纳时讨论内容最大字符数，超则保留最后一段
MAX_DISCUSSION_CHARS_FOR_SUMMARIZE = 12000

# 仅用于向后兼容展示（旧配置里可能用 power_system/level_system 作为 key）
DIRECTION_LABELS = {
    "power_system": "战力体系",
    "level_system": "境界体系",
    "章节大纲": "章节大纲",
    "chapter_outline": "章节大纲",
}


def classify_direction(
    author_message: str,
    theme: str,
    genre: str,
    existing_directions: list[str],
    runtime_config: dict,
) -> str:
    """
    由 LLM 根据作者输入判断讨论方向：从已有方向中匹配或新增一个方向名称。
    返回用于该次讨论的方向标签（如「境界体系」「炼丹体系」），后续会作为 special 的 key 存储。
    """
    runtime_config = runtime_config or {}
    existing_str = "、".join(existing_directions) if existing_directions else "（暂无）"
    prompt = (
        f"你是小说设定助手。请根据作者的一句话，判断他想讨论的「设定方向」。\n"
        f"题材：{theme or '未指定'}  类型：{genre or '未指定'}\n"
        f"当前已有设定方向（key，若匹配请直接使用）：{existing_str}\n\n"
        f"作者说：{author_message}\n\n"
        f"若与已有方向含义一致，请只输出已有的 key（如 power_system、level_system）；"
        f"否则输出一个新方向名称（如 炼丹体系、制符体系、物品体系）。只输出一个词，不要解释、不要换行。"
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return existing_directions[0] if existing_directions else "其他设定"
        raw = (provider.generate(prompt) or "").strip()
        line = raw.split("\n")[0].strip()
        return line or (existing_directions[0] if existing_directions else "其他设定")
    except Exception:
        return existing_directions[0] if existing_directions else "其他设定"


def _format_conversation_history_bounded(
    conversation_history: list[tuple[str, str]],
    max_rounds: int = MAX_HISTORY_ROUNDS,
    max_chars_per_side: int = MAX_CHARS_PER_TURN_SIDE,
) -> str:
    """将对话历史格式化为字符串，保留最近 max_rounds 轮，每轮单边超过 max_chars_per_side 则截断，保证每次 LLM 调用上下文可控且包含所需内容。"""
    if not conversation_history:
        return ""
    lines = []
    for a, b in conversation_history[-max_rounds:]:
        a_show = (a[:max_chars_per_side] + "…") if len(a) > max_chars_per_side else a
        b_show = (b[:max_chars_per_side] + "…") if len(b) > max_chars_per_side else b
        lines.append(f"作者：{a_show}\n设定 Agent：{b_show}")
    return "\n\n".join(lines)


def discuss_freely(
    author_message: str,
    theme: str,
    genre: str,
    full_special_summary: str,
    runtime_config: dict,
    conversation_history: list[tuple[str, str]] | None = None,
    assembled_context: str | None = None,
    *,
    read_line_fn: Callable[[str], str] | None = None,
    compressed_retrieval_is_canonical: bool = False,
) -> str:
    """
    与作者自由讨论设定，可涉及多个维度及其关系（如战力与境界的关系）。
    不锁定单一方向；讨论结束后由 summarize_and_extract_by_directions 归纳到各方向。
    每次调用注入：题材/类型、当前设定摘要（已提炼）、最近 N 轮对话（有字数上限），保证所需上下文且长度可控。

    ``assembled_context``：由 Harness 检索组装的已落盘片段（如 world / setting_research / book/setting），
    与 ``full_special_summary`` 互补；可为空。

    ``read_line_fn``：交互式控制台读一行（通常为 ``AuthorSession.read_line``）。
    非空时在传输超时后提示作者是否继续重试；为空则静默重试用尽后返回占位说明。

    ``compressed_retrieval_is_canonical``：自由讨论检索已走「YAML 提要 + 归档 Markdown 压缩」时置 True，
    避免与内存中的 ``full_special_summary`` 同源重复占位；仍会保留题材/类型行与「归档摘录」块。
    """
    logger.debug("[设定讨论] discuss_freely: 开始, author_message 长度=%s, history 轮数=%s",
                 len(author_message or ""), len(conversation_history or []))
    runtime_config = runtime_config or {}
    history_text = _format_conversation_history_bounded(conversation_history or [])
    canon_arc = bool((assembled_context or "").strip())
    mission = (
        "你是小说设定策划。当前与作者**自由讨论「可写入设定档」的内容**，优先围绕：\n"
        "- 世界规则、地理/聚落/势力、时间线、族群与技术、社会结构与禁忌；\n"
        "- 力量/职业/阶层等体系及其边界、资源与代价、关键道具或资源；\n"
        "- **全书或分卷、章节级剧情骨架（章节大纲）**：每章承担的功能、关键转折与伏笔位，用短条目表述即可，不写正文段落。\n"
        "- **通用范式优于空想**：谈及等级、境界、战力刻度或玄幻/修仙**常见档位**时，"
        "**优先**对齐读者熟悉的市面说法与短列表（若提示中有「互联网/外链检索」摘录，须先对齐其中要点并标明为可选参考）；"
        "**不要**在作者未明确要求「原创/反套路/全新体系」时，独白式编造与流行写法差距过大的命名或大段数值刻度表。"
        "若当前无摘录又需市面参照，请明确建议作者开联网检索或自行查百科后再定稿。\n\n"
        "**刻意避免**把对话写成「写作前成篇分析」：少谈修辞、镜头、句式、开场润色技巧等；若作者提到人物或桥段，请把它**收敛为可复述的设定条款**"
        "（关系网、动机规则、情节前提），而不是文学评论或教学口吻。\n"
        "**回复体例**：先 1～2 句说明如何对齐上文「归档摘录」各层；再用小标题或编号分条列出「可归档条款」，"
        "每条独立一行或极短段；避免无结构的长篇独白。\n\n"
        f"题材：{theme or '未指定'}  写作类型标签：{genre or '未指定'}\n\n"
    )
    if compressed_retrieval_is_canonical and canon_arc:
        prompt = mission + (
            "【归档摘录（结构化提要 + book/setting 归档压缩 · 与同目录磁盘一致）】\n"
            f"{assembled_context.strip()}\n\n"
            "已定稿关键点：请以**上文归档摘录为准**（程序已从 YAML/Markdown 压缩汇总）；"
            "勿逐句复述节选；仅在作者提出「与摘录不符」时再对照磁盘细节。\n\n"
        )
    else:
        prompt = mission + (f"当前设定摘要（内存提要）：\n{full_special_summary or '（暂无）'}\n\n")
        if canon_arc:
            prompt += (
                "【归档摘录（检索自磁盘 · 可与内存提要核对）】\n"
                f"{assembled_context.strip()}\n\n"
            )
    if history_text:
        prompt += "近期对话：\n" + history_text + "\n\n"
    prompt += (
        f"作者说：{author_message}\n\n"
        "在满足上述范围的前提下，可追问、细化、建议、澄清多体系之间的关系。不要输出 YAML。"
    )
    try:
        from src.llm import get_llm_provider
        from src.llm.call import (
            LLMTransportTimeoutExhausted,
            llm_invoke_with_transport_timeout_retry,
        )

        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return "（当前为 DummyLLM，无法自由讨论设定；请配置真实 LLM 或直接编辑 YAML。）"

        def _once() -> str:
            return (provider.generate(prompt) or "").strip()

        reply = llm_invoke_with_transport_timeout_retry(
            _once,
            input_fn=read_line_fn,
            log=logger,
            timeout_retry_budget=3,
            action_label="设定讨论",
        )
        return reply or "（无回复）"
    except LLMTransportTimeoutExhausted:
        return (
            "（讨论多次超时未完成；可稍后重试、在运行时配置中调大 framework.llm_options.timeout，"
            "或直接编辑 YAML。）"
        )
    except Exception:
        return "（讨论时出错，请重试或编辑 YAML。）"


def discuss_direction(
    direction_key: str,
    author_message: str,
    theme: str,
    genre: str,
    current_snippet: str,
    runtime_config: dict,
    conversation_history: list[tuple[str, str]] | None = None,
) -> str:
    """
    仅针对某一设定方向与作者对话，返回 Agent 的回复（仅该方向内容，非 YAML）。
    direction_key: power_system | level_system；conversation_history 为 [(author, agent), ...]。
    上下文：当前方向设定摘要 + 最近 N 轮对话（有字数上限）。
    """
    label = DIRECTION_LABELS.get(direction_key, direction_key)
    runtime_config = runtime_config or {}
    history_text = _format_conversation_history_bounded(conversation_history or [])
    prompt = (
        f"你是小说设定策划，当前**仅讨论【{label}】**，不要涉及其他设定方向。\n"
        f"题材：{theme or '未指定'}  类型：{genre or '未指定'}\n"
        f"当前该方向设定摘要：\n{current_snippet or '（暂无）'}\n\n"
    )
    if history_text:
        prompt += "近期对话：\n" + history_text + "\n"
    prompt += (
        f"作者说：{author_message}\n\n"
        f"请仅回复与【{label}】相关的**可归档设定要点**（可追问、细化、建议）。"
        f"若作者偏向文笔或成篇技巧，请简短将其拉回本方向的设定条文。不要输出 YAML，不要讨论其他方向。"
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return f"（当前为 DummyLLM，无法就【{label}】展开讨论；请配置真实 LLM 或直接编辑 YAML。）"
        return (provider.generate(prompt) or "").strip() or "（无回复）"
    except Exception:
        return f"（讨论【{label}】时出错，请重试或编辑 YAML。）"


def extract_direction_yaml(
    direction_key: str,
    discussion_text: str,
    theme: str,
    genre: str,
    runtime_config: dict,
) -> dict | None:
    """
    根据该方向的讨论内容，让 LLM 提炼为 YAML 片段，返回可合并的 dict（如 {"境界体系": {...}}）。
    direction_key 可为任意方向标签（战力体系、境界体系、炼丹体系等），不写死。
    """
    label = DIRECTION_LABELS.get(direction_key, direction_key)
    runtime_config = runtime_config or {}
    prompt = (
        f"根据以下关于【{label}】的讨论，请只输出该方向的 YAML 结构，不要其他解释。\n"
        f"题材：{theme}  类型：{genre}\n\n讨论内容：\n{discussion_text}\n\n"
        f"只输出该方向的 YAML，可包含 name、description、levels 或你认为合适的字段；"
        f"若用顶层 key 则使用「{label}」作为 key，或直接输出该方向的内容块。"
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return None
        raw = (provider.generate(prompt) or "").strip()
        yaml_part = _extract_yaml_block(raw)
        data = yaml.safe_load(yaml_part)
        if not isinstance(data, dict):
            return None
        if direction_key in data:
            return {direction_key: data[direction_key]}
        if label in data:
            return {direction_key: data[label]}
        # 无顶层 key 时视为该方向内容块，直接作为该 key 的值
        if "name" in data or "description" in data or "levels" in data or len(data) > 0:
            return {direction_key: data}
        return None
    except Exception:
        return None


def summarize_and_extract_by_directions(
    discussion_text: str,
    theme: str,
    genre: str,
    current_special: dict,
    runtime_config: dict,
) -> dict:
    """
    根据整段讨论内容，由 LLM 判断涉及哪些设定方向，并针对每个方向提炼 YAML。
    返回可合并的 dict，可能包含多个 key（如 {"境界体系": {...}, "战力体系": {...}}），
    讨论一轮后合并到各方向并提示作者。
    本次调用注入：整段讨论（若超长则保留最后 MAX_DISCUSSION_CHARS_FOR_SUMMARIZE 字并注明），保证归纳所需上下文。
    """
    logger.debug("[设定讨论] summarize_and_extract_by_directions: 开始, discussion_text 长度=%s, existing 方向=%s",
                 len(discussion_text or ""), list((current_special or {}).keys()))
    runtime_config = runtime_config or {}
    base_keys = {"genre", "theme", "world_id", "version", "reference"}
    existing = [k for k in (current_special or {}).keys() if k not in base_keys]
    existing_str = "、".join(existing) if existing else "（暂无，可新增方向）"
    text_to_use = discussion_text
    if len(discussion_text) > MAX_DISCUSSION_CHARS_FOR_SUMMARIZE:
        text_to_use = (
            f"（讨论较长，以下为最后约 {MAX_DISCUSSION_CHARS_FOR_SUMMARIZE} 字，请据此归纳）\n\n"
            + discussion_text[-MAX_DISCUSSION_CHARS_FOR_SUMMARIZE:]
        )
    prompt = (
        f"根据以下设定讨论，请判断讨论**涉及哪些设定方向**（可能多个，如战力体系、境界体系、炼丹体系、**章节大纲**等），"
        f"并针对每个涉及的方向分别输出该方向的 YAML 片段。\n"
        f"题材：{theme}  类型：{genre}\n"
        f"当前已有方向（key）：{existing_str}\n\n"
        f"讨论内容：\n{text_to_use}\n\n"
        f"重要：每个方向将写入**独立 .md 文件**，该文件**仅针对该方向展开**。"
        f"内容必须**涵盖讨论中与该方向相关的全部要点**，只能比讨论多、不能少；可适当扩展与润色，但不得遗漏讨论中的任何设定、边界或共识。\n"
        f"若讨论涉及**全书/分卷/逐章剧情骨架**，请使用顶层 key「章节大纲」，结构可含 name、description、chapters（列表，项可有 "
        f"chapter_number、title、summary 等；summary 仅一句剧情功能，勿写正文）。\n"
        f"要求：只输出一段 YAML，用顶层 key 区分各方向（与已有方向一致时请用已有 key，新方向用中文名如 炼丹体系）。"
        f"每个方向可包含 name、description、levels 或你认为合适的字段；若讨论的是多方向关系，可在各方向的 description 中体现或增加 relation 等字段。不要解释，不要 markdown 标题。"
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return {}
        raw = (provider.generate(prompt) or "").strip()
        logger.debug("[设定讨论] summarize_and_extract_by_directions: LLM 返回长度=%s", len(raw or ""))
        yaml_part = _extract_yaml_block(raw)
        data = yaml.safe_load(yaml_part)
        if not isinstance(data, dict):
            return {}
        # 只保留「方向」类 key（排除基础配置），便于合并
        base_keys_set = {"genre", "theme", "world_id", "version", "reference"}
        out = {k: v for k, v in data.items() if k not in base_keys_set and v is not None}
        logger.debug("[设定讨论] summarize_and_extract_by_directions: 归纳结果 keys=%s", list(out.keys()))
        return out
    except Exception:
        return {}


def run_discussion_logic_calibration(
    discussion_text: str,
    special_summary_text: str,
    theme: str = "",
    genre: str = "",
    runtime_config: dict | None = None,
) -> str | None:
    """
    对本迭代的讨论与归纳结果做逻辑校准：检查是否存在逻辑矛盾、遗漏或不一致。
    返回 LLM 的校准报告文本；无 LLM 或失败时返回 None。
    """
    logger.debug("[设定讨论] run_discussion_logic_calibration: 开始, discussion 长度=%s, special_summary 长度=%s",
                 len(discussion_text or ""), len(special_summary_text or ""))
    runtime_config = runtime_config or {}
    if not (discussion_text or "").strip():
        return None
    prompt = (
        "请对以下「设定讨论」与「当前归纳后的设定摘要」做逻辑校准：\n"
        "检查是否存在逻辑矛盾、设定遗漏、或与讨论共识不一致之处；若无则简要说明「未发现逻辑问题」。\n"
        f"题材：{theme or '未指定'}  类型：{genre or '未指定'}\n\n"
        "【讨论内容】\n" + (discussion_text or "").strip() + "\n\n"
        "【当前归纳后的设定摘要】\n" + (special_summary_text or "（无）") + "\n\n"
        "请逐条简要指出问题（若有），或明确说明未发现逻辑问题。"
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return None
        out = (provider.generate(prompt) or "").strip() or None
        logger.debug("[设定讨论] run_discussion_logic_calibration: 返回长度=%s", len(out or ""))
        return out
    except Exception:
        return None


def extract_discussion_boundaries_by_direction(
    discussion_text: str,
    direction_keys: list[str],
    theme: str = "",
    genre: str = "",
    runtime_config: dict | None = None,
) -> dict[str, str]:
    """
    根据讨论全文，为每个设定方向提炼一段「设定边界与讨论要点」，供写入 book/setting/<key>.md，
    便于后续查找、校准与边界确定。返回 dict[key, 段落文本]。
    """
    logger.debug("[设定讨论] extract_discussion_boundaries_by_direction: 开始, direction_keys=%s, discussion 长度=%s",
                 direction_keys, len(discussion_text or ""))
    runtime_config = runtime_config or {}
    if not direction_keys or not (discussion_text or "").strip():
        return {}
    keys_str = "、".join(direction_keys)
    text_to_use = (discussion_text or "").strip()
    if len(text_to_use) > MAX_DISCUSSION_CHARS_FOR_SUMMARIZE:
        text_to_use = text_to_use[-MAX_DISCUSSION_CHARS_FOR_SUMMARIZE:]
    prompt = (
        f"根据以下设定讨论全文，为**每个**设定方向各输出一段「设定边界与讨论要点」，"
        f"用于写入各方向对应的 .md 文件，便于后续查找与校准。\n"
        f"重要：每个方向的段落**必须涵盖讨论中与该方向相关的全部要点**，只能比讨论多、不能少；可归纳表述，不得遗漏任何讨论内容。\n"
        f"题材：{theme or '未指定'}  类型：{genre or '未指定'}\n"
        f"设定方向 key 列表（输出时每段标题必须用下列之一）：{keys_str}\n\n"
        f"讨论内容：\n{text_to_use}\n\n"
        f"输出格式：每段以「## 方向key」单独一行开头（方向key 必须从上面列表选），下一行起为该方向的完整段落（可长可短，以涵盖为准），再空行。只输出这些块，不要其他解释。"
    )
    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
        if provider.__class__.__name__ == "DummyLLM":
            return {}
        raw = (provider.generate(prompt) or "").strip()
        result: dict[str, str] = {}
        key_set = set(direction_keys)
        for block in raw.split("## "):
            block = block.strip()
            if not block:
                continue
            first_line, _, rest = block.partition("\n")
            key = first_line.strip().strip("：:")
            if key in key_set:
                result[key] = rest.strip() or ""
        logger.debug("[设定讨论] extract_discussion_boundaries_by_direction: 结果 keys=%s", list(result.keys()))
        return result
    except Exception:
        return {}


def _placeholder_yaml(theme: str = "", genre: str = "", reference: str | None = None) -> str:
    """生成占位设定 YAML 内容。"""
    undef = '"未指定"'
    lines = [
        "# 设定研究 Agent 产出（占位）",
        "# 当前为壳实现，未联网、未调用 LLM；后续可接入真实检索与抽取。",
        f"# 生成时间: {datetime.now().isoformat()}",
        "",
        "world_id: placeholder",
        "version: \"0.1\"",
        f"genre: {repr(genre) if genre else undef}",
        f"theme: {repr(theme) if theme else undef}",
    ]
    if reference:
        lines.append("reference: " + repr(reference))
    lines.extend([
        "",
        "power_system:",
        "  name: \"武力（占位）\"",
        "  description: \"壳实现，未做真实设定研究\"",
        "",
        "level_system:",
        "  name: \"境界（占位）\"",
        "  levels: []",
        "",
    ])
    return "\n".join(lines)
