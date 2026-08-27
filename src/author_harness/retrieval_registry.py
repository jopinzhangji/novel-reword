"""
R4：意图 → 检索工具链登记（RetrievalRouter 骨架）。

具体读盘仍由 ``author_loop.retrieve_for_intent`` 内建函数实现；本模块只提供**稳定工具名**
与 **intent → 工具序列** 映射，便于扩展 MAIN_WRITING 等阶段时增表不改核心循环。

**注意**：下列 ``TOOL_*`` 是**检索源逻辑名**，不是目录名；落地路径由 ``retrieve_for_intent`` 与
``config_dir`` / ``current_novel`` / ``get_book_root`` 共同决定——**多数在作品 config，
只有 ``book_setting_md`` 对应正文树下的 ``book/setting/*.md``**（见下表）。
"""
from __future__ import annotations

from src.author_loop.classify_intent import (
    INTENT_EDIT_SETTING_FILES,
    INTENT_INPUT_IDEA_DISCUSS,
    INTENT_REVIEW_REVISE,
    INTENT_SAVE_PROGRESS,
)

# 工具名与 retrieve_for_intent 内部 builder 一一对应（文档 / 单测可断言）。
# 典型挂载（绑定小说时）：
#   world / setting_research / author_interaction_state → 小说目录下 config/（或解析用的 config_dir）
#   design_session_meta → 编排 config_dir 下 design_session.yaml
#   book_setting_md → data_root 下该书 book/setting/*.md（归档设定稿，非「config 里那本小说的 yaml」）
TOOL_WORLD = "world"
TOOL_SETTING_RESEARCH = "setting_research"
TOOL_BOOK_SETTING_MD = "book_setting_md"
TOOL_AUTHOR_INTERACTION_STATE = "author_interaction_state"
TOOL_DESIGN_SESSION_META = "design_session_meta"
# R7c：正篇审阅「据反馈修订」——最近范围事件摘要 + 作者在环 digest（只读）
TOOL_SCOPE_RECENT_EVENTS = "scope_recent_events"
# I5：设定类讨论在 retrieve_for_intent 中可选追加（见 runtime.author_harness.internet_search）
TOOL_INTERNET_PLAYWRIGHT = "internet_playwright"

DESIGN_MAIN_SETTING_TOOLS: tuple[str, ...] = (
    TOOL_WORLD,
    TOOL_SETTING_RESEARCH,
    TOOL_BOOK_SETTING_MD,
)
DESIGN_MAIN_SAVE_TOOLS: tuple[str, ...] = (
    TOOL_AUTHOR_INTERACTION_STATE,
    TOOL_DESIGN_SESSION_META,
)

MAIN_WRITING_REVIEW_TOOLS: tuple[str, ...] = (
    TOOL_SCOPE_RECENT_EVENTS,
    TOOL_AUTHOR_INTERACTION_STATE,
)

INTENT_RETRIEVAL_TOOL_CHAINS: dict[str, tuple[str, ...]] = {
    INTENT_INPUT_IDEA_DISCUSS: DESIGN_MAIN_SETTING_TOOLS,
    INTENT_EDIT_SETTING_FILES: DESIGN_MAIN_SETTING_TOOLS,
    INTENT_SAVE_PROGRESS: DESIGN_MAIN_SAVE_TOOLS,
    INTENT_REVIEW_REVISE: MAIN_WRITING_REVIEW_TOOLS,
}
