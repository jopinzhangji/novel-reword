"""digest_compress_llm：摘要 LLM 压缩与回退。"""

from unittest.mock import patch

from src.llm.base import DummyLLM

from src.author_loop.digest_compress_llm import (
    compress_round_digest_fields,
    digest_llm_compress_enabled,
)


def test_disabled_returns_original():
    rc = {"runtime": {"author_interaction": {"digest_llm_compress": False}}}
    a, b, c, d = compress_round_digest_fields(
        rc,
        interaction="长" * 100,
        system_response="s",
        execution="e",
        open_issues=["x"],
    )
    assert a == "长" * 100 and b == "s" and c == "e" and d == ["x"]
    assert digest_llm_compress_enabled(rc) is False


def test_dummy_returns_original():
    rc = {"runtime": {"framework": {"llm": "dummy"}}}
    with patch("src.llm.get_llm_provider", return_value=DummyLLM()):
        a, b, c, d = compress_round_digest_fields(
            rc,
            interaction="i",
            system_response="s",
            execution="e",
            open_issues=[],
        )
    assert (a, b, c) == ("i", "s", "e")


class _FakeProvider:
    def generate(self, prompt: str, **kwargs) -> str:
        return (
            '{"interaction":"短","system_response":"短2","execution":"短3","open_issues":["a"]}'
        )


def test_llm_json_applied():
    rc = {"runtime": {}}
    with patch("src.llm.get_llm_provider", return_value=_FakeProvider()):
        a, b, c, d = compress_round_digest_fields(
            rc,
            interaction="很长原文",
            system_response="很长",
            execution="很长",
            open_issues=["old"],
        )
    assert a == "短" and b == "短2" and c == "短3" and d == ["a"]
