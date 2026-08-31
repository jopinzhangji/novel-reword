"""
G3 用户可调收敛：统一「能力开关」外观面（capability surface）。

把散落于 `runtime_config` 深层的各类增强门闩聚合为单一规范入口：
- `CapabilityFlags`：全布尔、全默认关、可判空、可序列化。
- `resolve_features`：唯一规范读法——`runtime.features.<name>`；缺失字段回退**旧深层位置**并一次性 `WARN`；
  per-novel `config/features.yaml` 与调用方 `features_override` 依次最后覆盖。
- `load_features` / `save_features`：小说级覆盖文件读写，作者不侵入合并后 runtime 深层即可开关能力。

确定性、无 LLM、不写盘（除显式 `save_features`）。默认（无任何 features）→ 逐字节等价旧版。
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# 旧深层位置回退表：`name -> (父字典路由, 键)`。命中即一次性 WARN「请迁移到 per-novel config/features.yaml」。
_LEGACY_LOOKUPS: dict[str, tuple[tuple[str, ...], str]] = {
    "bridging": (("runtime", "parallel_threads"), "enabled"),
    "off_screen_batch": (("runtime", "parallel_threads"), "enabled"),  # trigger=batch 时才随批（run_novel 判）
    "evolution_pacing": (("runtime", "evolution_pacing"), "enabled"),
    "beat_tags_to_growth": (("runtime", "evolution_pacing"), "beat_tags_to_growth"),
    "internet_search": (("setting_research", "internet_search"), "enabled"),
    "react_chain": (("runtime", "react_chain"), "enabled"),
    "memory_layers": (("runtime", "memory_layers"), "enabled"),
    "info_view": (("runtime", "info_view"), "enabled"),
    "semantic_edges": (("runtime", "semantic_edges"), "enabled"),
}


@dataclass(frozen=True)
class CapabilityFlags:
    """能力开关聚合。全默认关；可判空（`empty`）；与深层旧配置解耦的规范读法见 `resolve_features`。"""

    # G1 屏外线/并列主线
    bridging: bool = False
    off_screen_batch: bool = False
    # G2 演进层 ↔ 叙事策略层耦闸
    evolution_pacing: bool = False
    beat_tags_to_growth: bool = False
    # U-6 回合内二次反应链
    react_chain: bool = False
    # 联网检索
    internet_search: bool = False
    # 记忆分层 / 信息视野 / 语义关系边
    memory_layers: bool = False
    info_view: bool = False
    semantic_edges: bool = False
    # 候选备选稿（§4.1）
    alt_draft: bool = False

    def empty(self) -> bool:
        """无任何开关处于开启态（默认态判等用）。"""
        return not self.any_on

    @property
    def any_on(self) -> bool:
        return any(bool(getattr(self, f.name)) for f in fields(self))

    def to_dict(self) -> dict[str, bool]:
        if is_dataclass(self):
            return {k: bool(v) for k, v in asdict(self).items()}
        return {k: bool(getattr(self, k)) for k in _FIELD_ORDER}


_FIELD_ORDER = tuple(f.name for f in fields(CapabilityFlags))


def _deep_get(d: dict | None, route: tuple[str, ...], key: str) -> Any | None:
    if not d:
        return None
    cur: Any = d
    for part in route:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur.get(key) if isinstance(cur, dict) else None


def load_features(data_root: Path | str | None) -> dict[str, Any]:
    """读 per-novel `config/features.yaml`（仅返回真布尔键；缺失/异常→空 dict）。"""
    if data_root is None:
        return {}
    path = Path(data_root) / "config" / "features.yaml"
    try:
        if not path.is_file():
            return {}
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return {}
        return {str(k): bool(v) for k, v in raw.items() if isinstance(v, (bool, int))}
    except Exception as exc:  # noqa: BLE001 读覆盖文件失败不应炸主流程
        logger.warning("读取 features.yaml 失败，按空覆盖处理：%s（%s）", path, exc)
        return {}


def save_features(data_root: Path | str, override: dict[str, Any] | None) -> Path | None:
    """把覆盖键写 per-novel `config/features.yaml`（仅真布尔键；整表原子写，非整树 runtime 改写）。"""
    if data_root is None:
        return None
    override = {str(k): bool(v) for k, v in (override or {}).items() if isinstance(v, (bool, int))}
    root = Path(data_root)
    path = root / "config" / "features.yaml"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(override, allow_unicode=True, sort_keys=True), encoding="utf-8")
        return path
    except Exception as exc:  # noqa: BLE001
        logger.warning("写出 features.yaml 失败：%s（%s）", path, exc)
        return None


def resolve_features(
    runtime_config: dict[str, Any] | None,
    *,
    features_override: dict[str, Any] | None = None,
    data_root: Path | str | None = None,
) -> CapabilityFlags:
    """
    **唯一规范读法**。优先级（低→高）：默认全关 → 旧深层位置回退（命中 WARN）→ `runtime.features` →
    per-novel `config/features.yaml`（data_root 给定时）→ `features_override`（会话内作者改动，最高）。
    """
    rc = runtime_config or {}
    # 1) 规范位置 `runtime.features`（兼容顶层 `features`）
    canonical: dict[str, Any] = {}
    _inner = rc.get("runtime") if isinstance(rc.get("runtime"), dict) else rc
    _canon = _inner.get("features")
    if isinstance(_canon, dict):
        canonical = {str(k): bool(v) for k, v in _canon.items() if isinstance(v, (bool, int))}

    # 2) 逐字段：规范有则用规范；否则回退旧深层位置并一次性 WARN。
    values: dict[str, bool] = {}
    for name in _FIELD_ORDER:
        if name in canonical:
            values[name] = canonical[name]
            continue
        route, key = _LEGACY_LOOKUPS.get(name, ((), ""))
        found = _deep_get(rc, route, key) if route else None
        if isinstance(found, (bool, int)):
            logger.warning(
                "[G3] 能力开关 '%s' 命中旧深层位置 %s，建议收敛到 per-novel config/features.yaml（runtime.features）",
                name,
                "/".join(route) + "." + key,
            )
            values[name] = bool(found)
        else:
            values[name] = False

    # 3) per-novel features.yaml 覆盖（data_root 给定时）
    yaml_ov = load_features(data_root) if data_root is not None else {}
    for name in _FIELD_ORDER:
        if name in yaml_ov:
            values[name] = bool(yaml_ov[name])

    # 4) 会话内 features_override（最高优先级）
    for name in _FIELD_ORDER:
        if features_override and name in features_override:
            values[name] = bool(features_override[name])

    return CapabilityFlags(**values)


def capabilities_to_dict(flags: CapabilityFlags) -> dict[str, bool]:
    """序列化（供 /system/config 读、features.yaml 落盘、日志观测）。"""
    return flags.to_dict()