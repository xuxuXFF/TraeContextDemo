# Context Engineering Demos — Independent Review

## Checkpoints

- [x] CP-R1: ruff check 全部通过
  - **Type**: `rule`
  - **Covers**: AC-7, AC-9
  - **Evidence**: `ruff check .` → All checks passed, exit code 0

- [x] CP-R2: pytest 全部通过（24 个测试）
  - **Type**: `rule`
  - **Covers**: AC-1, AC-2, AC-3, AC-4, AC-5, AC-7
  - **Evidence**: `pytest -q` → 24 passed in 0.09s, 5 个 test 文件全部 pass

- [x] CP-R3: `python run_all.py` 4/4 demo 通过
  - **Type**: `rule`
  - **Covers**: AC-2, AC-3, AC-4, AC-5, AC-6
  - **Evidence**: 退出码 0, 汇总输出 ✅ PASS × 4

- [x] CP-R4: 每个 demo 输出包含 token 统计信息
  - **Type**: `rule`
  - **Covers**: NFR-4
  - **Evidence**: 滑动窗口输出压缩比、Map-Reduce 输出 Map/Reduce 阶段 token、RAG-lite 输出 hit_token_count 和 context_ratio、结构化索引输出 loaded_ratio

- [x] CP-R5: `pip install -e .` + `python -m build` 成功
  - **Type**: `rule`
  - **Covers**: AC-7, AC-9
  - **Evidence**: dist/ 含 context_engineering-0.1.0.tar.gz 和 .whl

- [x] CP-U1: 代码整体可理解性与 demo 引导清晰度
  - **Type**: `rubric`
  - **Covers**: AC-8
  - **Scale**: 1-5
  - **Anchors**: 1 = 杂乱无注释；3 = 能跑但注释稀疏；5 = 结构清晰 + docstring + demo 引导
  - **Pass Threshold**: >= 4
  - **Score**: 4.5
  - **Rationale**: 所有模块顶层 docstring 讲清"是什么/为什么"，函数级 docstring 完整；MockLLM 和 tfidf.py 设计达到 5/5；sliding_window/map_reduce/rag_lite/structured_index 四个方案模块各得 4/5；API 形状不统一（前俩 2-tuple、后俩 3-tuple）为主要扣分点
  - **Evidence**: 独立 Reviewer 逐项审阅 7 个核心源码 + 4 个数据文件 + demo 入口 + 构建配置

## Advisory Findings（非阻塞）

- A1: `codebase_mock.py` 里 `SECRET_KEY = 'dev-secret-change-me'` 硬编码 —— 虽然是 mock 数据，但硬编码 secret 属于安全红线，应改为 `os.environ.get('SECRET_KEY', '')` 或直接删除
- A2: `chunk_text`（sliding_window.py）与 `chunk_by_tokens`（rag_lite.py）实现几乎完全重复 —— 可抽到 utils/ 统一
- A3: `structured_index.py` 的 `query` 方法缺少 docstring
- A4: `codebase_mock.py` mock 数据量（1119 token）偏小，结构化索引 demo 里检索覆盖率 97.7%，压缩效果不够显著（但 demo 功能正确，非 bug）

## Review History

### Review R1
- **Result**: `pass`
- **Checks Performed**:
  - `ruff check .` → All checks passed
  - `pytest -q` → 24 passed
  - `python run_all.py` → 4/4 PASS
  - 7 个核心源码 + 4 个数据文件 + pyproject.toml + 4 个 demo 入口 + run_all.py 逐文件 Read 审阅
  - 评分 API 设计、注释水平、可读性三个维度
- **Checkpoint Results**:
  - CP-R1 (`rule`): pass
  - CP-R2 (`rule`): pass
  - CP-R3 (`rule`): pass
  - CP-R4 (`rule`): pass
  - CP-R5 (`rule`): pass
  - CP-U1 (`rubric`): pass; score 4.5; rationale 见上方
- **Findings**:
  - A1-A4: advisory（非 actionable），不阻塞验收
- **Remediation Notes**:
  - 已修 A1：`codebase_mock.py` 的 `SECRET_KEY` 改为 `os.environ.get('SECRET_KEY', '')` 占位符，避免硬编码模式
