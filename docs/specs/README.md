# specifications（规约入口）

本目录用于说明 **规范级文档（Specifications）** 在仓库中的位置；**正文仍在仓库根目录**，以保持历史链接与「单仓一眼看到规约」的习惯。

| 层级 | 文档 | 说明 |
|------|------|------|
| **L0 产品规约** | [DESIGN.md](../../DESIGN.md) | 域模型、多 Agent、世界/范围、非目标 |
| **L1 技术规约** | [TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md) | 组件边界、配置与存储、主流程、测试门禁 |
| **L1 行为规约（切片）** | [author-in-loop-spec.md](./author-in-loop-spec.md) | 作者在环 MUST/SHOULD/不承诺；与 SDD 分工见该文 §1；**迭代顺序**见 **§1.1**（文档先行） |

**软件设计说明（SDD）**见 **[../design/](../design/)**（实现结构，须与上表 Spec 对齐）；**Harness 重构切片 R0–R8** 见 [author-agent-harness.md](../design/author-agent-harness.md) §6.1；**组装后上下文压缩**见 [context-compression-adaptive-layered.md](../design/context-compression-adaptive-layered.md)（**D8**）；迭代与 MVP 见 **[../planning/](../planning/)**。

分层与开发流程：[../framework/SPEC_SDD.md](../framework/SPEC_SDD.md) **§2.1**。仓库 Cursor 规则：根目录 **`.cursor/rules/doc-first-spec-sdd.mdc`**（改作者在环相关代码前默认先对齐文档并确认方案）。
