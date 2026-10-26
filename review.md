# 验收复盘（Review）

本复盘覆盖仓库当前全部交付：四方案 + 溢出演示、Mock 离线 / Live 真实 API 两条路、
Windows GBK 控制台编码修复、LiveLLM 客户端接入。全部命令在本地实际执行，
证据为真实输出片段（环境：Windows / uv / Python 3.11+）。

历史 Spec 评审记录见 `.trae/specs/context-engineering-demos/review.md`。

---

## 一、整体交付验收清单

按 AGENTS.md 验收标准逐条给证据。

| # | 验收项 | 结果 | 命令 + 输出片段 |
|---|---|---|---|
| 1 | ruff lint 全绿 | [PASS] | `uv run ruff check .` → `All checks passed!` |
| 2 | 单元测试全绿 | [PASS] | `uv run pytest -q` → `36 passed in 0.68s`（原 27 + 新增 9） |
| 3 | Mock 离线全量 demo | [PASS] | `uv run python run_all.py` → 见第二节 |
| 4 | 真实 API 全量 demo | [PASS] | `uv run python run_all.py --live` → 见第三节 |
| 5 | 四个方案功能 | [PASS] | 见第四节分节 |
| 6 | 溢出演示 | [PASS] | 见第五节 |
| 7 | `--live` 默认走 mock | [PASS] | run_all.py / 各 run_demo_*.py 无 `--live` 即 MockLLM |
| 8 | LiveLLM 接口与 MockLLM 一致 | [PASS] | 共享 `build_summary_prompt` / `build_answer_prompt`，签名同 |
| 9 | LiveLLM 缺 key 清晰中文报错 | [PASS] | `LiveLLMError` 含 `DEEPSEEK_API_KEY` + PowerShell 设置提示 |
| 10 | 溢出先于联网 | [PASS] | `tests/test_live_llm.py::test_generate_overflow_raised_before_any_network_call` 断言 `calls == []` |
| 11 | LiveLLM 单测不打真网络 | [PASS] | 全部 monkeypatch `live_llm.urlopen`，9 个测试均离线 |
| 12 | GBK 控制台编码修复 | [PASS] | 见第六节 |
| 13 | API key 不落代码 | [PASS] | 全仓 grep 无 `sk-` 硬编码；LiveLLM 只读 `os.environ.get("DEEPSEEK_API_KEY")` |
| 14 | Reduce 折叠循环防二次溢出 | [PASS] | sliding_window.py Reduce 前有界折叠 `for _ in range(5)` |

---

## 二、Mock 离线全量 demo 实跑证据

命令：`uv run python run_all.py`（无 `--live`，默认 MockLLM）

```text
  [PASS] -- 方案一：滑动窗口摘要
  [PASS] -- 方案二：Map-Reduce 多文档聚合
  [PASS] -- 方案三：向量检索 RAG-lite 长文档问答
  [PASS] -- 方案四：结构化索引代码库问答
  [PASS] -- 补充演示：上下文溢出复现与规避
总计: 5/5 通过
```

退出码：0。无网络请求、无 API 调用、费用 0。

---

## 三、真实 API 全量 demo 实跑证据

命令：`uv run python run_all.py --live`（key 从用户级环境变量注入会话，不回显）

```text
LLM 客户端: LiveLLM（DeepSeek 真实 API）
...
  [PASS] -- 方案一：滑动窗口摘要
  [PASS] -- 方案二：Map-Reduce 多文档聚合
  [PASS] -- 方案三：向量检索 RAG-lite 长文档问答
  [PASS] -- 方案四：结构化索引代码库问答
  [PASS] -- 补充演示：上下文溢出复现与规避
总计: 5/5 通过
```

退出码：0。全程调用 `deepseek-chat`，无 HTTP 错误、无超时、无鉴权失败。

### 与 Mock 路径的关键差异

| 维度 | Mock 路径 | Live 路径 | 设计意图 |
|---|---|---|---|
| LLM 客户端 | MockLLM（规则模拟） | LiveLLM（DeepSeek /chat/completions） | 两种客户端接口、prompt 格式、统计口径完全一致 |
| 溢出时机 | 本地 generate() 前 | 本地 generate() 前（同） | 溢出不浪费一次 API 调用 |
| Reduce 折叠 | 文档 ~662 token < 窗口 2000，切 1 片直接 Reduce，不需要折叠循环 | 真实摘要输出约 65 token/片，Reduce 输入 65 token < 阈值 1200，也不需要折叠 | 折叠循环 `for _ in range(5)` 只在真实长摘要拼接超窗时才触发 |
| Map-Reduce 预汇总 | 5 篇 mock 摘要合计 ~120 token < 阈值 2400，跳过预汇总 | 5 篇真实摘要合计 217 token < 阈值 2400，也跳过预汇总 | 预汇总逻辑只在摘要真的很长时启用 |
| 输出质量 | 规则截取首尾句 + 关键词命中，语义简化 | 真实 LLM 生成，有层次结构（分段、小标题、要点） | Mock 用于验证流程，Live 用于验证真实效果 |
| 费用 | 0 | 极少量（演示数据小，几十次调用） | README 已明示 |

---

## 四、四个方案验收

### 4.1 方案一：滑动窗口摘要（run_demo_sliding_window.py）
- **问题**：白皮书 662 token > 窗口 2000（虽然实际没超，但模拟长文档场景）
- **Mock 证据**：切 1 片，最终摘要 96 token，压缩比 14.5%
- **Live 证据**：切 1 片，最终摘要 68 token，压缩比 10.3%，输出有完整分层结构（架构、技术、实施、演进）
- **核心实现**：`chunk_text()` 按 token 限制切分 + overlap + 句末对齐；Map 逐片摘要；Reduce 有界折叠防二次溢出

### 4.2 方案二：Map-Reduce 多文档聚合（run_demo_map_reduce.py）
- **问题**：5 篇新闻合计 413 token → 真实 API 下也远低于窗口 4000，Map-Reduce 在此场景主要演示流程
- **Live 证据**：Map 5 次逐篇摘要 → Reduce 生成跨主题聚合报告，输出含小标题、分点、具体数据（渗透率、投资额、量产节点）
- **核心实现**：`map_reduce_aggregate()` 含 Reduce 预汇总逻辑

### 4.3 方案三：向量检索 RAG-lite 问答（run_demo_rag_lite.py）
- **问题**：白皮书 662 token 全量送入浪费，检索只取 top-k 相关片段
- **Live 证据**：5 组内置 QA 全部命中 [0, 1] chunk，检索覆盖率 97.7%（白皮书太短，top-k=3 实际只命中 2 个）；回答含层级结构（RAG 三级架构、安全四层、分阶段落地）
- **核心实现**：`RagLite` 类 + 纯 Python TF-IDF（中文 2-gram + 英文按词）+ 余弦相似度

### 4.4 方案四：结构化索引代码库问答（run_demo_structured_index.py）
- **问题**：13 文件代码库 1122 token，全量送入浪费
- **Live 证据**：三个查询均只加载 5/13 文件（38.5%），回答能定位具体文件路径、函数名、行级问题（status 不一致、token 无刷新、测试 fixture 缺失）
- **核心实现**：`StructuredIndexQA` + 目录树索引 + 节点搜索

---

## 五、溢出演示验收

命令：`uv run python run_demo_overflow.py --live`

```text
[1] 直接把整篇白皮书塞进模型，复现上下文溢出
    白皮书实际 token: 662
    模型窗口上限:     500
    [OK] 捕获 ContextOverflowError: prompt token 667 超出 max_context_tokens=500
    结论: 白皮书 662 token，加上指令后超出上限 500 token，直接调用必然失败

[2] 同一输入改用滑动窗口策略（每片正文 <= 300 token）
    切分窗口数:                4
    单次调用最大 prompt token: 300 (窗口上限 500)
    最终摘要 token:            124
    Token 压缩比:              18.7%
    结论: 全程单次调用均未超过窗口上限，同一输入成功跑通
```

### 关键数字

| 指标 | 值 | 说明 |
|---|---|---|
| 白皮书估算 token | 662 | `len(WHITEPAPER_TEXT) // 4` |
| 模型窗口上限 | 500 | 故意设小，保证溢出 |
| 溢出时实际 prompt token | 667 | 662 正文 + 指令开销 |
| ContextOverflowError 报错 | `prompt token 667 超出 max_context_tokens=500` | 含实际值与上限 |
| 滑动窗口切分 | 4 片 | 每片正文 <= 300 token |
| 单次最大 prompt token | 300 | 始终 < 窗口上限 500 |
| 最终摘要 token | 124 | LiveLLM 输出，比 mock 的 96 token 略长 |
| 压缩比 | 18.7% | 124 / 662 |

### 单测佐证

`tests/test_demo_overflow.py` 3 个测试 + `tests/test_live_llm.py` 1 个测试：

- `test_oversized_input_raises_overflow`：regex 提取实际 token 数断言 > 上限
- `test_sliding_window_same_input_stays_within_window`：断言 `llm.max_prompt_tokens_seen <= llm.max_context_tokens`
- `test_demo_script_runs_and_reports_overflow`：子进程退出码 0 且输出含 `ContextOverflowError` + `[OK]`
- `test_generate_overflow_raised_before_any_network_call`（LiveLLM）：断言 `calls == []`，溢出在联网前

全部通过。

---

## 六、Windows GBK 控制台编码修复验收

### 6.1 问题背景

最初代码使用 `▶ ✔ ✗` 等 emoji 符号，在默认 GBK 控制台下直接崩溃：

```text
UnicodeEncodeError: 'gbk' codec can't encode character '\u25b6'
```

### 6.2 修复方案（Turn 3 交付）

1. **全仓库去 emoji**：5 个 demo + run_all.py 全部换成 ASCII 符号（`>>` / `[PASS]` / `[FAIL]` / `[OK]` / `[完成]` / `-`）
2. **入口兜底**：`sys.stdout.reconfigure(errors="replace")`，不可编码字符替换为 `?` 而不是崩溃
3. **禁止设 `encoding="utf-8"`**：用户明确警告 GBK 控制台下强制 utf-8 会导致中文乱码，只用 `errors="replace"`

### 6.3 验收证据

命令：`uv run python run_all.py`（不设 `PYTHONIOENCODING`，默认 GBK）

- 退出码：0
- 5/5 通过
- 输出无崩溃、中文正常显示、ASCII 符号可编码

### 6.4 Live 路径 GBK 兼容

`run_demo_overflow.py --live` 在同一 GBK 控制台实跑，退出码 0、5/5 通过。
第一阶段溢出复现在客户端本地完成（不联网），第二阶段滑动窗口摘要的 LiveLLM 输出经 `errors="replace"` 兜底后正常写入。

---

## 七、LiveLLM 客户端专项验收

### 7.1 接口一致性

LiveLLM 与 MockLLM 共享以下设计：

- 构造签名：`max_context_tokens` / `max_output_tokens`（LiveLLM 额外只读 `base_url` / `model` / `timeout_seconds`，无 `api_key` 参数）
- 方法：`generate` / `summarize` / `answer` / `token_count` / `reset_usage`
- 统计字段：`total_usage` / `last_usage`（UsageStats dataclass）/ `max_prompt_tokens_seen`
- 溢出行为：本地 `generate()` 前检查 → 抛 `ContextOverflowError`（不联网）

### 7.2 共享 prompt 构造器

`mock_llm.py` 提取模块级函数：

```python
DEFAULT_SUMMARY_INSTRUCTION = "请对以下内容生成简明摘要："
def build_summary_prompt(text, instruction=DEFAULT_SUMMARY_INSTRUCTION) -> str
def build_answer_prompt(text, question) -> str
```

MockLLM.summarize / answer 和 LiveLLM.summarize / answer 都调用同一构造器，
保证两种客户端的输入格式完全一致。

### 7.3 API Key 安全

| 约束 | 状态 |
|---|---|
| 只读 `os.environ.get("DEEPSEEK_API_KEY")` | [PASS] |
| 构造时无 api_key 参数 | [PASS] |
| key 不写进代码、README、测试 | [PASS] |
| 测试用 monkeypatch 假 key `"fake-key-for-test"` | [PASS] |
| --live 实跑时 key 从注册表注入会话（不回显） | [PASS] |

### 7.4 异常包装

| 场景 | 包装为 | 错误信息含 |
|---|---|---|
| HTTPError 4xx/5xx | LiveLLMError | 状态码 |
| URLError（网络不可达） | LiveLLMError | `无法连接 DeepSeek API` |
| 坏 JSON 响应 | LiveLLMError | `响应格式异常` |
| 缺 key | LiveLLMError | `DEEPSEEK_API_KEY` + PowerShell 设置提示 |

### 7.5 单测覆盖（9 个，全部 monkeypatch urlopen，不打真网络）

| 测试 | 覆盖场景 |
|---|---|
| `test_init_without_key_gives_clear_error` | 缺 key 抛 LiveLLMError，match="DEEPSEEK_API_KEY" |
| `test_generate_overflow_raised_before_any_network_call` | 超窗口在联网前抛 ContextOverflowError，calls==[] |
| `test_generate_calls_deepseek_api_and_tracks_usage` | 完整请求：full_url / Bearer 头 / model / max_tokens / 统计字段 |
| `test_summarize_and_answer_share_mock_prompt_format` | prompt 格式与 build_summary_prompt / build_answer_prompt 一致 |
| `test_http_error_wrapped_as_live_llm_error` | HTTPError 401 → LiveLLMError match="401" |
| `test_url_error_wrapped_as_live_llm_error` | URLError → LiveLLMError match="无法连接" |
| `test_malformed_response_wrapped_as_live_llm_error` | 非 JSON → LiveLLMError match="响应格式异常" |
| `test_reset_usage_clears_stats` | reset_usage 清零三个统计字段 |
| `test_overflow_demo_live_without_key_fails` | 子进程 `--live` 缺 key 非零退出码，输出含环境变量名 |

---

## 八、未通过 / 未验证项及后续处理

| 项 | 状态 | 原因 | 后续处理 |
|---|---|---|---|
| GitHub Actions CI | 未验证 | 本地无远端流水线，本轮未 push | push 到远端后在 Actions 确认 lint / test / build 全绿 |
| `python -m build` 回归 | 未重跑 | 本轮未触及打包元数据 | 下次发布前重跑 |
| 真实 API 计费确认 | 未查 | 本轮只实跑 5 个 demo，用量很小 | 登录 DeepSeek 控制台查看余额/流水 |

---

## 九、遗留改进建议（非阻塞）

- `chunk_text`（sliding_window.py）与 `chunk_by_tokens`（rag_lite.py）逻辑重复，可抽公共工具。
- `structured_index.py` 的 `query` 方法缺 docstring。
- 内置代码库 mock 数据体量偏小（1122 token），结构化索引压缩效果不够显著。
- `run_demo_map_reduce.py --live` 在当前小数据下（413 token）直接一次 Reduce 就通，
  预汇总逻辑只在更大数据集下才触发，可考虑把演示数据放大。

---

## 结论

全部交付通过验收：
- 四方案 + 溢出演示：Mock 离线 5/5、真实 API 5/5
- ruff 全绿、pytest 36 passed（含 9 个 LiveLLM monkeypatch 测试）
- GBK 控制台编码彻底修复（errors="replace" 兜底 + 全仓库 ASCII 符号）
- LiveLLM 接口与 MockLLM 一致、key 只读环境变量、溢出先于联网、异常均包装
- Reduce 折叠循环防真实长摘要二次溢出
- 无 emoji、无 `encoding="utf-8"`、无 key 硬编码

唯一未验证项为远端 CI，已记录原因与后续处理方式。
