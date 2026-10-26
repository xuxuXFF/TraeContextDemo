"""方案一演示入口：滑动窗口长文档摘要。

直接运行：python run_demo_sliding_window.py
走真实 API：python run_demo_sliding_window.py --live（需设置 DEEPSEEK_API_KEY）
"""

from __future__ import annotations

import argparse

from context_engineering.data.tech_whitepaper import WHITEPAPER_TEXT
from context_engineering.live_llm import LiveLLM
from context_engineering.mock_llm import MockLLM
from context_engineering.sliding_window import sliding_window_summarize
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
    print("方案一：滑动窗口摘要 (Sliding Window Summarization)")
    print("=" * 60)

    # 模拟一个较小的上下文窗口，体现长文档的窗口压力
    if args.live:
        llm = LiveLLM(max_context_tokens=2000, max_output_tokens=500)
        print("LLM 客户端: LiveLLM（调用 DeepSeek 真实 API）")
    else:
        llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
        print("LLM 客户端: MockLLM（离线模拟）")

    orig_tokens = count_tokens(WHITEPAPER_TEXT)
    print(f"\n原始白皮书字符数: {len(WHITEPAPER_TEXT)}")
    print(f"   估算 token 数:    {orig_tokens}")
    print(f"   模型窗口上限:     {llm.max_context_tokens} token")
    print("   [!] 无法一次性送入模型，需要滑动窗口处理")

    def progress(n: int, total: int) -> None:
        print(f"   Map 进度: [{n}/{total}] 正在处理窗口...")

    print("\n开始滑动窗口处理...")
    final, stats = sliding_window_summarize(llm, WHITEPAPER_TEXT, progress=progress)

    print("\nToken 统计:")
    print(f"   原始 token 数:     {stats['original_tokens']}")
    print(f"   切分窗口数:         {stats['num_chunks']}")
    print(f"   Map 阶段输出 token: {stats['map_stage_tokens']}")
    print(f"   Reduce 输入 token:  {stats['reduce_stage_input_tokens']}")
    print(f"   最终摘要 token:     {stats['final_tokens']}")
    print(f"   Token 压缩比:       {stats['token_reduction_ratio']:.1%}")
    print(f"   LLM 总 prompt token: {stats['total_llm_prompt_tokens']}")
    print(f"   LLM 总 completion token: {stats['total_llm_completion_tokens']}")

    print("\n最终摘要输出:")
    print(final)
    print("\n[完成] 演示结束\n")


if __name__ == "__main__":
    main()
