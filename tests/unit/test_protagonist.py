"""叙事主角 id 解析。"""
from src.runtime.protagonist import resolve_protagonist_id


def test_resolve_from_novel_run():
    rc = {
        "runtime": {"novel_run": {"protagonist_id": "hero"}},
        "agents": {"characters": {"enabled_ids": ["hero"]}},
    }
    chars = {"characters": [{"id": "hero", "name": "英雄"}]}
    pid, name = resolve_protagonist_id(rc, chars)
    assert pid == "hero"
    assert name == "英雄"


def test_resolve_from_is_protagonist():
    rc = {"runtime": {}, "agents": {"characters": {"enabled_ids": ["a"]}}}
    chars = {"characters": [{"id": "a", "name": "甲", "is_protagonist": True}]}
    pid, name = resolve_protagonist_id(rc, chars)
    assert pid == "a"
    assert name == "甲"


def test_resolve_none_when_unconfigured():
    rc = {"runtime": {}, "agents": {"characters": {"enabled_ids": ["x"]}}}
    chars = {"characters": [{"id": "x", "name": "X"}]}
    assert resolve_protagonist_id(rc, chars) == (None, None)


def test_multiple_is_protagonist_warns_and_uses_first(caplog):
    import logging

    rc = {"runtime": {}, "agents": {"characters": {"enabled_ids": ["a", "b"]}}}
    chars = {
        "characters": [
            {"id": "a", "name": "甲", "is_protagonist": True},
            {"id": "b", "name": "乙", "is_protagonist": True},
        ]
    }
    caplog.set_level(logging.WARNING)
    pid, name = resolve_protagonist_id(rc, chars)
    assert pid == "a" and name == "甲"
    assert any("多主角" in r.message and "未支持" in r.message for r in caplog.records)
