"""
上一轮摘要的 LLM 压缩（docs/design/author-interaction.md §7.4 / M6 能力下沉）。

不截断原文；仅在配置允许且存在非 Dummy LLM 时调用；失败或 Dummy 时返回原始字段。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _runtime_author_interaction(runtime_config: dict) -> dict[str, Any]:
    rt = runtime_config.get("runtime") if isinstance(runtime_config.get("runtime"), dict) else {}
    if not isinstance(rt, dict):
        rt = {}
    ai = rt.get("author_interaction")
    return ai if isinstance(ai, dict) else {}


def digest_llm_compress_enabled(runtime_config: dict) -> bool:
    """默认开启；可在 runtime.author_interaction.digest_llm_compress 设为 false 以关闭（仍完整落盘，不经 LLM）。"""
    cfg = _runtime_author_interaction(runtime_config)
    if "digest_llm_compress" in cfg:
        return bool(cfg["digest_llm_compress"])
    return True


def _extract_json_object(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    m = re.search(r"```(?:json)?\s*\n(.*?)```", s, re.DOTALL)
    if m:
        s = m.group(1).strip()
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def compress_round_digest_fields(
    runtime_config: dict,
    *,
    interaction: str,
    system_response: str,
    execution: str,
    open_issues: list[str] | None,
) -> tuple[str, str, str, list[str]]:
    """
    使用 LLM 将三段摘要压缩为更短中文要点；open_issues 同步压缩为短列表。
    任一环节跳过或失败时返回原始参数（不截断）。
    """
    issues = list(open_issues or [])
    if not digest_llm_compress_enabled(runtime_config):
        return interaction, system_response, execution, issues

    try:
        from src.llm import get_llm_provider
        provider = get_llm_provider(runtime_config)
    except Exception as e:
        logger.debug("digest LLM 跳过（get_llm_provider）: %s", e)
        return interaction, system_response, execution, issues

    if provider.__class__.__name__ == "DummyLLM":
        return interaction, system_response, execution, issues

    oi_text = "\n".join(f"- {x}" for x in issues) if issues else "（无）"
    prompt = (
        "你是写作会话摘要员。将下列「原始记录」压缩为更短的中文要点，供下一轮入口分类使用；"
        "保留关键事实与决策，删去冗余修辞，不要编造不存在的信息。\n"
        "必须只输出一个 JSON 对象，不要其它文字，键为："
        'interaction, system_response, execution, open_issues（字符串数组，无则 []）。\n\n'
        f"【interaction】\n{interaction}\n\n"
        f"【system_response】\n{system_response}\n\n"
        f"【execution】\n{execution}\n\n"
        f"【open_issues】\n{oi_text}\n"
    )
    try:
        raw = provider.generate(prompt)
        data = _extract_json_object(raw) or {}
        if not isinstance(data, dict):
            return interaction, system_response, execution, issues
        ni = data.get("interaction")
        ns = data.get("system_response")
        ne = data.get("execution")
        noi = data.get("open_issues")
        if not isinstance(ni, str) or not isinstance(ns, str) or not isinstance(ne, str):
            logger.warning("digest LLM 返回 JSON 缺字段或非字符串，使用原文")
            return interaction, system_response, execution, issues
        new_issues: list[str] = []
        if isinstance(noi, list):
            new_issues = [str(x).strip() for x in noi if str(x).strip()]
        elif isinstance(noi, str) and noi.strip():
            new_issues = [noi.strip()]
        else:
            new_issues = issues
        return ni, ns, ne, new_issues
    except Exception as e:
        logger.warning("digest LLM 压缩失败，使用原文: %s", e)
        return interaction, system_response, execution, issues
