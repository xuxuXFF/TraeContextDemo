"""RAG-lite 方案测试。"""

from context_engineering.data.qa_pairs import QA_PAIRS
from context_engineering.data.tech_whitepaper import WHITEPAPER_TEXT
from context_engineering.mock_llm import MockLLM
from context_engineering.rag_lite import RagLite


def test_rag_index_builds_and_queries():
    llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
    qa = RagLite(llm, WHITEPAPER_TEXT, top_k=3)
    assert len(qa.chunks) >= 3

    ans, stats, hits = qa.query("总体架构")
    assert ans
    assert stats["hit_indices"]
    assert stats["context_ratio"] > 0


def test_rag_qa_hit_rate():
    """内置 QA 对的命中率应该 >= 60%（答案关键词出现在检索到的 chunk 中）。"""
    llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
    qa = RagLite(llm, WHITEPAPER_TEXT, top_k=3)

    hits = 0
    for question, keywords in QA_PAIRS:
        results = qa.index.search(question, top_k=3)
        # 取 top-3 chunks 内容（search 返回 list[tuple[int, float]]）
        top_chunks = [qa.chunks[idx] for idx, _ in results]
        combined = " ".join(top_chunks)
        if any(kw in combined for kw in keywords):
            hits += 1

    rate = hits / len(QA_PAIRS)
    assert rate >= 0.6, f"QA 命中率 {rate:.1%} 低于 60%，实际检索效果差"


def test_rag_context_not_exceeding_window():
    llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
    qa = RagLite(llm, WHITEPAPER_TEXT, top_k=3)
    _, stats, _ = qa.query("检索增强生成")
    # 检索到的上下文 + prompt 不应超限（llm_prompt_tokens 由 MockLLM 自己算）
    assert stats["hit_token_count"] < llm.max_context_tokens
