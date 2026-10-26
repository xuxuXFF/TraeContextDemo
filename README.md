# Context Engineering Demos — 上下文工程案例演示

围绕 **Token 限制与长文本处理** 的可运行案例集。默认基于本地 MockLLM，
离线可跑、无需任何 LLM API Key；也支持 `--live` 开关切到真实 DeepSeek API（见下文「接真实 API」）。

## 环境准备

要求 Python 3.11+，推荐使用 [uv](https://docs.astral.sh/uv/)：

```bash
uv sync            # 创建虚拟环境、安装项目本体与 dev 依赖（pytest / ruff），并生成 uv.lock
uv run pytest -q   # 运行单元测试
```

不使用 uv 时也可以用 pip：

```bash
pip install -e .
pip install -r requirements-dev.txt
```

## 案例总览：各自解决什么上下文问题

| Demo | 场景 | 解决的问题 |
|---|---|---|
| `run_demo_sliding_window.py` | 单篇超长文档摘要 | 文档 token 超过上下文窗口，无法一次送入 → 切成窗口逐段摘要，再汇总为最终摘要 |
| `run_demo_map_reduce.py` | 多文档聚合报告 | 多份文档合计超过窗口 → 先对每份独立摘要（Map），再生成统一聚合报告（Reduce） |
| `run_demo_rag_lite.py` | 超长文档定向问答 | 只需要与问题相关的片段 → TF-IDF + 余弦相似度检索 top-k 片段，再送入模型回答 |
| `run_demo_structured_index.py` | 大代码库问答 | 全量代码远超窗口 → 按目录树建索引定位相关子树，只加载命中的少数文件 |
| `run_demo_overflow.py` | 上下文溢出本身 | 直观复现超窗口输入触发 `ContextOverflowError`（打印实际 token 数 vs 上限），并演示换滑动窗口策略后同一输入跑通且全程不超上限 |

所有 demo 都会打印 token 统计（原始 token、各阶段 token、压缩比），展示每种策略如何节省上下文。

## 运行方式

```bash
uv run python run_all.py                  # 依次运行全部 demo（推荐入口）
uv run python run_demo_sliding_window.py  # 运行单个 demo
uv run python run_demo_rag_lite.py --question "下一代企业智能客服系统采用了什么总体架构？"
uv run python run_demo_structured_index.py --query "auth token"
```

## 接真实 API（--live）

所有 demo 与 `run_all.py` 都支持 `--live` 开关：传入后由 MockLLM 切换为
`LiveLLM`（`src/context_engineering/live_llm.py`），调用真实的 DeepSeek `deepseek-chat`。
两种客户端的调用签名、prompt 格式、token 统计口径完全一致，
超窗口时同样在本地抛 `ContextOverflowError`（不发起网络请求）。

### 1. 设置 API Key

key 只从环境变量 `DEEPSEEK_API_KEY` 读取，代码、测试与本文档均不包含 key，也不要把 key 提交进仓库。

PowerShell（仅当前会话生效）:

```powershell
$env:DEEPSEEK_API_KEY = "你的key"
```

PowerShell（永久写入用户环境变量，setx 后需重开终端生效）:

```powershell
setx DEEPSEEK_API_KEY "你的key"
```

未设置该变量时运行 `--live` 会得到明确的中文报错（`LiveLLMError`），不带 `--live` 不受影响。

### 2. 运行

```bash
uv run python run_demo_overflow.py --live   # 单个 demo 走真实 API
uv run python run_all.py --live             # 全部 demo 走真实 API
```

### 3. 费用与限流注意

- `--live` 会真实计费：一次滑动窗口摘要约发起 3~10 次 API 调用，
  `run_all.py --live` 全量跑完约几十次调用；内置演示数据量小，费用通常很低，但请自行留意用量。
- DeepSeek API 有并发与速率限制，触发限流或鉴权失败会返回 HTTP 4xx/5xx，
  客户端会包装成 `LiveLLMError` 并给出中文提示。
- token 统计沿用本地估算（`len(text) // 4`），与 DeepSeek 实际计费 token 存在偏差，
  统计数字仅用于演示对比，不代表真实账单。
- key 不要写进代码、README、测试或提交历史，不要在截图、日志、issue 中粘贴 key；
  一旦泄露请到 DeepSeek 控制台吊销并重发。

## 目录结构

```text
.
├── pyproject.toml                # 打包 / ruff / pytest 配置（含 [dependency-groups] dev）
├── uv.lock                       # uv 锁文件（uv sync 自动生成）
├── requirements.txt              # pip 用户的开发依赖
├── requirements-dev.txt
├── run_all.py                    # 统一入口
├── run_demo_sliding_window.py    # 方案一：滑动窗口摘要
├── run_demo_map_reduce.py        # 方案二：Map-Reduce 多文档聚合
├── run_demo_rag_lite.py          # 方案三：向量检索 RAG-lite
├── run_demo_structured_index.py  # 方案四：结构化索引
├── run_demo_overflow.py          # 补充演示：上下文溢出复现与规避
├── src/context_engineering/
│   ├── mock_llm.py               # MockLLM（窗口限制 / token 统计 / 单次最大 prompt 记录）
│   ├── live_llm.py               # LiveLLM（--live 时调用 DeepSeek 真实 API，接口与 MockLLM 一致）
│   ├── tokenizer.py              # token 估算（len // 4 近似）
│   ├── exceptions.py             # ContextOverflowError 等
│   ├── sliding_window.py         # 方案一实现
│   ├── map_reduce.py             # 方案二实现
│   ├── rag_lite.py               # 方案三实现
│   ├── structured_index.py       # 方案四实现
│   ├── utils/
│   │   ├── tfidf.py              # 纯 Python TF-IDF（中文 2-gram + 英文按词）
│   │   └── tree_index.py         # 目录树索引
│   └── data/                     # 内置 mock 数据（白皮书 / 新闻简报 / 问答对 / 代码库）
└── tests/                        # pytest 单测
```

## 已知限制

- **默认 MockLLM 是规则模拟器**：通过截取首尾句、关键词命中等规则生成"摘要"和"回答"，
  只用于验证上下文管理流程，不具备真实语言模型的语义质量；`--live` 时才走真实 DeepSeek API。
- **离线可跑**：不带 `--live` 时全程不联网、不调用任何 LLM 服务；
  带 `--live` 时才会真实联网调 DeepSeek API（会产生少量费用，见「接真实 API」一节）。
- **token 数为估算值**：统一用 `len(text) // 4` 近似（英文约 4 字符 1 token），
  中文按此口径会低估真实 token 数，与真实 tokenizer 存在偏差。
- **检索为教学简化版**：TF-IDF 中文按 2-gram 切分，无同义词与语义理解能力，
  检索质量不能与真实向量模型（embedding + 向量库）相比。
- **演示数据体量小**：内置 mock 数据（白皮书约 662 token、代码库约 1100 token），
  压缩比例仅供示意，真实场景中文档可达数十万 token。
- **Windows 控制台编码**：全部 demo 的输出只用中文和 ASCII 符号（GBK 可编码），
  不使用 emoji 或其它非 ASCII 符号；`run_all.py` 与 `run_demo_overflow.py` 入口统一做
  `sys.stdout.reconfigure(errors="replace")` 兜底（不可编码字符替换为 `?` 而不是崩溃，
  且不设置 `encoding="utf-8"`，避免 GBK 控制台下中文乱码）。默认 GBK 控制台可直接运行。
