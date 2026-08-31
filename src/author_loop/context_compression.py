"""CC-b：自适应分层任务锚定上下文压缩 —— CompressionContract 结构与生成器。

SDD ``docs/design/context-compression-adaptive-layered.md``（SPEC_SDD **D8**）§3.2/§3.3/§6。

**范围**：仅 CC-b——**CompressionContract 数据结构 + 规则/软原型（Soft Template）生成器**。
纯确定性、**无 LLM**、**不挂载到检索链路**（挂载 = CC-c）。

每轮生成一份「压缩契约」，明确本轮：
- ``task_thread``：本轮**任务主线**（由 phase + intent + 作者输入摘要推导的**过程**描述，非剧情结局）
- ``structure_preservation``：必须保留的**结构形式**（多来源标签 / 条目骨架 / 节拍锚点…）
- ``layer_roles``：**动态分层**（每层 name / importance / compress_strategy；不得写死为全仓唯一三层）
- ``sacrifice_order``：超预算时的**削减顺序**（避免一刀切成单段摘要）
- ``query_focus``：与 retrieval_query / 作者输入对齐的关注面

由**软原型**（按 phase+intent 对齐，仅给 layer_roles/structure/sacrifice 初值）+**自适应修正**
（输入长度、分类置信度）生成；**置信度低 / 无法归类**时退化为「**最小安全集**」兜底
（任务句 + 作者原句(或截断) + 来源标签骨架 + 少量事实锚点）。

CC-c（2026-08-31）落地确定性结构保留削减 ``reduce_snippet_structure_preserved`` 并挂载设计讨论
检索组装（见 ``retrieve_for_intent.compress_retrieval_snippets`` / ``design_phase``）。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .classify_intent import (
    INTENT_DESIGN_COMPLETE,
    INTENT_EDIT_SETTING_FILES,
    INTENT_FALLBACK,
    INTENT_INPUT_IDEA_DISCUSS,
    INTENT_REVIEW_CONFIRM,
    INTENT_REVIEW_EDIT,
    INTENT_REVIEW_REJECT,
    INTENT_REVIEW_REVISE,
    INTENT_REVIEW_SUPPLEMENT,
    INTENT_SAVE_PROGRESS,
)

# -- 分层权重 / 压缩策略常量（取值见 SDD §3.2 layer_roles 表）--
IMPORTANCE_HIGH = "high"
IMPORTANCE_MID = "mid"
IMPORTANCE_LOW = "low"

KEEP = "keep"          # 原样保留
SHORTEN = "shorten"    # 短写
EXTRACT = "extract"    # 抽取式压缩
ANCHOR = "anchor_only" # 仅保留锚点

# 自适应修正阈值
_LONG_INPUT_CHARS = 120      # 达到则抬高「作者原句」层权重（检索块更易压）
_LOW_CONFIDENCE = 0.5        # 低于则退化为最小安全集


@dataclass(frozen=True)
class LayerRole:
    """单个动态层的角色：名称 / 权重 / 压缩策略。"""

    name: str
    importance: str        # high | mid | low
    compress_strategy: str  # keep | shorten | extract | anchor_only


@dataclass(frozen=True)
class CompressionContract:
    """本轮自适应压缩契约（SDD §3.2）。序列化为 dict 供可观测。"""

    task_thread: str
    structure_preservation: str
    layer_roles: tuple[LayerRole, ...]
    sacrifice_order: tuple[str, ...]
    query_focus: str
    prototype_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {"task_thread": self.task_thread,
             "structure_preservation": self.structure_preservation,
             "layer_roles": [asdict(lr) for lr in self.layer_roles],
             "sacrifice_order": list(self.sacrifice_order),
             "query_focus": self.query_focus,
             "prototype_id": self.prototype_id}
        return d


def _lr(name: str, importance: str, strategy: str) -> LayerRole:
    return LayerRole(name, importance, strategy)


@dataclass(frozen=True)
class _ProtoSpec:
    prototype_id: str
    structure: str
    layers: tuple[LayerRole, ...]
    sacrifice: tuple[str, ...]


_PROTOTYPES: dict[str, _ProtoSpec] = {
    # 设定自由讨论：作者原句最高，检索证据可短写，世界 digest 只留锚点
    "design_discussion": _ProtoSpec(
        prototype_id="design_discussion",
        structure="多【来源】标签 + 条目级骨架（编号/小标题）",
        layers=(
            _lr("作者原句", IMPORTANCE_HIGH, KEEP),
            _lr("检索证据（归档/联网）", IMPORTANCE_MID, SHORTEN),
            _lr("世界/设定 digest", IMPORTANCE_LOW, ANCHOR),
        ),
        sacrifice=("世界/设定 digest", "检索证据（归档/联网）", "作者原句"),
    ),
    # 设定阶段编辑/结束：文件正文最高，YAML 提要可短写，归档抽取
    "design_edit": _ProtoSpec(
        prototype_id="design_edit",
        structure="文件名定位 + 键值/条目骨架",
        layers=(
            _lr("设定文件正文", IMPORTANCE_HIGH, KEEP),
            _lr("YAML 提要", IMPORTANCE_MID, SHORTEN),
            _lr("归档 .md", IMPORTANCE_LOW, EXTRACT),
        ),
        sacrifice=("归档 .md", "YAML 提要", "设定文件正文"),
    ),
    # 保存进度：进度摘要最高，上一轮 digest 可短写
    "save_progress": _ProtoSpec(
        prototype_id="save_progress",
        structure="进度键值列表或时间顺序摘要",
        layers=(
            _lr("进度摘要", IMPORTANCE_HIGH, KEEP),
            _lr("上一轮 digest", IMPORTANCE_MID, SHORTEN),
            _lr("设定/事件锚点", IMPORTANCE_LOW, ANCHOR),
        ),
        sacrifice=("设定/事件锚点", "上一轮 digest", "进度摘要"),
    ),
    # 正篇回合审阅：待检正文最高，成长/关系只留锚点，检索事件可抽取
    "main_review": _ProtoSpec(
        prototype_id="main_review",
        structure="节拍/章节点 + 事件时间顺序 + 待检正文",
        layers=(
            _lr("待检正文", IMPORTANCE_HIGH, KEEP),
            _lr("成长/关系锚点", IMPORTANCE_MID, ANCHOR),
            _lr("检索事件摘要", IMPORTANCE_LOW, EXTRACT),
        ),
        sacrifice=("检索事件摘要", "成长/关系锚点", "待检正文"),
    ),
    # 通用：已知意图但无专属原型
    "general": _ProtoSpec(
        prototype_id="general",
        structure="来源标签骨架 + 条目级骨架",
        layers=(
            _lr("作者原句", IMPORTANCE_HIGH, KEEP),
            _lr("检索证据", IMPORTANCE_MID, SHORTEN),
            _lr("digest/锚点", IMPORTANCE_LOW, ANCHOR),
        ),
        sacrifice=("digest/锚点", "检索证据", "作者原句"),
    ),
    # 最小安全集（兜底）：不得合为单段结论
    "minimal": _ProtoSpec(
        prototype_id="minimal",
        structure="来源标签骨架（禁止合为单段结论）",
        layers=(
            _lr("作者原句(或截断)", IMPORTANCE_HIGH, KEEP),
            _lr("事实锚点", IMPORTANCE_MID, ANCHOR),
            _lr("其它", IMPORTANCE_LOW, ANCHOR),
        ),
        sacrifice=("其它", "事实锚点", "作者原句(或截断)"),
    ),
}

_PHASE_ACT: dict[str, str] = {
    "DESIGN_MAIN": "推进设定阶段主流程",
    "DESIGN_DISCUSSION": "与作者就设定自由讨论并补足世界模型",
    "MAIN_WRITING_REVIEW": "展开正篇回合并请作者审阅/修订",
    "MAIN_WRITING": "推进正篇写作",
}
_INTENT_DESC: dict[str, str] = {
    INTENT_DESIGN_COMPLETE: "结束设定并进入正篇",
    INTENT_EDIT_SETTING_FILES: "编辑设定文件",
    INTENT_INPUT_IDEA_DISCUSS: "录入/讨论设定想法",
    INTENT_SAVE_PROGRESS: "保存进度与上下文摘要",
    INTENT_REVIEW_CONFIRM: "确认本回合正文",
    INTENT_REVIEW_REJECT: "驳回并要求重来",
    INTENT_REVIEW_EDIT: "就地编辑正文",
    INTENT_REVIEW_SUPPLEMENT: "补充检索/素材",
    INTENT_REVIEW_REVISE: "按意见修订正文",
    INTENT_FALLBACK: "未能明确归类的输入",
}

_REVIEW_IDS = {
    INTENT_REVIEW_CONFIRM,
    INTENT_REVIEW_REJECT,
    INTENT_REVIEW_EDIT,
    INTENT_REVIEW_SUPPLEMENT,
    INTENT_REVIEW_REVISE,
}


def _task_thread(phase: str, intent_id: str, user_input: str) -> str:
    """推导任务主线：phase + intent 描述 + 作者输入摘要（过程语义，非剧情结局）。"""
    act = _PHASE_ACT.get((phase or "").strip(), "处理作者本轮输入")
    desc = _INTENT_DESC.get(intent_id, intent_id or "")
    tail = ""
    s = (user_input or "").strip()
    if s:
        clipped = s[:20] + ("…" if len(s) > 20 else "")
        tail = f"（作者输入：{clipped}）"
    return f"辅助作者{act}——意图：{desc}{tail}"


def _match_prototype(phase: str, intent_id: str) -> str:
    """软原型匹配：按 phase+intent 对齐；无专属则 general；fallback 走 minimal。"""
    if intent_id == INTENT_FALLBACK:
        return "minimal"
    p = (phase or "").strip()
    if intent_id == INTENT_INPUT_IDEA_DISCUSS and p == "DESIGN_DISCUSSION":
        return "design_discussion"
    if intent_id in (INTENT_EDIT_SETTING_FILES, INTENT_DESIGN_COMPLETE) and p == "DESIGN_MAIN":
        return "design_edit"
    if intent_id == INTENT_SAVE_PROGRESS:
        return "save_progress"
    if intent_id in _REVIEW_IDS or p == "MAIN_WRITING_REVIEW":
        return "main_review"
    return "general"


def _bump_author_layer_keep(layers: list[LayerRole]) -> list[LayerRole]:
    """自适应：长输入下抬高「作者原句」层到 keep，其余层不动。"""
    def _f(lr: LayerRole) -> LayerRole:
        if "作者原句" in lr.name:
            return _lr(lr.name, IMPORTANCE_HIGH, KEEP)
        return lr
    return [_f(lr) for lr in layers]


def build_compression_contract(
    *,
    phase: str,
    intent_id: str,
    user_input: str = "",
    retrieval_query: str = "",
    confidence: float = 1.0,
) -> CompressionContract:
    """规则式生成压缩契约（确定性、无 LLM）。

    - 置信度 < ``_LOW_CONFIDENCE`` 或 fallback 意图 → 退化「最小安全集」兜底；
    - 其余按软原型 + 自适应修正（作者输入 ≥ ``_LONG_INPUT_CHARS`` 时抬高作者原句层）。
    """
    text = (user_input or "").strip()
    qf = (retrieval_query or (text or "")).strip()

    # 兜底：低置信 / 无法归类 → 最小安全集（任务句 + 作者原句 + 来源骨架 + 事实锚点）
    low_conf = confidence < _LOW_CONFIDENCE
    if low_conf or intent_id == INTENT_FALLBACK:
        spec = _PROTOTYPES["minimal"]
        return CompressionContract(
            task_thread=_task_thread(phase, intent_id, text),
            structure_preservation=spec.structure,
            layer_roles=spec.layers,
            sacrifice_order=spec.sacrifice,
            query_focus=qf,
            prototype_id=spec.prototype_id,
        )

    proto_id = _match_prototype(phase, intent_id)
    spec = _PROTOTYPES[proto_id]

    layers = list(spec.layers)
    if len(text) >= _LONG_INPUT_CHARS:
        layers = _bump_author_layer_keep(layers)

    return CompressionContract(
        task_thread=_task_thread(phase, intent_id, text),
        structure_preservation=spec.structure,
        layer_roles=tuple(layers),
        sacrifice_order=spec.sacrifice,
        query_focus=qf,
        prototype_id=proto_id,
    )


def contract_summary(contract: CompressionContract) -> dict[str, str]:
    """§5 可观测：仅取观测所需的契约摘要，避免把全量上下文写进日志。"""
    weights = {lr.name: f"{lr.importance}/{lr.compress_strategy}" for lr in contract.layer_roles}
    return {
        "prototype": contract.prototype_id,
        "task_thread": contract.task_thread,
        "structure": contract.structure_preservation,
        "layer_roles": str(weights),
        "sacrifice_order": "/".join(contract.sacrifice_order),
        "query_focus": contract.query_focus,
    }


# --- CC-c：确定性结构保留压缩（2026-08-31；SDD D8 §6.1） ---
# 门限触发、逐块结构保留削减，绝不压成单段结论；来源标签由 assembler 保留。

# 结构化标题行锚点：Markdown 标题 / 加粗小标题 / 编号项 / 作者记忆【…】标签 / 缩进条目。
_HEADING_RE = re.compile(r"^(#{1,6}\s|\*\*|[-*]\s+\*\*|\d+[.)]\s|【)")
_CLIP_TAIL_MARK = "\n…（已压缩）"


def reduce_snippet_structure_preserved(text: str, max_chars: int) -> str:
    """结构保留削减一块文本至 `max_chars`（确定性、无 LLM）。

    保留首个结构化标题行（`#`/`**`/编号/`【`）作锚点 + 逐行装入正文行；不低于可读锚点下限，
    结尾打节流标记。**禁止**把整块塌成单段结论文 —— 输出始终分节、可辨来源。
    契约的 layer_roles 用作文本是否可裁的提示（调用方裁剪范围由份额决定），此处保证表观结构。
    """
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    if max_chars < 1:
        return ""
    lines = t.split("\n")
    # 锚点：首个结构化标题行，否则首个非空内容行
    anchor = next((ln for ln in lines if _HEADING_RE.match(ln)), next((ln for ln in lines if ln.strip()), ""))
    if len(anchor) > max_chars:
        # 极小额：连标题都放不下时也截锚点（来源标签仍由 assembler 保留），绝不让整块留在原长度
        return anchor[: max_chars - 1] + "…"
    out = anchor
    budget = max_chars - len(anchor)
    dropped = False
    for ln in lines[1:]:
        if not ln.strip():
            continue
        if budget - len(ln) < 0:
            dropped = True
            break
        out += "\n" + ln
        budget -= len(ln)
    # 有正文行被丢弃（入口保证 len(t) > max_chars，故必有丢弃）→ 打节流标记，标识非完整
    # （不牺牲来源/结构，输出仍分节、可辨来源，绝不含糊为单段结论）。
    if dropped or budget < 0:
        out += _CLIP_TAIL_MARK
    return out[:max_chars] if len(out) > max_chars else out