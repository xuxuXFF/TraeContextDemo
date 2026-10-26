"""方案二：Map-Reduce 多文档聚合。

问题背景：
需要从多份独立文档中汇总信息生成统一报告，但所有文档合起来 token 数超限。
Map-Reduce 方案先对每份文档单独生成摘要（Map 阶段），再把所有摘要拼起来
生成最终聚合报告（Reduce 阶段）。
"""

from __future__ import annotations

from typing import Callable

from context_engineering.mock_llm import MockLLM
from context_engineering.tokenizer import count_tokens


def map_reduce_aggregate(
    llm: MockLLM,
    documents: list[dict],  # [{title, content, tag}] 或 [{content}]
    reduce_max_tokens: int | None = None,
    progress: Callable[[str], None] | None = None,
) -> tuple[str, dict, list[str]]:
    """多文档 Map-Reduce 聚合。

    Args:
        llm: MockLLM 实例
        documents: 文档列表，每个元素至少含 'content' 字段
        reduce_max_tokens: Reduce 阶段输入 token 上限（超限则对 Map 摘要再做一次预汇总）
        progress: 阶段回调

    Returns:
        (最终聚合报告, 统计信息 dict, 每篇文档的 Map 摘要列表)
    """
    llm.reset_usage()

    if reduce_max_tokens is None:
        reduce_max_tokens = int(llm.max_context_tokens * 0.6)

    # Map 阶段
    local_summaries: list[str] = []
    for i, doc in enumerate(documents):
        content = doc["content"] if isinstance(doc, dict) else str(doc)
        title = doc.get("title", f"文档{i+1}") if isinstance(doc, dict) else f"文档{i+1}"
        if progress:
            progress(f"Map: 正在摘要「{title}」")
        summary = llm.summarize(content, instruction=f"请对以下内容生成一段简明摘要（{title}）：")
        local_summaries.append(summary)

    # 如果所有 Map 摘要拼起来仍超限，先做一次预汇总
    combined = "\n---\n".join(local_summaries)
    if count_tokens(combined) > reduce_max_tokens:
        if progress:
            progress("Reduce 预汇总: Map 摘要总长超限，先折叠一轮")
        combined = llm.summarize(
            combined, instruction="以下是多篇文档的局部摘要，请先折叠为一份总摘要："
        )

    # Reduce 阶段
    if progress:
        progress("Reduce: 生成最终聚合报告")
    final = llm.summarize(
        combined,
        instruction=(
            "以下是多篇新闻简报的摘要汇总，请生成一份跨主题的统一聚合报告，"
            "覆盖每个主题的关键信息："
        ),
    )

    original_total = sum(
        count_tokens(doc["content"] if isinstance(doc, dict) else str(doc)) for doc in documents
    )
    map_total = sum(count_tokens(s) for s in local_summaries)
    final_tokens = count_tokens(final)

    stats = {
        "num_documents": len(documents),
        "original_total_tokens": original_total,
        "map_stage_total_tokens": map_total,
        "final_tokens": final_tokens,
        "llm_prompt_tokens": llm.total_usage.prompt_tokens,
        "llm_completion_tokens": llm.total_usage.completion_tokens,
    }
    return final, stats, local_summaries
