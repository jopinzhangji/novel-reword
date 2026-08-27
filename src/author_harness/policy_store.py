"""
I1：PolicyStore（最小实现）

目标：提供可版本化、可加载、可分层解析的策略存储，不改变现有写作行为。
本模块只做数据组织；实际注入由后续 I2 PolicyAssembler 接入。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyStoreConfig:
    """策略存储快照（已归一化）。"""

    version: str
    global_rules: list[str]
    novel_rules: dict[str, list[str]]
    phase_rules: dict[str, list[str]]
    intent_rules: dict[str, list[str]]
    default_pace_mode: str
    allow_dynamic_pace_adjust: bool

    def resolve_rules(
        self,
        *,
        novel_profile: str | None = None,
        phase: str | None = None,
        intent_id: str | None = None,
    ) -> list[str]:
        """
        按层叠顺序解析规则（global -> novel -> phase -> intent）。
        去重保序，供 I2 组装器直接消费。
        """
        out: list[str] = []
        out.extend(self.global_rules)
        if novel_profile:
            out.extend(self.novel_rules.get(novel_profile, []))
        if phase:
            out.extend(self.phase_rules.get(phase, []))
        if intent_id:
            out.extend(self.intent_rules.get(intent_id, []))
        return _dedupe_keep_order(out)

    def resolve_pace_mode(self, requested_mode: str | None = None) -> str:
        """
        解析当前回合节奏模式。
        - 未请求时返回默认值；
        - 允许动态调整时接受请求值；
        - 禁止动态调整时始终使用默认值。
        """
        if not requested_mode:
            return self.default_pace_mode
        mode = str(requested_mode).strip().lower()
        if mode not in {"slow_burn", "balanced", "push"}:
            return self.default_pace_mode
        if self.allow_dynamic_pace_adjust:
            return mode
        return self.default_pace_mode


def load_policy_store_from_runtime(runtime_config: dict[str, Any]) -> PolicyStoreConfig:
    """
    从 runtime 配置加载策略存储。

    兼容两种路径：
    1) runtime.author_harness.policy_store（推荐）
    2) runtime.policy_store（兼容）
    """
    inner = runtime_config.get("runtime") if isinstance(runtime_config, dict) else None
    inner = inner if isinstance(inner, dict) else runtime_config
    if not isinstance(inner, dict):
        inner = {}
    ah = inner.get("author_harness")
    ah = ah if isinstance(ah, dict) else {}
    raw = ah.get("policy_store")
    if not isinstance(raw, dict):
        raw = inner.get("policy_store")
    raw = raw if isinstance(raw, dict) else {}
    return PolicyStoreConfig(
        version=str(raw.get("version") or "v1"),
        global_rules=_to_rule_list(raw.get("global_rules")),
        novel_rules=_to_rule_mapping(raw.get("novel_rules")),
        phase_rules=_to_rule_mapping(raw.get("phase_rules")),
        intent_rules=_to_rule_mapping(raw.get("intent_rules")),
        default_pace_mode=_to_pace_mode(raw.get("default_pace_mode")),
        allow_dynamic_pace_adjust=bool(raw.get("allow_dynamic_pace_adjust", True)),
    )


def _to_rule_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for x in value:
        sx = str(x or "").strip()
        if sx:
            out.append(sx)
    return out


def _to_rule_mapping(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for k, v in value.items():
        sk = str(k or "").strip()
        if not sk:
            continue
        rules = _to_rule_list(v)
        if rules:
            out[sk] = rules
    return out


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _to_pace_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    if mode in {"slow_burn", "balanced", "push"}:
        return mode
    return "balanced"

