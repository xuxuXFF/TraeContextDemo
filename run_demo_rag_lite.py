"""方案三演示入口：向量检索 RAG-lite 长文档问答。

直接运行：python run_demo_rag_lite.py
或者：    python run_demo_rag_lite.py --question "你的问题"
走真实 API：加 --live（需设置 DEEPSEEK_API_KEY）
"""

from __future__ import annotations

import argparse

from context_engineering.data.qa_pairs import QA_PAIRS
from context_engineering.data.tech_whitepaper import WHITEPAPER_TEXT
from context_engineering.live_llm import LiveLLM
from context_engineering.mock_llm import MockLLM
from context_engineering.rag_lite import RagLite
from context_engineering.tokenizer import count_tokens

DEFAULT_QUESTIONS = [
    "下一代企业智能客服系统采用了什么总体架构？",
    "解决大模型幻觉问题的关键技术方案是什么？",
    "企业应该如何推进 AI 客服落地？",
]


def run_query(qa: RagLite, question: str) -> None:
    print(f"\n   问题: {question}")
    answer, stats, hits = qa.query(question)
    print(f"   命中 chunk 索引: {hits}")
    print(f"   检索到的上下文 token: {stats['hit_token_count']}")
    print(f"   检索覆盖率: {stats['context_ratio']:.1%}（命中 chunk / 全量 chunk）")
    print(f"   回答: {answer}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", type=str, default=None, help="单个问题；不传则轮询演示内置问题")
    parser.add_argument(
        "--live",
        action="store_true",
        help="调用真实 DeepSeek API（需设置 DEEPSEEK_API_KEY）；默认走 MockLLM 离线演示",
    )
    args = parser.parse_args(argv)

    print("=" * 60)
    print("方案三：向量检索 RAG-lite 长文档问答")
    print("=" * 60)

    if args.live:
        llm = LiveLLM(max_context_tokens=2000, max_output_tokens=500)
        print("LLM 客户端: LiveLLM（调用 DeepSeek 真实 API）")
    else:
        llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
        print("LLM 客户端: MockLLM（离线模拟）")

    orig_tokens = count_tokens(WHITEPAPER_TEXT)
    print(f"\n白皮书 token: {orig_tokens}")
    print(f"   模型窗口:      {llm.max_context_tokens} token")
    print("   构建索引并切 chunk...")

    qa = RagLite(llm, WHITEPAPER_TEXT, top_k=3)
    print(f"   切分 chunk 数量: {len(qa.chunks)}（实际检索时只取 top-{qa.top_k} 相关片段）")

    if args.question:
        run_query(qa, args.question)
    else:
        print(f"\n内置 QA 对（{len(QA_PAIRS)} 组）:")
        for q, _ in QA_PAIRS:
            run_query(qa, q)

    print("\n[完成] 演示结束\n")


if __name__ == "__main__":
    main()
