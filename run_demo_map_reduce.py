"""方案二演示入口：Map-Reduce 多文档聚合。

直接运行：python run_demo_map_reduce.py
走真实 API：python run_demo_map_reduce.py --live（需设置 DEEPSEEK_API_KEY）
"""

from __future__ import annotations

import argparse

from context_engineering.data.news_briefings import NEWS_BRIEFINGS
from context_engineering.live_llm import LiveLLM
from context_engineering.map_reduce import map_reduce_aggregate
from context_engineering.mock_llm import MockLLM
from context_engineering.tokenizer import count_tokens


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="调用真实 DeepSeek API（需设置 DEEPSEEK_API_KEY）；默认走 MockLLM 离线演示",
    )
    args = parser.parse_args(argv)

    print("=" * 60)
    print("方案二：Map-Reduce 多文档聚合")
    print("=" * 60)

    if args.live:
        llm = LiveLLM(max_context_tokens=4000, max_output_tokens=600)
        print("LLM 客户端: LiveLLM（调用 DeepSeek 真实 API）")
    else:
        llm = MockLLM(max_context_tokens=4000, max_output_tokens=600)
        print("LLM 客户端: MockLLM（离线模拟）")

    total_orig = sum(count_tokens(d["content"]) for d in NEWS_BRIEFINGS)
    print(f"\n文档数量:          {len(NEWS_BRIEFINGS)} 篇新闻简报")
    print(f"   全部 token 合计:     {total_orig}")
    print(f"   模型窗口上限:        {llm.max_context_tokens} token")
    print("   [!] 直接把全部文档塞进模型会超限")

    def progress(msg: str) -> None:
        print(f"   {msg}")

    print("\n开始 Map-Reduce 聚合...")
    final, stats, _ = map_reduce_aggregate(llm, NEWS_BRIEFINGS, progress=progress)

    print("\nToken 统计:")
    print(f"   原始合计 token:      {stats['original_total_tokens']}")
    print(f"   Map 阶段合计 token:  {stats['map_stage_total_tokens']}")
    print(f"   最终聚合 token:      {stats['final_tokens']}")
    print(f"   LLM prompt token:    {stats['llm_prompt_tokens']}")
    print(f"   LLM completion token: {stats['llm_completion_tokens']}")

    print("\n聚合报告输出:")
    print(final)
    print("\n[完成] 演示结束\n")


if __name__ == "__main__":
    main()
