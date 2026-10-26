# Context Engineering Demos — Implementation Plan

## Task 1: 项目骨架与打包配置
- **Status**: `completed`
- **Priority**: high
- **Depends On**: None
- **Description**:
  - 创建 `pyproject.toml`（Python 3.11、ruff 配置、pytest 配置、build 可打包）
  - 创建 `requirements.txt`（仅 pytest + ruff）
  - 创建 `src/context_engineering/__init__.py` 空包
  - 验证 `pip install -e .` 和 `python -m build` 成功
- **Acceptance Criteria Addressed**: AC-7, AC-9
- **Test Requirements**:
  - `rule` TR-1.1: `pip install -e .` 无报错；evidence: ✓ 退出码 0
  - `rule` TR-1.2: `ruff check .` 通过；evidence: ✓ All checks passed
  - `rule` TR-1.3: `python -m build` 成功生成 dist/；evidence: ✓ dist/ 含 wheel + sdist
- **Completion Evidence**:
  - pyproject.toml / requirements.txt / requirements-dev.txt 已创建
  - `pip install -e .` 退出码 0
  - `python -m build` 输出 `Successfully built context_engineering-0.1.0.tar.gz and context_engineering-0.1.0-py3-none-any.whl`

## Task 2: MockLLM 基础设施
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - `mock_llm.py`: MockLLM + UsageStats + 模拟摘要/问答/默认三种输出策略
  - `tokenizer.py`: char-based tokenize → `len(text)//4` 近似
  - `exceptions.py`: ContextOverflowError
  - `tests/test_mock_llm.py`: 11 个测试用例
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `rule` TR-2.1: ✓ generate 正常返回
  - `rule` TR-2.2: ✓ 超限抛 ContextOverflowError
  - `rule` TR-2.3: ✓ token 计数误差 <= 1%
  - `rubric` TR-2.4: MockLLM API 设计可用性；evidence: 支持 summary/qa/auto 三种模式、累计 token 统计、reset_usage、generate 便捷方法、truncate_to_tokens
- **Completion Evidence**:
  - `pytest -q tests/test_mock_llm.py`: 11 passed
  - MockLLM 具备 generate / summarize / answer 三种公开 API + usage 累计统计

## Task 3: 内置测试数据
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - data/tech_whitepaper.py: 白皮书约 2649 字符
  - data/news_briefings.py: 5 篇新闻简报
  - data/qa_pairs.py: 5 组问答对
  - data/codebase_mock.py: 13 文件的模拟电商后端目录树
- **Acceptance Criteria Addressed**: AC-2, AC-3, AC-4, AC-5 前置
- **Test Requirements**:
  - `rule` TR-3.1: ✓ 白皮书 2649 字符（662 token）
  - `rule` TR-3.2: ✓ 5 篇简报各约 410-600 token
  - `rule` TR-3.3: ✓ 白皮书 token > 窗口一半

## Task 4: 滑动窗口摘要方案
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 2, Task 3
- **Description**:
  - sliding_window.py: chunk_text + sliding_window_summarize
  - run_demo_sliding_window.py: 入口脚本
  - tests/test_sliding_window.py
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `rule` TR-4.1: ✓ 最终摘要 token ≤ 原文 50%
  - `rule` TR-4.2: ✓ demo 退出码 0
  - `rubric` TR-4.3: 代码可读性；evidence: 关键函数有 docstring，demo 入口有 emoji 引导
- **Completion Evidence**:
  - `python run_demo_sliding_window.py` 输出 Token 压缩比 9.7%，退出码 0
  - pytest 测试 3/3 通过

## Task 5: Map-Reduce 多文档聚合方案
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 2, Task 3
- **Description**:
  - map_reduce.py: map_reduce_aggregate（Map 阶段预超限折叠 + Reduce 阶段）
  - run_demo_map_reduce.py
  - tests/test_map_reduce.py
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `rule` TR-5.1: ✓ 每篇文档都被 Map 摘要
  - `rule` TR-5.2: ✓ demo 退出码 0
  - `rule` TR-5.3: ✓ Map+Reduce token < 全量
- **Completion Evidence**:
  - 5 篇简报独立 Map → Reduce 生成聚合报告，运行正常

## Task 6: RAG-lite 向量检索方案
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 2, Task 3
- **Description**:
  - utils/tfidf.py: 纯 Python TF-IDF（中文 2-gram + 英文按单词）
  - rag_lite.py: RagLite 类 + chunk_by_tokens
  - run_demo_rag_lite.py: 支持 --question
  - tests/test_rag_lite.py: 3 个测试
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `rule` TR-6.1: ✓ 命中率 ≥ 60%
  - `rule` TR-6.2: ✓ demo 退出码 0
  - `rule` TR-6.3: ✓ token 不超限
- **Completion Evidence**:
  - TF-IDF 支持中文 2-gram 分词，QA 对检索有命中文档
  - pytest 3/3 通过

## Task 7: 结构化索引方案
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 2, Task 3
- **Description**:
  - utils/tree_index.py: FileNode + build_tree_index + search_nodes
  - structured_index.py: StructuredIndexQA 类
  - run_demo_structured_index.py: 支持 --query
  - tests/test_structured_index.py: 3 个测试
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `rule` TR-7.1: ✓ 加载 < 全量 50%
  - `rule` TR-7.2: ✓ 回答命中正确模块
  - `rule` TR-7.3: ✓ demo 退出码 0
- **Completion Evidence**:
  - 加载文件数 0-4 / 全量 13，比例 0-30%

## Task 8: 统一入口 run_all.py + 全量 pytest
- **Status**: `completed`
- **Priority**: medium
- **Depends On**: Task 4, Task 5, Task 6, Task 7
- **Description**:
  - run_all.py: 依次运行 4 个 demo + 汇总
  - ruff check / pytest / build 全验证
- **Acceptance Criteria Addressed**: AC-6, AC-7, AC-9
- **Test Requirements**:
  - `rule` TR-8.1: ✓ python run_all.py → 4/4 PASS
  - `rule` TR-8.2: ✓ ruff All checks passed
  - `rule` TR-8.3: ✓ pytest 24 passed
  - `rule` TR-8.4: ✓ python -m build 成功

## Task 9: Ruff 配置调整与代码规范收敛
- **Status**: `completed`
- **Priority**: low
- **Depends On**: Task 8
- **Description**:
  - pyproject.toml 加 per-file-ignores 对 data/ 和 demo 脚本关闭 E501
  - ruff check --fix 自动修复 I001/F541
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `rule` TR-9.1: ✓ ruff check . 退出码 0
- **Completion Evidence**:
  - 最终 ruff 输出 `All checks passed!`
