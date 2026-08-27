"""
文心一言（百度千帆）HTTP 直连调用层：使用官方 URL 与鉴权，不依赖 OpenAI 兼容接口。
鉴权：API Key + Secret Key -> access_token；请求：POST 到配置的 chat_url，body 为 messages。
与 docs/design/llm-and-agents.md 一致；配置见 framework.llm_options。
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from src.llm.base import LLMProvider

# 百度 OAuth 与默认对话端点（文心一言 旧版 / 千帆）
DEFAULT_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
DEFAULT_CHAT_URL = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro"


def _get_access_token(api_key: str, secret_key: str, token_url: str, timeout: float = 10.0) -> str:
    """使用 API Key + Secret Key 获取 access_token。"""
    qs = f"grant_type=client_credentials&client_id={urllib.parse.quote(api_key)}&client_secret={urllib.parse.quote(secret_key)}"
    url = f"{token_url.rstrip('/')}?{qs}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    token = data.get("access_token")
    if not token:
        raise ValueError(f"获取 access_token 失败: {data}")
    return token


def _parse_chat_response(body: dict) -> str:
    """从文心/千帆响应中解析出文本。支持 result 或 choices[0].message.content。"""
    if "result" in body and isinstance(body["result"], str):
        return (body["result"] or "").strip()
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict) and "content" in msg:
            return (msg["content"] or "").strip()
    return ""


class WenxinLLM(LLMProvider):
    """
    文心一言（百度）HTTP 直连：先取 access_token，再 POST 到 chat_url。
    API Key / Secret Key 从环境变量读取；chat_url、model 等可配置。
    """

    def __init__(
        self,
        *,
        api_key: str,
        secret_key: str,
        chat_url: str = DEFAULT_CHAT_URL,
        token_url: str = DEFAULT_TOKEN_URL,
        model: str | None = None,
        timeout: float = 60.0,
        token_ttl_seconds: int = 3600 * 24 * 25,
        max_retries: int = 1,
    ) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._chat_url = chat_url.rstrip("/")
        self._token_url = token_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._token_ttl = token_ttl_seconds
        self._max_retries = max(0, int(max_retries))
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    def _ensure_token(self) -> str:
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token
        self._access_token = _get_access_token(
            self._api_key, self._secret_key, self._token_url, timeout=min(30.0, self._timeout)
        )
        self._token_expires_at = time.monotonic() + self._token_ttl
        return self._access_token

    def generate(self, prompt: str, **kwargs: Any) -> str:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            token = self._ensure_token()
            sep = "&" if "?" in self._chat_url else "?"
            url = f"{self._chat_url}{sep}access_token={urllib.parse.quote(token)}"
            payload: dict[str, Any] = {
                "messages": [{"role": "user", "content": prompt}],
            }
            if self._model:
                payload["model"] = self._model
            if "temperature" in kwargs:
                payload["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                payload["max_tokens"] = kwargs["max_tokens"]
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    data = json.loads(resp.read().decode())
                if "error_code" in data and data.get("error_code"):
                    raise RuntimeError(
                        f"文心 API 返回错误: {data.get('error_code')} {data.get('error_msg', data)}"
                    )
                return _parse_chat_response(data)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode() if e.fp else ""
                try:
                    err_json = json.loads(err_body)
                    msg = err_json.get("error_msg", err_json.get("message", err_body))
                except Exception:
                    msg = err_body or str(e)
                # HTTP 错误多为确定性错误，不做重试
                raise RuntimeError(f"文心 API 请求失败: {e.code} {msg}") from e
            except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as e:
                last_error = e
                if attempt >= self._max_retries:
                    break
                # 简单线性回退，避免长时间卡住
                time.sleep(min(0.5 * (attempt + 1), 2.0))
        raise RuntimeError(f"文心 API 请求失败（重试后）: {last_error}") from last_error


def build_wenxin_llm_from_config(llm_options: dict) -> WenxinLLM:
    """
    从 framework.llm_options 构建 WenxinLLM。
    api_key / secret_key 从 llm_options 指定的环境变量读取；
    可选：chat_url、token_url、model、timeout、api_key_env、secret_key_env。
    """
    opts = llm_options or {}
    api_key_env = opts.get("api_key_env", "WENXIN_API_KEY")
    secret_key_env = opts.get("secret_key_env", "WENXIN_SECRET_KEY")
    api_key = os.environ.get(api_key_env)
    secret_key = os.environ.get(secret_key_env)
    if not api_key:
        raise ValueError(
            f"未设置环境变量 {api_key_env}，请在环境中配置文心 API Key"
        )
    if not secret_key:
        raise ValueError(
            f"未设置环境变量 {secret_key_env}，请在环境中配置文心 Secret Key"
        )
    chat_url = (opts.get("chat_url") or DEFAULT_CHAT_URL).strip()
    token_url = (opts.get("token_url") or DEFAULT_TOKEN_URL).strip()
    model = opts.get("model")
    timeout = opts.get("timeout", 30.0)
    max_retries = opts.get("max_retries", 1)
    token_ttl = opts.get("token_ttl_seconds", 3600 * 24 * 25)
    return WenxinLLM(
        api_key=api_key,
        secret_key=secret_key,
        chat_url=chat_url,
        token_url=token_url,
        model=model,
        timeout=float(timeout) if timeout is not None else 60.0,
        max_retries=int(max_retries) if max_retries is not None else 1,
        token_ttl_seconds=int(token_ttl),
    )
