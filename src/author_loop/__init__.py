# 作者在环：两阶段审阅与确认（CLI 或后续 Web/API）；开书前设定阶段
# 注意：勿在包初始化时 import design_phase，否则会与 author_harness → retrieve_for_intent 形成环状依赖。
from .author_session import AuthorSession
from .cli import review_turn_result, review_memory_plan

__all__ = ["AuthorSession", "review_turn_result", "review_memory_plan", "run_design_phase"]


def __getattr__(name: str):
    if name == "run_design_phase":
        from .design_phase import run_design_phase

        return run_design_phase
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
