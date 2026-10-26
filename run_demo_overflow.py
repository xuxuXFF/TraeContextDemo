"""上下文溢出演示：先复现 ContextOverflowError，再展示用滑动窗口策略规避。

与其它 demo 不同，本脚本输出只用中文和 ASCII 符号（避免 Windows GBK 控制台编码问题），
并在入口处对 stdout 设置 errors="replace" 兜底（不改变控制台编码，避免中文乱码）。

直接运行：python run_demo_overflow.py
走真实 API：python run_demo_overflow.py --live（需设置 DEEPSEEK_API_KEY；
注意溢出复现发生在客户端本地、不发起请求，只有第二阶段的滑动窗口摘要会真实调 API）
"""

from __future__ import annotations

import argparse
import sys

from context_engineering.data.tech_whitepaper import WHITEPAPER_TEXT
from context_engineering.exceptions import ContextOverflowError
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
    print("[补充演示] 上下文溢出复现与规避 (Context Overflow)")
    print("=" * 60)

    # 故意用一个小窗口（500 token），白皮书约 662 token，直接塞必然溢出
    if args.live:
        llm = LiveLLM(max_context_tokens=500, max_output_tokens=300)
        print("\nLLM 客户端: LiveLLM（调用 DeepSeek 真实 API）")
    else:
        llm = MockLLM(max_context_tokens=500, max_output_tokens=300)
        print("\nLLM 客户端: MockLLM（离线模拟）")
    orig_tokens = count_tokens(WHITEPAPER_TEXT)

    print()
    print("[1] 直接把整篇白皮书塞进模型，复现上下文溢出")
    print(f"    白皮书实际 token: {orig_tokens}")
    print(f"    模型窗口上限:     {llm.max_context_tokens}")
    try:
        llm.summarize(WHITEPAPER_TEXT)
        print("    [FAIL] 未触发异常，不符合预期")
    except ContextOverflowError as exc:
        print(f"    [OK] 捕获 ContextOverflowError: {exc}")
        print(
            f"    结论: 白皮书 {orig_tokens} token，加上指令后超出上限 "
            f"{llm.max_context_tokens} token，直接调用必然失败"
        )

    print()
    print("[2] 同一输入改用滑动窗口策略（每片正文 <= 300 token）")
    final, stats = sliding_window_summarize(llm, WHITEPAPER_TEXT, chunk_max_tokens=300)
    print(f"    切分窗口数:                {stats['num_chunks']}")
    print(
        f"    单次调用最大 prompt token: {llm.max_prompt_tokens_seen}"
        f" (窗口上限 {llm.max_context_tokens})"
    )
    print(f"    最终摘要 token:            {stats['final_tokens']}")
    print(f"    Token 压缩比:              {stats['token_reduction_ratio']:.1%}")
    print("    结论: 全程单次调用均未超过窗口上限，同一输入成功跑通")
    print()
    print("[完成] 溢出演示结束")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            # 只替换不可编码字符，不改变控制台编码（GBK 下设 utf-8 会导致中文乱码）
            sys.stdout.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001 —— 编码重配置失败不影响演示本身
            pass
    main()
