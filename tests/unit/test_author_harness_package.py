"""R1/R2：Harness 包可导入；PromptAssembler 与 M4 格式化对拍。"""

import src.author_harness as ah
from src.author_harness.prompt_assembler import assemble_retrieval_prompt_block
from src.author_loop.retrieve_for_intent import (
    RetrievalSnippet,
    format_snippets_design_discussion,
    format_snippets_for_prompt,
)


def test_package_exports_assembler() -> None:
    assert hasattr(ah, "assemble_retrieval_prompt_block")
    assert ah.assemble_retrieval_prompt_block is assemble_retrieval_prompt_block
    assert hasattr(ah, "apply_design_main_menu_ingress")
    assert hasattr(ah, "apply_main_writing_review_ingress")
    assert hasattr(ah, "AuthorHarness")


def test_assemble_retrieval_prompt_block_empty() -> None:
    assert assemble_retrieval_prompt_block([]) == ""


def test_assemble_retrieval_prompt_block_matches_legacy_formatter() -> None:
    snippets = [
        RetrievalSnippet(source="world.yaml", text="世界名: X"),
        RetrievalSnippet(source="a.md", text="hello", truncated=True),
    ]
    assert assemble_retrieval_prompt_block(snippets) == format_snippets_for_prompt(snippets)


def test_assemble_retrieval_prompt_block_design_discussion_layout() -> None:
    snippets = [
        RetrievalSnippet(source="book/setting/note.md（#压缩摘要）", text="要点"),
        RetrievalSnippet(source="world.yaml", text="世界名: X"),
    ]
    want = format_snippets_design_discussion(snippets)
    got = assemble_retrieval_prompt_block(snippets, layout="design_discussion")
    assert got == want
    assert "「归档摘录」" in got
    assert "① 世界配置摘要" in got
