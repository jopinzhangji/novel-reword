"""G4 Novel-Data 工作台：后端确定性 Read/写口服务层（SDD D13 §5）。

纯 Python、无 LLM、无 Web 依赖、可单测。FastAPI router（G4b）对本包做薄包装即可。
每本书以「novel_root = data/novels/<slug>/」为基准，内部依既有模块的盘符约定
（book/…/graph.yaml、book/characters/<id>/{growth_state,threads}.yaml、
book/outline/{outline,progress}.yaml、book/characters/<id>/events/turn_*.md 等）读取。
"""