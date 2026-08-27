"""
LLM 抽象层：Provider 接口与占位实现，供 Agent 接入 LangChain/LlamaIndex 时复用。
与 TECH_IMPLEMENTATION §10 一致；当前仅提供 dummy 实现，不引入外部 API 依赖。
"""
from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """LLM 提供方抽象：根据 prompt 生成文本。"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """根据 prompt 生成一段文本。"""
        ...


class DummyLLM(LLMProvider):
    """占位实现：固定返回，与当前 Agent 壳行为一致，不调用任何 API。"""

    def __init__(self, default_response: str = "（壳）暂无") -> None:
        self.default_response = default_response

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return self.default_response


# 通义千问（DashScope）OpenAI 兼容模式默认端点与键名，见阿里云文档
TONGYI_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
TONGYI_DEFAULT_API_KEY_ENV = "DASHSCOPE_API_KEY"
TONGYI_DEFAULT_MODEL = "qwen-turbo"


class LLMQuotaExhaustedError(RuntimeError):
    """LLM 额度/配额耗尽（计费余额不足/硬限制达到/insufficient_quota 等）。"""


_QUOTA_EXHAUSTED = False
_QUOTA_REMINDER_SHOWN = False


def _looks_like_quota_exhausted_message(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    # OpenAI / 兼容接口常见字段（中英文混合都尽量覆盖）
    quota_markers = [
        "insufficient_quota",
        "quota",
        "billing",
        "hard limit",
        "rate limit",
        "too many requests",
        "balance",
        "insufficient balance",
        "insufficient_balance",
    ]
    cn_markers = ["配额", "额度", "余额", "用尽", "耗尽", "不足"]
    if any(m in t for m in cn_markers) and any(m in t for m in quota_markers):
        return True
    if any(m in t for m in ["insufficient_quota", "insufficient balance", "insufficient_balance"]):
        return True
    if ("quota" in t or "配额" in text or "额度" in text or "余额" in text) and any(
        k in t for k in ["exceeded", "exhausted", "hard limit", "limit", "不足", "用尽", "耗尽"]
    ):
        return True
    return False


def _is_quota_exhausted_error(e: Exception) -> bool:
    status = getattr(e, "status_code", None)
    if status in (402, 403, 429):
        # 仍然用文本做二次过滤，避免把所有 429 都当成“额度用尽”
        return _looks_like_quota_exhausted_message(str(e))
    return _looks_like_quota_exhausted_message(str(e))


class QuotaAwareLLMProvider(LLMProvider):
    """
    给真实 Provider 加一层“额度耗尽提醒/回退”：
    - 第一次检测到额度/配额耗尽：向控制台打印清晰提醒，并设置全局状态
    - 后续直接抛出 LLMQuotaExhaustedError（不重复打印）
    """

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner

    def generate(self, prompt: str, **kwargs: Any) -> str:
        global _QUOTA_EXHAUSTED, _QUOTA_REMINDER_SHOWN
        if _QUOTA_EXHAUSTED:
            raise LLMQuotaExhaustedError("模型额度已耗尽（已触发过一次提醒）")

        try:
            return self._inner.generate(prompt, **kwargs)
        except Exception as e:
            if _is_quota_exhausted_error(e):
                _QUOTA_EXHAUSTED = True
                if not _QUOTA_REMINDER_SHOWN:
                    _QUOTA_REMINDER_SHOWN = True
                    msg = (
                        "\n[模型额度/配额已用尽提醒]\n"
                        "LLM 返回“额度/配额用尽/余额不足”类错误。\n"
                        "将把后续生成自动回退为占位输出。\n"
                        "请检查：1) API Key 是否正确；2) 是否需要充值/恢复额度；3) 或把 framework.llm 配置为 `dummy` 继续调试。\n"
                    )
                    try:
                        print(msg)
                    except Exception:
                        pass
                raise LLMQuotaExhaustedError(str(e)) from e
            raise


def get_llm_provider(runtime_config: dict) -> LLMProvider:
    """
    从运行时配置获取 LLM 提供方。
    配置约定：framework.llm 为 "dummy" | "openai" | "openai_compatible" | "tongyi" | "qwen" | "wenxin" | "ernie"；
    framework.llm_options 见各 Provider 说明。
    - tongyi/qwen：通义千问，使用 DashScope OpenAI 兼容接口，默认 base_url、DASHSCOPE_API_KEY、qwen-turbo，可被 llm_options 覆盖。
    - openai：model、api_key_env、base_url。
    - wenxin：文心 HTTP 直连，api_key_env、secret_key_env、chat_url、token_url。
    密钥仅从环境变量读取。
    """
    framework = runtime_config.get("framework") or {}
    llm_key = (framework.get("llm") or "dummy").strip().lower()
    if llm_key in ("dummy", "custom", ""):
        return DummyLLM()
    # 通义：tongyi、qwen 或 qwen 开头的模型名（如 qwen-plus、qwen-turbo）均走 DashScope
    if llm_key in ("tongyi", "qwen") or llm_key.startswith("qwen"):
        from src.llm.openai_provider import build_openai_llm_from_config
        opts = dict(framework.get("llm_options") or {})
        opts.setdefault("api_key_env", TONGYI_DEFAULT_API_KEY_ENV)
        opts.setdefault("base_url", TONGYI_DEFAULT_BASE_URL)
        opts.setdefault("model", llm_key if llm_key.startswith("qwen") and len(llm_key) > 4 else TONGYI_DEFAULT_MODEL)
        inner = build_openai_llm_from_config(opts)
        return QuotaAwareLLMProvider(inner)
    if llm_key in ("openai", "openai_compatible"):
        from src.llm.openai_provider import build_openai_llm_from_config
        llm_options = framework.get("llm_options") or {}
        inner = build_openai_llm_from_config(llm_options)
        return QuotaAwareLLMProvider(inner)
    if llm_key in ("wenxin", "ernie"):
        from src.llm.wenxin_provider import build_wenxin_llm_from_config
        llm_options = framework.get("llm_options") or {}
        inner = build_wenxin_llm_from_config(llm_options)
        return QuotaAwareLLMProvider(inner)
    return DummyLLM()
