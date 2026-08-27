"""
OpenAI 接口 LLM 提供方：直接使用 openai 包调用 Chat Completions API。
维持自研编排；不引入 LangChain 等框架。支持 base_url 以对接国内代理或自建兼容端点。
与 docs/design/llm-and-agents.md 一致。
"""
import os
from typing import Any

from openai import OpenAI

from src.llm.base import LLMProvider


class OpenAICompatibleLLM(LLMProvider):
    """
    使用 OpenAI 官方接口（含兼容端点）的 LLM。
    API Key 从环境变量读取；base_url 可选，不设则使用官方默认。
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._model = model
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if timeout is not None:
            kwargs["timeout"] = timeout
        if max_retries is not None:
            kwargs["max_retries"] = max_retries
        self._client = OpenAI(**kwargs)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """调用 Chat Completions，返回 assistant 首条消息内容。"""
        model = kwargs.pop("model", self._model)
        messages = [{"role": "user", "content": prompt}]
        resp = self._client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        if not resp.choices:
            return ""
        return (resp.choices[0].message.content or "").strip()


def build_openai_llm_from_config(llm_options: dict) -> OpenAICompatibleLLM:
    """
    从 framework.llm_options 构建 OpenAICompatibleLLM。
    api_key 从 llm_options["api_key_env"] 指定的环境变量读取（默认 OPENAI_API_KEY）。
    """
    opts = llm_options or {}
    api_key_env = opts.get("api_key_env", "OPENAI_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ValueError(
            f"未设置环境变量 {api_key_env}，请在环境中配置 API Key 后再使用 OpenAI Provider"
        )
    model = opts.get("model", "gpt-3.5-turbo")
    base_url = opts.get("base_url") or None
    # 长上下文设定讨论、兼容端点排队时 ~30s 易读超时；未在配置中指定时放宽默认
    timeout = opts.get("timeout", 180.0)
    max_retries = opts.get("max_retries", 1)
    return OpenAICompatibleLLM(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=float(timeout) if timeout is not None else None,
        max_retries=int(max_retries) if max_retries is not None else None,
    )
