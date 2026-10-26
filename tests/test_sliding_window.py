"""滑动窗口方案测试。"""

from context_engineering.data.tech_whitepaper import WHITEPAPER_TEXT
from context_engineering.mock_llm import MockLLM
from context_engineering.sliding_window import chunk_text, sliding_window_summarize
from context_engineering.tokenizer import count_tokens


def test_chunk_text_splits_oversized():
    big = "测试内容。" * 500  # 2500 字符 ≈ 625 token
    chunks = chunk_text(big, max_tokens=100)
    assert len(chunks) > 1
    # 所有 chunk token 数都 <= max_tokens（允许略超因为句末对齐）
    for c in chunks:
        assert count_tokens(c) <= 100 + 20


def test_chunk_text_single_for_short():
    short = "这是一小段话，不需要切分。"
    chunks = chunk_text(short, max_tokens=1000)
    assert len(chunks) == 1


def test_sliding_window_reduces_token_count():
    llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
    final, stats = sliding_window_summarize(llm, WHITEPAPER_TEXT, chunk_max_tokens=600)

    # 最终摘要 token 必须远小于原文
    assert stats["final_tokens"] < stats["original_tokens"] * 0.5
    # 统计信息完整
    assert "original_tokens" in stats
    assert "num_chunks" in stats
    assert stats["num_chunks"] >= 2


def test_sliding_window_produces_summary_text():
    llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
    final, _ = sliding_window_summarize(llm, WHITEPAPER_TEXT, chunk_max_tokens=600)
    assert "Mock 摘要" in final or len(final) > 20
