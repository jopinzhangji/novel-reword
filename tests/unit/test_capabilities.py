"""G3 能力外观面（SDD D12 §3）：统一开关读法、旧深层回退 WARN、per-novel 覆盖、默认全关等价。"""
import logging

import pytest

from src.runtime.capabilities import (
    CapabilityFlags,
    capabilities_to_dict,
    load_features,
    resolve_features,
    save_features,
)


def test_default_all_off():
    f = resolve_features(None)
    assert f is not None
    assert not f.any_on
    assert f.empty()
    assert f.bridging is False and f.evolution_pacing is False and f.alt_draft is False


def test_canonical_features_read():
    f = resolve_features({"runtime": {"features": {"evolution_pacing": True, "alt_draft": True}}})
    assert f.evolution_pacing is True
    assert f.alt_draft is True
    assert f.bridging is False  # 未设字段默认关


def test_legacy_fallback_warns(caplog):
    with caplog.at_level(logging.WARNING):
        f = resolve_features({"runtime": {"parallel_threads": {"enabled": True}}})
    assert f.bridging is True
    assert any("旧深层位置" in r.message for r in caplog.records)


def test_features_yaml_override_beats_canonical_and_legacy(tmp_path):
    root = tmp_path / "novel"
    save_features(root, {"bridging": True, "evolution_pacing": True})
    f = resolve_features({"runtime": {"features": {"evolution_pacing": False}}}, data_root=root)
    # features.yaml覆盖 优先于 runtime.features / 旧深层
    assert f.evolution_pacing is True
    assert f.bridging is True
    assert load_features(root) == {"bridging": True, "evolution_pacing": True}


def test_override_arg_highest():
    f = resolve_features({"runtime": {"features": {"react_chain": True}}}, features_override={"react_chain": False})
    assert f.react_chain is False


def test_capabilities_to_dict_and_roundtrip():
    d = capabilities_to_dict(CapabilityFlags(bridging=True))
    assert d["bridging"] is True
    assert d["evolution_pacing"] is False
    rt = CapabilityFlags(**{k: (v is True) for k, v in d.items()})
    assert rt.bridging is True and rt.evolution_pacing is False