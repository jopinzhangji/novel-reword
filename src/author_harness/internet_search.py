"""
I5：受控联网检索（Playwright 首版；后续可切换专用搜索 API）。

- 默认关闭，由 runtime.author_harness.internet_search 控制。
- 仅用于设定阶段「输入想法 / 编辑设定」等讨论类 intent 的检索增强（见 retrieve_for_intent）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


def _truncate_local(s: str, max_chars: int) -> tuple[str, bool]:
    s = (s or "").strip()
    if len(s) <= max_chars:
        return s, False
    return s[: max_chars - 1] + "…", True


@dataclass(frozen=True)
class InternetFetchResult:
    source: str
    text: str
    truncated: bool


@dataclass(frozen=True)
class InternetSearchSettings:
    enabled: bool
    provider: str
    max_chars: int
    timeout_ms: int
    max_results: int
    trust_level: str
    min_query_tokens: int
    #: True：须分类器打上 internet_search_needed 才触发联网（避免每轮冗余检索）
    require_classifier_signal: bool


def load_internet_search_settings(runtime_config: dict[str, Any]) -> InternetSearchSettings:
    inner = runtime_config.get("runtime") if isinstance(runtime_config.get("runtime"), dict) else {}
    if not isinstance(inner, dict):
        inner = {}
    ah = inner.get("author_harness")
    ah = ah if isinstance(ah, dict) else {}
    raw = ah.get("internet_search")
    raw = raw if isinstance(raw, dict) else {}
    provider = str(raw.get("provider") or "playwright").strip().lower()
    max_chars = raw.get("max_chars")
    if not isinstance(max_chars, int) or max_chars < 200:
        max_chars = 1200
    max_chars = min(max_chars, 8000)
    timeout_ms = raw.get("timeout_ms")
    if not isinstance(timeout_ms, int) or timeout_ms < 3000:
        timeout_ms = 20000
    timeout_ms = min(timeout_ms, 120000)
    max_results = raw.get("max_results")
    if not isinstance(max_results, int) or max_results < 1:
        max_results = 5
    max_results = min(max_results, 10)
    min_q = raw.get("min_query_tokens")
    if not isinstance(min_q, int) or min_q < 0:
        min_q = 1
    min_q = min(min_q, 8)
    trust = str(raw.get("trust_level") or "low").strip().lower()
    if trust not in {"low", "medium", "high"}:
        trust = "low"
    rc = raw.get("require_classifier_signal")
    if rc is None:
        require_classifier_signal = True
    else:
        require_classifier_signal = bool(rc)
    return InternetSearchSettings(
        enabled=bool(raw.get("enabled", False)),
        provider=provider,
        max_chars=max_chars,
        timeout_ms=timeout_ms,
        max_results=max_results,
        trust_level=trust,
        min_query_tokens=min_q,
        require_classifier_signal=require_classifier_signal,
    )


def fetch_internet_snippet_playwright(
    query: str,
    *,
    budget: int,
    settings: InternetSearchSettings,
) -> InternetFetchResult | None:
    """
    使用 Playwright 抓取 Bing 网页搜索结果摘要；失败时返回说明性片段（不抛异常）。
    """
    from src.author_harness.playwright_search import search_web_bing_sync

    q = (query or "").strip()
    if not q:
        return None

    lines: list[str] = [
        f"trust_level={settings.trust_level}",
        f"provider={settings.provider}",
        f"engine=bing",
        "",
    ]
    try:
        rows = search_web_bing_sync(
            q,
            timeout_ms=settings.timeout_ms,
            max_results=settings.max_results,
        )
    except Exception as e:
        logger.info("Playwright 联网检索失败（已降级）: %s", e)
        t, trunc = _truncate_local(
            f"（联网检索失败: {e}）",
            budget,
        )
        return InternetFetchResult(source="internet:playwright:bing", text=t, truncated=trunc)

    if not rows:
        t, trunc = _truncate_local("（联网检索无结果或页面结构已变化）", budget)
        return InternetFetchResult(source="internet:playwright:bing", text=t, truncated=trunc)

    for i, row in enumerate(rows, 1):
        title = (row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        snippet = (row.get("snippet") or "").strip()
        lines.append(f"[{i}] {title}")
        if url:
            lines.append(f"    url: {url}")
        if snippet:
            lines.append(f"    {snippet}")
        lines.append("")

    body = "\n".join(lines).strip()
    t, trunc = _truncate_local(body, min(budget, settings.max_chars))
    return InternetFetchResult(
        source="internet:playwright:bing",
        text=t,
        truncated=trunc,
    )
