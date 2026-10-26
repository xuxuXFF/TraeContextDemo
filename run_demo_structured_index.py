"""方案四演示入口：结构化索引代码库问答。

直接运行：python run_demo_structured_index.py
或者：    python run_demo_structured_index.py --query "你的查询"
走真实 API：加 --live（需设置 DEEPSEEK_API_KEY）
"""

from __future__ import annotations

import argparse

from context_engineering.data.codebase_mock import CODEBASE_TREE, flatten_tree
from context_engineering.live_llm import LiveLLM
from context_engineering.mock_llm import MockLLM
from context_engineering.structured_index import StructuredIndexQA
from context_engineering.tokenizer import count_tokens

DEFAULT_QUERIES = [
    "auth token",
    "order create",
    "MongoDB Redis",
]


def run_query(qa: StructuredIndexQA, query: str) -> None:
    print(f"\n   查询: {query}")
    answer, stats, paths = qa.query(query)
    print(f"   加载文件数: {stats['matched_files']} / {stats['total_files']}")
    print(f"   加载比例:   {stats['loaded_ratio']:.1%}")
    print(f"   加载文件路径: {paths}")
    print(f"   回答: {answer}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default=None)
    parser.add_argument(
        "--live",
        action="store_true",
        help="调用真实 DeepSeek API（需设置 DEEPSEEK_API_KEY）；默认走 MockLLM 离线演示",
    )
    args = parser.parse_args(argv)

    print("=" * 60)
    print("方案四：结构化索引代码库问答")
    print("=" * 60)

    if args.live:
        llm = LiveLLM(max_context_tokens=2000, max_output_tokens=500)
        print("LLM 客户端: LiveLLM（调用 DeepSeek 真实 API）")
    else:
        llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
        print("LLM 客户端: MockLLM（离线模拟）")

    flat = flatten_tree(CODEBASE_TREE)
    total_tokens = sum(count_tokens(v) for v in flat.values())

    print(f"\n模拟代码库文件数: {len(flat)}")
    print(f"   全量 token 合计:    {total_tokens}")
    print(f"   模型窗口:           {llm.max_context_tokens} token")
    print("   [!] 全量送入模型会严重超限，结构化索引只加载相关子树")

    qa = StructuredIndexQA(llm, CODEBASE_TREE)

    if args.query:
        run_query(qa, args.query)
    else:
        for q in DEFAULT_QUERIES:
            run_query(qa, q)

    print("\n[完成] 演示结束\n")


if __name__ == "__main__":
    main()
