"""
Playwright 同步搜索：Bing 网页结果（https://www.bing.com/search）。

相较 DuckDuckGo，Bing 在国内网络环境下通常更易访问；后续可再接专用搜索 API。
页面 DOM 可能变化；失败时抛异常由上层降级。
需安装: pip install playwright && playwright install chromium
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

logger = logging.getLogger(__name__)


def search_web_bing_sync(
    query: str,
    *,
    timeout_ms: int = 20000,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """
    打开 Bing 搜索页并解析有机结果（li.b_algo）标题、链接与摘要。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(
            "未安装 playwright。请执行: pip install playwright && playwright install chromium"
        ) from e

    q = (query or "").strip()
    if not q:
        return []

    url = f"https://www.bing.com/search?q={quote(q, safe='')}"
    out: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        page = context.new_page()
        try:
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

            # 可选：Cookie / 同意横幅（失败则忽略）
            try:
                page.locator("#bnp_btn_accept").click(timeout=2000)
            except Exception:
                try:
                    page.locator("#acceptButton").click(timeout=1500)
                except Exception:
                    pass

            rows = page.locator("li.b_algo").all()
            if not rows:
                rows = page.locator("#b_results > li.b_algo").all()

            for row in rows[:max_results]:
                try:
                    title = ""
                    href = ""
                    tl = row.locator("h2 a")
                    if tl.count() == 0:
                        tl = row.locator(".b_algoheader a")
                    if tl.count() > 0:
                        link = tl.first
                        title = link.inner_text(timeout=3000).strip()
                        href = (link.get_attribute("href") or "").strip()

                    snippet = ""
                    sn_block = row.locator("div.b_caption p")
                    if sn_block.count() == 0:
                        sn_block = row.locator(".b_caption p")
                    if sn_block.count() == 0:
                        sn_block = row.locator("p")
                    if sn_block.count() > 0:
                        snippet = sn_block.first.inner_text(timeout=3000).strip()

                    if title or snippet:
                        out.append({"title": title, "url": href, "snippet": snippet})
                except Exception as e:
                    logger.debug("解析单条 Bing 结果失败: %s", e)
                    continue
        finally:
            context.close()
            browser.close()

    return out


# 旧名兼容（曾用 DuckDuckGo；现统一走 Bing）
def search_duckduckgo_html_sync(
    query: str,
    *,
    timeout_ms: int = 20000,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """已弃用别名，请使用 search_web_bing_sync。"""
    return search_web_bing_sync(query, timeout_ms=timeout_ms, max_results=max_results)
