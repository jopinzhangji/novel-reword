# 世界 Agent：世界状态、事件簿、因果与一致性、世界演进
# 范围 Agent 壳：ScopeAgent + ScopeTurnOutput，输入 TurnContext，输出固定/规则，不接 LLM。

from .agent import ScopeAgent, ScopeTurnOutput

__all__ = ["ScopeAgent", "ScopeTurnOutput"]
