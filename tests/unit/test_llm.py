"""
LLM 抽象层单元测试：DummyLLM、get_llm_provider、OpenAI/文心对接（mock）。
与 TECH_IMPLEMENTATION §10、docs/design/llm-and-agents.md 一致。
"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from src.llm import LLMProvider, get_llm_provider
from src.llm.base import DummyLLM, LLMQuotaExhaustedError
from src.llm.openai_provider import OpenAICompatibleLLM, build_openai_llm_from_config
from src.llm.wenxin_provider import (
    WenxinLLM,
    build_wenxin_llm_from_config,
    _parse_chat_response,
)


def test_dummy_llm_returns_default():
    llm = DummyLLM(default_response="（壳）暂无")
    assert llm.generate("任意 prompt") == "（壳）暂无"


def test_dummy_llm_custom_response():
    llm = DummyLLM(default_response="自定义")
    assert llm.generate("") == "自定义"


def test_get_llm_provider_returns_dummy_by_default():
    provider = get_llm_provider({})
    assert isinstance(provider, DummyLLM)


def test_get_llm_provider_from_framework_llm_dummy():
    provider = get_llm_provider({"framework": {"llm": "dummy"}})
    assert isinstance(provider, LLMProvider)
    assert provider.generate("test") == "（壳）暂无"


def test_get_llm_provider_unknown_falls_back_to_dummy():
    provider = get_llm_provider({"framework": {"llm": "langchain"}})
    assert isinstance(provider, DummyLLM)


def test_get_llm_provider_openai_returns_openai_provider_when_env_set():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        provider = get_llm_provider({
            "framework": {"llm": "openai", "llm_options": {"model": "gpt-3.5-turbo"}},
        })
    assert isinstance(provider, LLMProvider)
    assert isinstance(getattr(provider, "_inner", None), OpenAICompatibleLLM)


def test_get_llm_provider_openai_compatible_returns_openai_provider_when_env_set():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        provider = get_llm_provider({
            "framework": {"llm": "openai_compatible", "llm_options": {"api_key_env": "OPENAI_API_KEY"}},
        })
    assert isinstance(provider, LLMProvider)
    assert isinstance(getattr(provider, "_inner", None), OpenAICompatibleLLM)


def test_get_llm_provider_tongyi_returns_openai_compatible_with_dashscope_defaults():
    """通义千问预设：llm=tongyi 时使用 DASHSCOPE_API_KEY、DashScope base_url、qwen-turbo。"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-dashscope"}):
        provider = get_llm_provider({"framework": {"llm": "tongyi"}})
    assert isinstance(provider, LLMProvider)
    inner = getattr(provider, "_inner", None)
    assert isinstance(inner, OpenAICompatibleLLM)
    assert inner._model == "qwen-turbo"


def test_get_llm_provider_qwen_alias_same_as_tongyi():
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-qwen"}):
        provider = get_llm_provider({"framework": {"llm": "qwen"}})
    assert isinstance(provider, LLMProvider)
    inner = getattr(provider, "_inner", None)
    assert isinstance(inner, OpenAICompatibleLLM)


def test_quota_exhausted_triggers_llm_quota_exhausted_error_and_sets_state():
    import src.llm.base as llm_base

    # 重置全局状态，避免与其他测试相互影响
    llm_base._QUOTA_EXHAUSTED = False
    llm_base._QUOTA_REMINDER_SHOWN = False

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        provider = get_llm_provider({
            "framework": {"llm": "openai", "llm_options": {"model": "gpt-3.5-turbo"}},
        })

    inner = getattr(provider, "_inner", None)
    assert isinstance(inner, OpenAICompatibleLLM)

    # 模拟额度耗尽错误（由适配层识别并抛出）
    inner.generate = MagicMock(side_effect=RuntimeError("insufficient_quota"))
    with pytest.raises(LLMQuotaExhaustedError):
        provider.generate("hello")

    # 第二次应直接进入耗尽状态，不再依赖 inner.generate
    with pytest.raises(LLMQuotaExhaustedError):
        provider.generate("hello again")


def test_build_openai_llm_from_config_raises_when_api_key_env_missing():
    # 使用不存在的环境变量名，避免依赖真实环境
    with pytest.raises(ValueError, match="未设置环境变量"):
        build_openai_llm_from_config({"api_key_env": "__NONEXISTENT_ENV_VAR_FOR_TEST__"})


def test_openai_compatible_llm_generate_returns_content_from_mock_client():
    fake_content = "这是模型返回的文本"
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = fake_content
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    with patch("src.llm.openai_provider.OpenAI", return_value=mock_client):
        llm = OpenAICompatibleLLM(api_key="sk-test", model="gpt-3.5-turbo")
        out = llm.generate("hello")
    assert out == fake_content
    mock_client.chat.completions.create.assert_called_once()
    call_kw = mock_client.chat.completions.create.call_args[1]
    assert call_kw["model"] == "gpt-3.5-turbo"
    assert call_kw["messages"] == [{"role": "user", "content": "hello"}]
