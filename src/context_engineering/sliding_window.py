"""方案一：滑动窗口摘要（Sliding Window Summarization）。

问题背景：
当文档 token 数超过 LLM 上下文窗口时，无法一次性送入模型生成摘要。
滑动窗口方案将文档切成多个 token 可控的窗口，逐片生成局部摘要，
再对所有局部摘要做二次调用生成最终摘要。

方案优势：
- 充分利用有限窗口，每片都能完整送入
- 保留了跨窗口通过 overlap 衔接的语义连续性
"""

from __future__ import annotations

from typing import Callable

from context_engineering.mock_llm import MockLLM
from context_engineering.tokenizer import count_tokens


def chunk_text(
    text: str,
    max_tokens: int,
    overlap_chars: int = 80,
) -> list[str]:
    """按 token 限制将文本切片，相邻 chunk 重叠 overlap_chars 避免句被切断。"""
    if count_tokens(text) <= max_tokens:
        return [text]

    max_chars = max_tokens * 4
    chunks: list[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + max_chars, n)
        # 尽量在句末 / 换行处切
        if end < n:
            cutoff = max(start + max_chars - 50, start + max_chars // 2)
            for sep in ["\n\n", "\n", "。", ".", "！", "!", "？", "?"]:
                pos = text.rfind(sep, cutoff, end)
                if pos > 0:
                    end = pos + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # 下一片起始位置 = end - overlap
        next_start = end - overlap_chars
        if next_start <= start:
            next_start = end  # 强制推进防止死循环
        start = next_start

    return chunks


def sliding_window_summarize(
    llm: MockLLM,
    text: str,
    chunk_max_tokens: int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[str, dict]:
    """完整滑动窗口摘要流程。

    Args:
        llm: MockLLM 实例（调用前请先 reset_usage）
        text: 待摘要长文本
        chunk_max_tokens: 每个窗口的最大 token 数，默认 = 模型 max_context_tokens 的 60%
        progress: 进度回调 progress(当前第 n 片, 总共 N 片)

    Returns:
        (最终摘要, 统计信息 dict)
    """
    llm.reset_usage()

    if chunk_max_tokens is None:
        chunk_max_tokens = int(llm.max_context_tokens * 0.6)

    original_tokens = count_tokens(text)
    chunks = chunk_text(text, chunk_max_tokens)

    # Map 阶段：逐片摘要
    local_summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        if progress:
            progress(i + 1, len(chunks))
        summary = llm.summarize(chunk, instruction="请对以下段落生成简短摘要：")
        local_summaries.append(summary)

    # Reduce 阶段：汇总所有局部摘要。
    # 真实 LLM 的局部摘要通常远长于 Mock 输出，拼接后可能再次超出窗口，
    # 因此先做有界折叠：把 Reduce 输入压到安全范围，再生成最终摘要。
    all_summaries = "\n---\n".join(local_summaries)
    reduce_max_tokens = int(llm.max_context_tokens * 0.6)
    for _ in range(5):
        if count_tokens(all_summaries) <= reduce_max_tokens:
            break
        fold_chunks = chunk_text(all_summaries, reduce_max_tokens)
        if len(fold_chunks) <= 1:
            break
        all_summaries = "\n---\n".join(
            llm.summarize(c, instruction="以下是原文的局部摘要，请折叠为更简短的摘要：")
            for c in fold_chunks
        )
    final_summary = llm.summarize(
        all_summaries,
        instruction="以下是对原文各章节的局部摘要，请汇总生成一份完整的核心内容摘要：",
    )

    stats = {
        "original_tokens": original_tokens,
        "num_chunks": len(chunks),
        "map_stage_tokens": sum(count_tokens(s) for s in local_summaries),
        "reduce_stage_input_tokens": count_tokens(all_summaries),
        "final_tokens": count_tokens(final_summary),
        "total_llm_prompt_tokens": llm.total_usage.prompt_tokens,
        "total_llm_completion_tokens": llm.total_usage.completion_tokens,
        "token_reduction_ratio": (
            round(final_summary_tokens / original_tokens, 3) if original_tokens else 1.0
        ) if (final_summary_tokens := count_tokens(final_summary)) else 1.0,
    }
    return final_summary, stats
