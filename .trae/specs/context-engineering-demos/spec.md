# Context Engineering Demos — Product Requirements Document

## Overview
- **Summary**: 一个纯 Python 的上下文工程案例演示仓库，聚焦 **Token 限制与长文本处理**这一核心问题，提供 4 种典型解决方案的可运行代码与演示。
- **Purpose**: 让读者通过可运行的代码直观理解在 LLM 上下文窗口有限的前提下，如何处理超长文本、多文档聚合、长文档问答、代码库分析等常见场景。
- **Target Users**: AI 应用工程师、Agent 开发者、对上下文工程感兴趣的技术人员。

## Goals
- 提供覆盖 4 类经典问题场景的、**纯本地可运行**（无需外部 LLM API）的解决方案
- 每个方案都包含：问题背景 → 方案原理 → 代码实现 → 可执行演示 → 输出验证
- 用 Mock LLM 模拟真实模型的 token 限制、调用行为和截断机制，让读者能快速跑通
- 所有代码通过 `ruff check` lint 和 `pytest` 单测，与仓库既有 CI 流程对齐

## Non-Goals
- 不调用真实 LLM API（OpenAI / 国产模型等）
- 不做生产级别的向量数据库、RAG 框架集成
- 不覆盖其他上下文工程领域（如 Prompt 工程、Agent 多轮记忆等）
- 不提供 GUI / Web 界面

## Background & Context
- LLM 有固定的上下文窗口限制（如 8K / 32K / 128K tokens），但真实应用中的文档、代码库、数据集远超这个上限
- 业界已形成多种成熟的应对模式：滑动窗口、Map-Reduce 分层、向量检索、关键段落提取、结构化索引等
- 本仓库旨在用最小化的代码骨架复刻这些模式，方便读者理解和改造

## Functional Requirements
- **FR-1**: 提供 MockLLM 基础设施，支持 token 计数、上下文窗口限制模拟、调用时自动截断、返回模拟结果
- **FR-2**: 提供内置测试数据：模拟技术白皮书（单超长文档）、新闻简报集（多短文档）、长问答对（需要从长文找答案）、模拟代码库目录树
- **FR-3**: 实现 **滑动窗口摘要方案** —— 将长文档切片逐段送入模型生成局部摘要，再合并为最终摘要
- **FR-4**: 实现 **Map-Reduce 多文档聚合方案** —— 多文档各自 Map 摘要后，再 Reduce 生成统一聚合报告
- **FR-5**: 实现 **向量检索（RAG-lite）方案** —— 用简化版 TF-IDF + 余弦相似度实现 chunk 召回，将最相关片段送入模型回答问题
- **FR-6**: 实现 **结构化索引方案** —— 为模拟代码库构建目录层级索引，按相关路径加载子树内容进行问答
- **FR-7**: 每个方案都有独立的 `run_demo_*.py` 脚本，运行后打印问题描述、执行过程、最终结果和 token 统计
- **FR-8**: 每个方案都有 pytest 测试用例，验证输出结果符合预期（token 使用量、结果包含关键信息等）
- **FR-9**: 提供统一入口 `python run_all.py` 依次运行所有 demo

## Non-Functional Requirements
- **NFR-1**: 纯标准库 + `pytest` + `ruff`，无第三方外部依赖（不引入 numpy、scikit-learn 等，向量计算用纯 Python 实现）
- **NFR-2**: 任意 demo 运行时间 < 5 秒（本地 CPU）
- **NFR-3**: 代码风格通过 `ruff check`，测试通过 `pytest -q` 100% 绿
- **NFR-4**: 每个 demo 的输出包含 token 统计信息，让读者直观看到方案如何节省 token

## Constraints
- **Technical**: Python 3.11、纯本地执行、Mock LLM 不联网
- **CI**: 必须适配仓库既有 `.github/workflows/ci.yml`（ruff + pytest + build）
- **Dependencies**: 运行期零第三方依赖；开发期仅 `pytest` + `ruff`

## Assumptions
- 读者具备基础 Python 知识和 LLM 上下文窗口概念
- MockLLM 的 token 计数用简单的 `len(text) // 4` 近似（英文 1 token ≈ 4 字符，中文 1 token ≈ 1.5 字符，本项目统一用字符数估算）
- MockLLM 对摘要/问答的返回用内置规则生成（如：截取文本首尾、提取关键词附近段落），不追求语义质量，只验证流程正确性

## Acceptance Criteria

### AC-1: MockLLM 基础设施可用
- **Type**: `rule`
- **Given**: 项目已安装
- **When**: 调用 `MockLLM(max_context_tokens=N).generate(prompt)` 且 prompt 长度 ≤ N
- **Then**: 正常返回模拟结果；若 prompt 超 N，抛出 `ContextOverflowError` 或按策略截断
- **Pass Condition**: MockLLM 正确计数 token、正确模拟窗口限制
- **Evidence**: pytest 测试 `test_mock_llm.py` 通过

### AC-2: 滑动窗口摘要 demo 可运行
- **Type**: `rule`
- **Given**: 项目已安装
- **When**: 执行 `python run_demo_sliding_window.py`
- **Then**: 输出完整演示流程，最终摘要 token 量远小于原始文档，且包含文档核心段落信息
- **Pass Condition**: demo 运行成功，token 使用量输出 < 原始文档 token 的 50%
- **Evidence**: 脚本成功退出码 0，stdout 含 `token` 关键字和摘要内容

### AC-3: Map-Reduce 多文档聚合 demo 可运行
- **Type**: `rule`
- **Given**: 项目已安装
- **When**: 执行 `python run_demo_map_reduce.py`
- **Then**: 先对各文档分别做 Map 摘要，再 Reduce 生成统一报告
- **Pass Condition**: demo 运行成功，输出包含各阶段 token 统计和最终聚合报告
- **Evidence**: 脚本退出码 0，输出明确显示 Map 阶段和 Reduce 阶段

### AC-4: 向量检索 RAG-lite demo 可运行
- **Type**: `rule`
- **Given**: 项目已安装
- **When**: 执行 `python run_demo_rag_lite.py --question "..."`
- **Then**: 基于 TF-IDF 相似度检索最相关 chunks，送入 MockLLM 回答
- **Pass Condition**: 检索到的 chunks 确实包含答案关键词；最终回答正确
- **Evidence**: pytest 验证问答命中率 ≥ 80%

### AC-5: 结构化索引 demo 可运行
- **Type**: `rule`
- **Given**: 项目已安装
- **When**: 执行 `python run_demo_structured_index.py --query "..."`
- **Then**: 基于目录树索引定位相关子树，加载子树文件内容进行问答
- **Pass Condition**: 只加载了相关路径下的文件（而非全量代码库），回答正确
- **Evidence**: token 统计显示加载量远小于全量，pytest 验证查询命中率

### AC-6: 统一入口可运行
- **Type**: `rule`
- **Given**: 项目已安装
- **When**: 执行 `python run_all.py`
- **Then**: 依次运行所有 4 个 demo，全部成功退出
- **Pass Condition**: 4 个 demo 全部 exit code 0
- **Evidence**: 脚本依次输出各 demo 结果

### AC-7: 代码质量通过 CI
- **Type**: `rule`
- **Given**: 项目已 push 到 GitHub
- **When**: CI pipeline 执行
- **Then**: ruff check 通过、pytest 全部通过、python -m build 成功
- **Pass Condition**: CI 全绿
- **Evidence**: GitHub Actions 运行记录

### AC-8: 示例的可理解性
- **Type**: `rubric`
- **Dimension**: 每个 demo 的代码可读性与概念清晰度
- **Scale**: 1-5
- **Anchors**: 1 = 代码混杂难读；3 = 可运行但注释稀少；5 = 每个 demo 结构清晰、关键逻辑有注释、main 函数有打印引导
- **Pass Threshold**: >= 4
- **Evidence**: 代码 review + 独立 reviewer 判断

### AC-9: 纯本地零依赖验证
- **Type**: `rule`
- **Given**: 一个干净的 Python 3.11 环境，仅安装 pytest 和 ruff
- **When**: 安装项目并运行所有 demo
- **Then**: 无网络请求、无第三方运行时依赖报错
- **Pass Condition**: 全量跑通，requirements.txt 只有 pytest + ruff
- **Evidence**: requirements.txt 内容 + 离线环境运行验证

## Open Questions
- [x] 运行时零第三方依赖是否可以？—— 是，用纯 Python 实现 TF-IDF 等
- [x] 是否需要打包成可安装包（pyproject.toml）？—— 需要，适配 CI 的 `python -m build` 步骤
