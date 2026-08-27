# 作者在环产品规约（Specification）

**层级**：L1 行为规约（与根目录 [TECH_IMPLEMENTATION.md](../../TECH_IMPLEMENTATION.md) §6 配套；产品愿景见 [DESIGN.md](../../DESIGN.md) §6.x）  
**版本**：2026-05-01  
**非本文范围**：具体类名、函数签名、提示词全文——见 L2 SDD（[design/author-agent-harness.md](../design/author-agent-harness.md)、[design/author-interaction.md](../design/author-interaction.md)）。

---

## 1. Spec 与 SDD 的分工

| 类型 | 回答的问题 | 本仓库典型位置 |
|------|------------|----------------|
| **Spec（规约）** | **必须/禁止做什么**；产品与测试如何验收；边界与不承诺项 | 根目录 **DESIGN.md**（L0）、**TECH_IMPLEMENTATION.md**（L1）、**本文**（作者在环 L1 切片） |
| **SDD（软件设计说明）** | **怎么做**：组件、状态机、迁移步骤、与代码文件的映射 | **docs/design/** 下专题（如 author-agent-harness、author-interaction） |

**冲突处理**：实现细节以 SDD 为准；**行为是否允许**以 Spec（含本文与 TECH）为准。若 SDD 拟突破 Spec，须先修订 Spec 与 DESIGN。

### 1.1 迭代开发：文档与代码的顺序

为满足**可评审、可回归、可并行迭代**的诉求，维护者与自动化助手应遵守：

| 顺序 | 动作 | 说明 |
|------|------|------|
| 1 | **更新或引用 Spec/SDD** | 行为或验收有变：先改 **本文**、**DESIGN**、**TECH** 或 **author-agent-harness / author-interaction** 中与该变更对应的条目；见 [SPEC_SDD.md §2.1](../framework/SPEC_SDD.md)。 |
| 2 | **方案可见** | 在 PR、会话或 `WORKLOG` 中用列表说明：触及的规约段落、拟改模块、单测计划。 |
| 3 | **确认后再改代码** | 对**作者在环相关**的大块逻辑，以用户/评审确认方案后再实现；避免「先写再补文档」导致双源真相。 |
| 4 | **收尾** | 更新 [planning/next-iteration.md](../planning/next-iteration.md) 步骤勾选；规约级变更写入 `WORKLOG.md`。 |

**仓库规则**：Cursor 规则 `.cursor/rules/doc-first-spec-sdd.mdc`（`alwaysApply: true`）要求助手默认遵守上述顺序。

---

## 2. 必须满足（MUST）

1. **作者在环审阅与确认**（L0 延续）：关键写回路径上，**不得**在默认配置下跳过 DESIGN 与 TECH 已定义的**作者确认/门闩**（如设定阶段基础世界未填不得直接结束、回合同步与记忆写回的两阶段确认）。  
2. **作品目录门闩**：`setting_research.trigger=design_only` 时，进入完整设定交互前**必须**具备有效作品根目录（与 [author-interaction.md §11.1](../design/author-interaction.md) 一致）。  
3. **依赖已落盘内容时的检索义务（目标态）**：当作者自然语言**明确依赖**既有设定、正文、会话或记忆时，系统在生成答复或覆盖性重写前**应当**通过已实现的检索/工具拉取相关片段并注入上下文；**禁止**长期仅依赖单字符串 `reference` 让模型在无材料情况下断言「已确认全书状态」。*注：当前代码若未达标，以 [planning/next-iteration.md](../planning/next-iteration.md) Harness 步骤为收敛项。*  
4. **可观测（目标态）**：作者在环主路径上，对每一次作者输入，日志或调试信息中**应能**关联：`phase`、意图分类结果（或等价路由）、是否发生检索及来源摘要；具体字段以 SDD「可观测」条款为准。

---

## 3. 应当满足（SHOULD）

1. **统一入口（目标态）**：所有作者输入**宜**经同一套控制流：**分类 →（按需）检索/工具 → 阶段策略 → Handler**；阶段差异通过**策略包**体现，而非在入口复制多套 `if phase` 绕过分类/检索。  
2. **检索结果与下游 LLM 的契约**：组装进领域 Agent（设定研究、自由讨论、回合审阅等）的上下文**宜**经**单一组装点**（SDD 中称 PromptAssembler 或等价物），避免分叉维护。  
3. **主动协创（可选能力）**：若实现「助手主动联想/建议」，**应当**提供作者可配置的强度或开关，并避免无闸门的高频打断（见 SDD 风险条）。
4. **联网知识检索（目标态）**：当本地记忆与设定材料不足以支持作者请求，且场景属于「套路/背景/写法参考」等外部知识型任务时，系统**宜**通过受控联网 Tool（如 Playwright + Bing 或后续专用搜索 API）检索资料，并将来源摘要注入统一组装点；默认不把外网原文直接当作最终正文。**按需触发**：应由入口分类产出 `internet_search_needed` / `internet_query`（作者在讨论中明示搜索，或本轮明显需要外链创意/模版/范式参考），与 `runtime.author_harness.internet_search.require_classifier_signal` 配合，避免无差别每轮抓取。  
5. **规则动态加载（目标态）**：系统提示词中的规则与要求**宜**拆分为可版本化策略包（全局、作品、阶段、任务），按当前 phase/intent 动态装配，避免长期依赖单一巨型静态 prompt。  
6. **策略自我迭代（目标态）**：若引入自我迭代，规则更新**应当**以“候选变更（candidate patch）→门禁验证→生效/回滚”流程执行，且保留可观测证据（触发输入、评估分、命中来源），禁止无审计直接覆盖核心规则。

#### 3.4 正篇回合审阅（目标态，R7）

4. 在 **MAIN_WRITING** 阶段一（本回合结果审阅）中，当作者输入为**自由文本**并触发「据反馈修订正文」等需理解上下文的 Handler 时，**宜**与设定阶段一致，经 **分类 →（按需）检索 → 单一组装点 → Handler** 注入已落盘材料片段，避免仅依赖当前回合正文与一句反馈做覆盖性改写。**不得**为实现 R7 而合并或跳过 TECH 已规定的**两阶段审阅顺序**（阶段一事件簿 / 阶段二记忆写回）。设计切片、工具优先级与单 PR 边界见 [author-agent-harness.md §6.3](../design/author-agent-harness.md)。

**实现进度（说明性，不新增 MUST）**：与 §3.4 SHOULD 对齐的落地分步以 **D6 §6.3**、**next-iteration R7 子步** 为准。截至 **2026-03-29**：**R7b–R7d** 同上；**R7e** 阶段二 **`review_memory_plan`** 可观测日志（`MEMORY_PLAN_REVIEW` / `memory_plan_action`）；**R8** 阶段一 Harness 日志字段 + **`test_apply_main_writing_review_ingress_revise`** 检索源与组装块断言。

---

## 4. 禁止或不承诺（MUST NOT / 默认 OUT OF SCOPE）

1. **默认不承诺**：仅凭**单条作者诉求**、在**无在环审阅**前提下，**全自动**生成 **百万字量级**以上长篇并作为默认产品行为。若未来提供此类**执行**模式，须**单独规约**（成本、安全、一致性、与 L0 作者在环是否修订），不得默示由 Harness 常规落地自动覆盖。  
2. **禁止**：将 WORKLOG 或过程纪要中的临时表述当作与本文等价的**行为规约**（单源真相仍为 DESIGN / TECH / 本文及对应 SDD）。

---

## 5. 远期规划（当前里程碑不交付）

下列能力**不在当前迭代作为 MUST/验收项**，仅在 L0/L2 中**预留产品方向**，单独立项后再写入 MUST/SHOULD。

1. **续写潜力评估**：基于当前与作者交流的**设定、正文、会话及已落盘材料**，估计在约定质量/一致性假设下，系统**后续最多可自动续写多少字数或多少章**，并列出主要瓶颈（大纲缺口、记忆未覆盖、矛盾未解决等）。该输出为**决策参考**，**不**等同于授权系统无审阅写满该长度。设计细节见 [author-agent-harness.md §7.1](../design/author-agent-harness.md)。

---

## 6. 与 SDD 文档的映射（审查用）

| 主题 | Spec 依据（本文） | SDD 依据 |
|------|-------------------|----------|
| 迭代开发顺序（文档先行） | §1.1 | [SPEC_SDD.md §2.1](../framework/SPEC_SDD.md)；仓库 `.cursor/rules/doc-first-spec-sdd.mdc` |
| 统一入口与 Harness 分层 | §2.3、§3.1 | [author-agent-harness.md](../design/author-agent-harness.md) 全文；**编码切片** §6.1（R0–R8） |
| 状态机、M1–M6、会话与 digest | §2.1（与 DESIGN 一致） | [author-interaction.md](../design/author-interaction.md) |
| 设定阶段门闩与预览展示 | §2.2 | [author-interaction.md §11.1](../design/author-interaction.md) |
| 存储与检索路径 | §2.3（检索义务） | [memory-storage-and-retrieval.md](../design/memory-storage-and-retrieval.md) |
| 协创/思路演化/百万字边界 | §3.3、§4.1 | [author-agent-harness.md §1.1、§7](../design/author-agent-harness.md) |
| 联网检索、动态规则与策略迭代 | §3.4–§3.6 | [author-agent-harness.md §4.1、§4.3、§6.2](../design/author-agent-harness.md)；[novel-assistant-pm-agent-model.md §4.3](../design/novel-assistant-pm-agent-model.md) |
| 续写潜力评估（远期） | §5 | [author-agent-harness.md §7.1](../design/author-agent-harness.md) |
| 正篇审阅 Harness（R7） | §3.4；§2.4 可观测（落地后） | [author-agent-harness.md §6.3](../design/author-agent-harness.md) |

---

## 7. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-01 | §3 联网知识检索：补充按需触发（分类器 `internet_search_needed` / `internet_query` + 配置门闩） |
| 2026-04-13 | §3 新增目标态 SHOULD：联网知识检索、规则动态加载、策略自我迭代；§6 增补 D6/D7 映射 |
| 2026-04-11 | §3.4 **实现进度**更新：R7d 主流程已接线 |
| 2026-03-29 | §3.4 增补**实现进度**（R7b/R7c 已编码、R7d 待接主流程）；与 D6/next-iteration 同步 |
| 2026-04-09 | 新增 §3.4 正篇审阅目标态（R7）；§6 映射 **§6.3** |
| 2026-04-06（续） | 新增 §1.1 迭代开发与文档先行；互链 SPEC_SDD、next-iteration、Cursor 规则 |
| 2026-04-06 | 新增 §5 远期规划：续写潜力评估；§4 与「执行层全自动」表述对齐 |
| 2026-04-05 | 初版：拆分作者在环 L1 Spec；与 Harness SDD、TECH、DESIGN 分工说明 |
