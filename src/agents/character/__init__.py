# 角色 Agent：人格、记忆、目标、独立“思考”与演进
# 壳实现：CharacterAgent + CharacterTurnOutput，输入 TurnContext，输出固定/规则，不接 LLM。

from .agent import CharacterAgent, CharacterTurnOutput

__all__ = ["CharacterAgent", "CharacterTurnOutput"]
