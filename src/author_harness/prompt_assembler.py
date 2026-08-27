"""
将结构化检索结果拼成可注入 LLM 的文本块（PromptAssembler 最小切片，R2）。

后续在此扩展 digest、阶段 system 模板等；设定主菜单接线见 R3（design_phase）。
"""
from __future__ import annotations

from collections.abc import Sequence

from src.author_loop.retrieve_for_intent import (
    RetrievalSnippet,
    format_snippets_design_discussion,
    format_snippets_for_prompt,
)


def assemble_retrieval_prompt_block(
    snippets: Sequence[RetrievalSnippet],
    *,
    layout: str = "default",
) -> str:
    """
    把检索片段格式化为单段 prompt 补充块。

    - ``default``：``format_snippets_for_prompt``（主菜单 Harness、审阅等）。
    - ``design_discussion``：分层编号 + 固定阅读顺序，供 ``discuss_freely`` 归档摘录。
    """
    seq = list(snippets)
    if layout == "design_discussion":
        return format_snippets_design_discussion(seq)
    return format_snippets_for_prompt(seq)
