"""
关键角色成长状态（阶段 1a 骨架；设计文档 §2、§2.1）。

`CharacterGrowthState` 数据类 + 落盘到 `<novel_root>/book/characters/<id>/growth_state.yaml`，
以及 `mind_state` 进程内承载入口 `record_mind_emotion`（写已有 `MemoryStorage.emotions[]` 空槽位）。
本文件只提供数据结构与持久化（阶段 1a）；完整五维迁移规则见阶段 1b。
"""
from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

GROWTH_STATE_VERSION = 1


@dataclass
class CharacterGrowthState:
    """一个关键角色的可审计成长状态：五维子状态 + 迁移日志。可序列化为 YAML。"""

    character_id: str
    power_state: dict[str, Any] = field(default_factory=dict)
    mind_state: dict[str, Any] = field(default_factory=dict)
    social_state: dict[str, Any] = field(default_factory=dict)
    goal_state: dict[str, Any] = field(default_factory=dict)
    resource_state: dict[str, Any] = field(default_factory=dict)
    transition_log: list[dict[str, Any]] = field(default_factory=list)
    version: int = GROWTH_STATE_VERSION
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any], character_id: str | None = None) -> "CharacterGrowthState":
        """从字典重建。缺字段时回退默认，保证旧/缺省文件可读。"""
        data = dict(data or {})
        return cls(
            character_id=character_id or str(data.get("character_id") or ""),
            power_state=dict(data.get("power_state") or {}),
            mind_state=dict(data.get("mind_state") or {}),
            social_state=dict(data.get("social_state") or {}),
            goal_state=dict(data.get("goal_state") or {}),
            resource_state=dict(data.get("resource_state") or {}),
            transition_log=list(data.get("transition_log") or []),
            version=int(data.get("version", GROWTH_STATE_VERSION)),
            updated_at=str(data.get("updated_at") or ""),
        )


def default_growth_state(character_id: str) -> CharacterGrowthState:
    """返回某关键角色的默认（空）成长状态。"""
    return CharacterGrowthState(character_id=character_id)


def growth_state_yaml_path(novel_root: Path, character_id: str) -> Path:
    """与 §2.1 一致：`<novel_root>/book/characters/<id>/growth_state.yaml`。"""
    return Path(novel_root) / "book" / "characters" / str(character_id) / "growth_state.yaml"


def load_growth_state(character_id: str, novel_root: Path) -> CharacterGrowthState:
    """
    读取某关键角色成长状态。文件不存在或不可解析时回退默认（不报错）。
    """
    path = growth_state_yaml_path(novel_root, character_id)
    if not path.is_file():
        return default_growth_state(character_id)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        logger.warning("growth_state 解析失败，回退默认：%s", path)
        return default_growth_state(character_id)
    if not isinstance(data, dict):
        return default_growth_state(character_id)
    return CharacterGrowthState.from_dict(data, character_id)


def save_growth_state(state: CharacterGrowthState, novel_root: Path) -> None:
    """将成长状态落盘 YAML。"""
    path = growth_state_yaml_path(novel_root, state.character_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(state.to_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def record_mind_emotion(storage: Any, character_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    """
    把一条主观心理记录写入该角色的进程内记忆槽位（`storage.append_emotion`，阶段 1a 起由代码写入）。
    entry 建议含 `target_id`/`emotion`/`intensity`/`turn` 等；返回原 entry 便于链式调用。
    """
    entry = dict(entry)
    if getattr(storage, "append_emotion", None) is None:
        logger.debug("storage 无 append_emotion，跳过 mind 记录：%s", character_id)
        return entry
    storage.append_emotion(character_id, entry)
    return entry


def format_growth_snippet(state: CharacterGrowthState) -> str:
    """
    将成长状态格式化为 prompt 友好文本，供阶段 1b 注入角色/范围 Agent。
    阶段 1a 仅作展示；非空字段逐维列出，全空返回空串。
    """
    dims: list[str] = []
    mapping = {
        "能力（power_state）": "power_state",
        "心理（mind_state）": "mind_state",
        "关系（social_state）": "social_state",
        "目标（goal_state）": "goal_state",
        "资源（resource_state）": "resource_state",
    }
    for label, key in mapping.items():
        v = getattr(state, key, None) or {}
        if v:
            dims.append(f"{label}：" + "；".join(f"{k}={val}" for k, val in v.items() if val))
    if not dims:
        return ""
    return "【成长状态】" + "\n".join(dims)


def format_present_growth_snippet(
    data_root: Path,
    characters_config: dict[str, Any] | None,
    present_character_ids: list[str],
) -> str:
    """
    汇总**在场**关键角色的成长状态，供范围（主线叙事者）prompt 注入，使叙述与角色演进一致。
    仅含非空状态、按角色名标注；全部为空则返回空串（不改变无成长场景行为）。
    """
    data_root = Path(data_root)
    present = sorted({str(x) for x in present_character_ids if x})
    if not present:
        return ""
    config = (characters_config or {}).get("characters") or []
    name_of = {str(c.get("id")): (c.get("name") or str(c.get("id"))) for c in config}
    blocks: list[str] = []
    for cid in present:
        snippet = format_growth_snippet(load_growth_state(cid, data_root))
        if snippet:
            # 去掉「【成长状态】」头，仅保留维度明细（头部与首维可能同行）。
            body = snippet[len("【成长状态】"):].strip()
            name = name_of.get(cid, cid)
            blocks.append(f"{name}（{cid}）：{body}")
    if not blocks:
        return ""
    return "【在场角色成长状态】" + "\n".join(f"\n- {b}" for b in blocks)


# --- 阶段 1b：五维语义迁移规则（设计文档 §3；确定性、非数值） ---
# 规则为"当前状态 + 事件类型 + 触发条件 -> 叙事变化 + 代价"。事件类型由关键词匹配摘要判定；
# 命中即对该角色五维子状态做语义增量，写入 `growth_state.yaml` 与 `transition_log`。
# 采用叙事语义状态（low/med/high 或计数），不做重数值化；GrowthGuard 强约束由阶段 2 承担。

_MAX_BUMP = 5  # 计数维度软上限，避免无代价无限膨胀


def _bump(state: CharacterGrowthState, dim: str, key: str, amount: int = 1, cap: int | None = None) -> int:
    """对某个计数维度累加。返回新值。"""
    sub = dict(getattr(state, dim) or {})
    try:
        cur = int(sub.get(key, 0))
    except (TypeError, ValueError):
        cur = 0
    nxt = cur + amount
    if cap is not None:
        nxt = min(nxt, cap)
    sub[key] = nxt
    setattr(state, dim, sub)
    return nxt


def _set(state: CharacterGrowthState, dim: str, key: str, value: Any) -> None:
    """以叙事语义值（如 low/med/high / 描述串）覆盖某维度条目。"""
    sub = dict(getattr(state, dim) or {})
    sub[key] = value
    setattr(state, dim, sub)


def _delta(rule_name: str, dim: str, key: str, value: Any, note: str = "") -> dict[str, Any]:
    return {"rule": rule_name, "dim": dim, "key": key, "value": value, "note": note}


# 每个规则：name, keywords（命中其一即触发）, apply(state, bundle)->list[_delta]
_RULES: list[dict[str, Any]] = [
    {
        "name": "near_death",
        "keywords": ("濒死", "重伤濒死", "劫后余生", "垂死", "九死一生", "死里逃生"),
        "apply": lambda s, b: [
            _bump(s, "power_state", "突破契机", 1, cap=3),
            _bump(s, "mind_state", "应激", 1, cap=3),
            _bump(s, "resource_state", "伤势损耗", 1, cap=_MAX_BUMP),
        ],
    },
    {
        "name": "trusted_betrayal",
        "keywords": ("背叛", "出卖", "反水", "欺骗", "栽赃", "背信"),
        "apply": lambda s, b: [
            _bump(s, "social_state", "人心之疑", 1, cap=3),
            _bump(s, "mind_state", "防御倾向", 1, cap=3),
            _bump(s, "goal_state", "目标重估", 1, cap=3),
        ],
    },
    {
        "name": "rescue_debt",
        "keywords": ("救命", "相救", "恩人", "仗义出手", "搭救"),
        "apply": lambda s, b: [
            _bump(s, "social_state", "受恩于人", 1, cap=3),
            _bump(s, "resource_state", "人情债", 1, cap=3),
        ],
    },
    {
        "name": "conflict_showdown",
        "keywords": ("对峙", "冲突", "决战", "剑拔弩张", "交手", "反目"),
        "apply": lambda s, b: [
            _bump(s, "power_state", "交手经验", 1, cap=_MAX_BUMP),
            _bump(s, "social_state", "敌对", 1, cap=3),
            _bump(s, "mind_state", "警惕", 1, cap=3),
        ],
    },
    {
        "name": "deep_loss",
        "keywords": ("丧", "死别", "遇害", "重伤不治", "阴阳两隔", "失去至亲"),
        "apply": lambda s, b: [
            _bump(s, "mind_state", "创伤", 1, cap=3),
            _bump(s, "goal_state", "动机转变", 1, cap=3),
        ],
    },
    {
        "name": "resource_gain",
        "keywords": ("得到", "获得", "寻得", "线索", "灵石", "秘笈", "至宝", "阵获"),
        "apply": lambda s, b: [_bump(s, "resource_state", "增益", 1, cap=_MAX_BUMP)],
    },
    {
        "name": "resource_loss",
        "keywords": ("损失", "赔", "败", "耗尽", "被夺", "亏空"),
        "apply": lambda s, b: [_bump(s, "resource_state", "损耗", 1, cap=_MAX_BUMP)],
    },
    {
        "name": "goal_affirmed",
        "keywords": ("领悟", "顿悟", "明悟", "了然", "决心", "起誓"),
        "apply": lambda s, b: [
            _bump(s, "goal_state", "里程碑", 1, cap=3),
            _bump(s, "mind_state", "信念", 1, cap=3),
        ],
    },
    {
        "name": "horror_trap",
        "keywords": ("陷阱", "被擒", "被困", "围困", "中毒", "危机"),
        "apply": lambda s, b: [
            _bump(s, "mind_state", "恐惧", 1, cap=3),
            _bump(s, "resource_state", "损耗", 1, cap=3),
        ],
    },
    {
        "name": "romance",
        "keywords": ("爱慕", "心动", "表白", "倾心", "相恋", "两情相悦", "情愫"),
        "apply": lambda s, b: [
            _bump(s, "social_state", "牵绊", 1, cap=3),
            _bump(s, "mind_state", "牵挂", 1, cap=3),
        ],
    },
]

_RULE_INDEX = {r["name"]: r for r in _RULES}


def match_rules_for_event(summary: str) -> list[str]:
    """
    对事件摘要命中哪些迁移规则（按顺序返回 rule 名）。summary 为空返回空。
    """
    text = (summary or "").strip()
    if not text:
        return []
    fired: list[str] = []
    for rule in _RULES:
        if any(k in text for k in rule["keywords"]):
            fired.append(rule["name"])
    return fired


def apply_growth_transition(
    state: CharacterGrowthState,
    event_bundle: dict[str, Any],
) -> tuple[CharacterGrowthState, list[str]]:
    """
    将一条事件作用到某角色当前成长状态：命中迁移规则则施加语义增量并写入 transition_log。
    返回 (state, fired_rule_names)。不修改 storage；写盘由调用方 save_growth_state 负责。
    event_bundle 建议含 summary/scope_id/turn_index。
    """
    summary = str(event_bundle.get("summary") or "")
    fired = match_rules_for_event(summary)
    log_suffix = []
    for name in fired:
        rule = _RULE_INDEX[name]
        deltas = rule["apply"](state, event_bundle) if callable(rule["apply"]) else []
        state.transition_log.append(
            {
                "rule": name,
                "turn": event_bundle.get("turn_index"),
                "scope_id": event_bundle.get("scope_id"),
                "reason": (summary[:120] or "未提供摘要"),
                "deltas": deltas,
            }
        )
        log_suffix.append(name)
    state.transition_log = state.transition_log[-100:]
    return state, log_suffix


# --- 阶段 2：GrowthGuard 强约束（设计文档 §6；确定性、非 LLM） ---
# 校验四类叙事一致性约束，校验失败的迁移**拒绝写回**或做**最小安全迁移**（钳制到界限），
# 并把「被拒/被钳」记为 transition_log 告警条目（含失败规则），满足 §7.1「被拒绝迁移原因可观测」。

# 规则语义分类（用于约束判定，与 _RULES 的触发无关）：
_BENEFIT_RULES = {"resource_gain", "goal_affirmed"}          # 纯收益：需有代价/代偿/后遗症作抵
_COST_RULES = {"resource_loss", "near_death", "horror_trap", "deep_loss", "conflict_showdown"}  # 内带损耗/创伤
_POSITIVE_SOCIAL_RULES = {"rescue_debt", "romance"}          # 正向关系（要铺垫）
_NEGATIVE_SOCIAL_RULES = {"conflict_showdown", "trusted_betrayal"}  # 负向关系
_GOAL_RULES = {"goal_affirmed", "trusted_betrayal", "deep_loss"}    # 会改目标的规则（频率冷却）

# 视为「既有代价积欠」的维度键：存在任一即认为之前已为收益付过代价
_COST_KEY_CANDIDATES = (
    ("resource_state", "损耗"), ("resource_state", "人情债"),
    ("power_state", "伤势损耗"), ("mind_state", "应激"), ("mind_state", "创伤"),
)
_COUNTING_DIMS = ("power_state", "mind_state", "social_state", "goal_state", "resource_state")


def _has_prior_cost(state: CharacterGrowthState) -> bool:
    """该角色是否已有未清的代价积欠（用于「无代价收益禁止」的既有代价豁免）。"""
    for dim, key in _COST_KEY_CANDIDATES:
        sub = getattr(state, dim) or {}
        try:
            if int(sub.get(key, 0)) > 0:
                return True
        except (TypeError, ValueError):
            pass
    return False


def _last_goal_change_turn(state: CharacterGrowthState) -> int | None:
    """最近一次目标状态变化的回合号（扫 transition_log），无则 None。"""
    last: int | None = None
    for entry in getattr(state, "transition_log") or []:
        dims = entry.get("deltas") or []
        # 1b 的 deltas 是 _bump 返回值（int 列表），不含 dim 元信息；按 rule 名判目标类更稳。
        if str(entry.get("rule")) in _GOAL_RULES:
            t = entry.get("turn")
            if isinstance(t, int) and (last is None or t > last):
                last = t
    return last


class GrowthGuard:
    """
    强约束校验器。dec 明一次迁移的允许规则集并给出告警；确定性、无需 LLM。

    约四类校验（与 §6 对应）：
      - 目标切换冷却 `goal_cooldown_turns`：目标类规则在距上次目标变动不足冷却窗口时被跳过（避免动机抖动）。
      - 无代价收益禁止 `balance_required`：纯收益规则缺代价/积欠时被跳过（避免无代价神级跳）。
      - 关系连续性：同回合同时触发正向关系与负向关系 → 跳过正向关系（避免「无事件铺垫立场反转」）。
      - 单回合跃迁边界 `per_turn_delta_cap`：apply 后对计数维度做钳制到「上限一次 + cap」的最小安全迁移。
    """

    def __init__(
        self,
        *,
        per_turn_delta_cap: int = 3,
        goal_cooldown_turns: int = 3,
        balance_required: bool = True,
    ) -> None:
        self.per_turn_delta_cap = per_turn_delta_cap
        self.goal_cooldown_turns = goal_cooldown_turns
        self.balance_required = balance_required

    def decide(
        self,
        fired: list[str],
        state: CharacterGrowthState,
        event_bundle: dict[str, Any],
    ) -> tuple[set[str], list[dict[str, Any]]]:
        """
        依据 fired 规则名与该角色当前状态，返回：
          (allowed_rule_names, decisions)
        decisions 每条含 rule/action(skipped|allowed)/reason；被 skip 的规则需在 apply 前剔除。
        """
        allowed = set(fired)
        decisions: list[dict[str, Any]] = []
        turn = event_bundle.get("turn_index")
        for name in fired:
            decisions.append({"rule": name, "action": "allowed", "reason": ""})

        # --- 关系连续性：同回合正负关系反转让正向铺垫失效 ---
        pos = _POSITIVE_SOCIAL_RULES & allowed
        neg = _NEGATIVE_SOCIAL_RULES & allowed
        if pos and neg:
            for name in pos:
                allowed.discard(name)
                decisions.append(
                    {"rule": name, "action": "skipped",
                     "reason": f"同回合触发负向关系，正向关系需事件铺垫（{name}）"}
                )

        # --- 目标切换冷却：避免动机抖动 ---
        last_goal = _last_goal_change_turn(state)
        for name in _GOAL_RULES & allowed:
            if isinstance(turn, int) and last_goal is not None and (turn - last_goal) < self.goal_cooldown_turns:
                allowed.discard(name)
                decisions.append(
                    {"rule": name, "action": "skipped",
                     "reason": f"目标切换冷却：距上次目标变动 {turn - last_goal} 回合 < {self.goal_cooldown_turns}"}
                )

        # --- 无代价收益禁止：纯收益需同事件代价或既有积欠 ---
        benefits = _BENEFIT_RULES & allowed
        if benefits and self.balance_required and not (_COST_RULES & allowed) and not _has_prior_cost(state):
            for name in benefits:
                allowed.discard(name)
                decisions.append(
                    {"rule": name, "action": "skipped",
                     "reason": f"无代价收益：本事件无代价/后遗症且无既有积欠（{name}）"}
                )

        return allowed, decisions


def apply_growth_transition_guarded(
    state: CharacterGrowthState,
    event_bundle: dict[str, Any],
    guard: GrowthGuard | None = None,
) -> tuple[CharacterGrowthState, list[str], list[dict[str, Any]]]:
    """
    GrowthGuard 约束下的迁移入口（阶段 2）。guard 为 None 时等价于未约束的 apply_growth_transition。
    返回 (state, all_fired_rule_names, decisions)。被 guard 跳过的规则不写数据增量，但以告警条目记入
    transition_log（含失败规则与原因），满足 §7.1 可观测；计数维度越界做「最小安全迁移」钳制到界限。
    """
    summary = str(event_bundle.get("summary") or "")
    fired = match_rules_for_event(summary)
    if guard is None:
        state, _ = apply_growth_transition(state, event_bundle)
        decisions: list[dict[str, Any]] = []
        return state, fired, decisions

    allowed, decisions = guard.decide(fired, state, event_bundle)
    state_before = {dim: dict(getattr(state, dim) or {}) for dim in _COUNTING_DIMS}

    log_suffix: list[str] = []
    for name in fired:
        if name not in allowed:
            continue  # 被 guard 跳过：不施加数据增量
        rule = _RULE_INDEX[name]
        deltas = rule["apply"](state, event_bundle) if callable(rule["apply"]) else []
        state.transition_log.append(
            {"rule": name, "turn": event_bundle.get("turn_index"),
             "scope_id": event_bundle.get("scope_id"),
             "reason": (summary[:120] or "未提供摘要"), "deltas": deltas}
        )
        log_suffix.append(name)

    # --- 最小安全迁移：计数维度单次净增超界则钳制 ---
    clamped: list[str] = []
    cap = guard.per_turn_delta_cap
    for dim in _COUNTING_DIMS:
        before = state_before.get(dim) or {}
        after = dict(getattr(state, dim) or {})
        for key, new in list(after.items()):
            old = before.get(key)
            if isinstance(new, int) and isinstance(old, int) and (new - old) > cap:
                after[key] = old + cap
                clamped.append(f"{dim}.{key}")
        setattr(state, dim, after)
    if clamped:
        decisions.append(
            {"rule": "per_turn_delta_cap", "action": "clamp",
             "reason": "单回合跃迁越界，最小安全迁移钳制到界限", "keys": clamped}
        )

    # --- 把 guard 决定写为告警审计条目（含被拒规则/原因） ---
    guard_entries = [d for d in decisions if d["action"] != "allowed"]
    for d in guard_entries:
        state.transition_log.append(
            {"rule": f"guard.{'clamp' if d['action']=='clamp' else 'skip'}",
             "turn": event_bundle.get("turn_index"),
             "scope_id": event_bundle.get("scope_id"),
             "reason": (summary[:120] or "未提供摘要"),
             "guard": d["rule"], "action": d["action"], "guard_reason": d.get("reason", "")}
        )
    state.transition_log = state.transition_log[-100:]
    return state, fired, decisions


def apply_growth_transition_for_turn(
    storage: Any,
    data_root: Path,
    *,
    scope_id: str,
    turn_index: int,
    present_character_ids: list[str],
    event_entry: dict[str, Any] | None = None,
    characters_config: dict[str, Any] | None = None,
    guard: GrowthGuard | None = None,
) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    """
    编排器在回合写回后调用：对每个**在场**关键角色（信息视野一致，只有亲身经历者受影响）加载成长状态、
    执行迁移（阶段 2 起受 `guard` 约束）、落盘，并把 `mind_state` 变化写入该角色 emotions 槽位。
    返回 (results, guard_audit) —— results = {character_id: fired_rule_names}；guard_audit 汇总被拒/被钳制告警。
    """
    data_root = Path(data_root)
    summary = str((event_entry or {}).get("summary") or "")
    results: dict[str, list[str]] = {}
    guard_audit: list[dict[str, Any]] = []
    for cid in sorted({str(x) for x in present_character_ids if x}):
        state = load_growth_state(cid, data_root)
        bundle = {
            "summary": summary,
            "scope_id": scope_id,
            "turn_index": turn_index,
            "character_id": cid,
        }
        state, fired, decisions = apply_growth_transition_guarded(state, bundle, guard)
        results[cid] = fired
        for d in decisions:
            d = dict(d)
            d["character_id"] = cid
            d["turn"] = turn_index
            guard_audit.append(d)
        if fired:
            save_growth_state(state, data_root)
            mind = state.mind_state or {}
            if mind and hasattr(storage, "append_emotion"):
                record_mind_emotion(
                    storage,
                    cid,
                    {
                        "emotion": "、".join(str(k) for k in mind.keys()),
                        "scope_id": scope_id,
                        "turn": turn_index,
                        "trigger": ",".join(fired),
                    },
                )
    return results, guard_audit