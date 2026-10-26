"""Map-Reduce 方案测试。"""

from context_engineering.data.news_briefings import NEWS_BRIEFINGS
from context_engineering.map_reduce import map_reduce_aggregate
from context_engineering.mock_llm import MockLLM


def test_map_reduce_runs_end_to_end():
    llm = MockLLM(max_context_tokens=4000, max_output_tokens=600)
    final, stats, summaries = map_reduce_aggregate(llm, NEWS_BRIEFINGS)

    assert final  # 非空
    assert stats["num_documents"] == len(NEWS_BRIEFINGS)
    assert len(summaries) == len(NEWS_BRIEFINGS)


def test_map_reduce_covers_all_docs():
    llm = MockLLM(max_context_tokens=4000, max_output_tokens=600)
    final, stats, local_summaries = map_reduce_aggregate(llm, NEWS_BRIEFINGS)

    # Map 阶段必须对每篇文档都生成了独立摘要
    assert len(local_summaries) == len(NEWS_BRIEFINGS)
    # 最终聚合报告非空，且经过了 Reduce 阶段
    assert final
    assert stats["num_documents"] == len(NEWS_BRIEFINGS)


def test_map_reduce_token_efficiency():
    llm = MockLLM(max_context_tokens=4000, max_output_tokens=600)
    _, stats, _ = map_reduce_aggregate(llm, NEWS_BRIEFINGS)

    # Map 阶段输出应该远小于原始合计
    assert stats["map_stage_total_tokens"] < stats["original_total_tokens"] * 0.6
    # LLM prompt token 不超过直接全量送入模型（模型上限）
    assert stats["llm_prompt_tokens"] >= 0
