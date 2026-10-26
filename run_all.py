"""统一入口 —— 依次运行全部上下文工程案例演示。"""

from __future__ import annotations

import argparse
import sys
import traceback

from run_demo_map_reduce import main as demo2
from run_demo_overflow import main as demo5

# 把 run_demo_*.py 里的 main() 函数收集起来
from run_demo_rag_lite import main as demo3
from run_demo_sliding_window import main as demo1
from run_demo_structured_index import main as demo4


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="依次运行全部上下文工程案例演示")
    parser.add_argument(
        "--live",
        action="store_true",
        help="调用真实 DeepSeek API（需设置 DEEPSEEK_API_KEY）；默认走 MockLLM 离线演示",
    )
    args = parser.parse_args(argv)
    demo_argv = ["--live"] if args.live else []

    demos = [
        ("方案一：滑动窗口摘要", demo1),
        ("方案二：Map-Reduce 多文档聚合", demo2),
        ("方案三：向量检索 RAG-lite 长文档问答", demo3),
        ("方案四：结构化索引代码库问答", demo4),
        ("补充演示：上下文溢出复现与规避", demo5),
    ]

    print("=" * 60)
    print("上下文工程常见问题解决方案 —— 全量案例演示")
    print("=" * 60)
    mode = "LiveLLM（DeepSeek 真实 API）" if args.live else "MockLLM（离线模拟）"
    print(f"LLM 客户端: {mode}")

    results: list[tuple[str, bool]] = []
    for name, fn in demos:
        print(f"\n{'-' * 40}")
        print(f">> 运行 {name}")
        print(f"{'-' * 40}")
        try:
            fn(demo_argv)
            results.append((name, True))
        except Exception as exc:  # noqa: BLE001 —— 入口脚本需要兜底
            print(f"[FAIL] {name} 运行异常: {exc}")
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("全量运行结果汇总")
    print("=" * 60)
    ok_count = sum(1 for _, ok in results if ok)
    for name, ok in results:
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {status} —— {name}")
    print(f"\n总计: {ok_count}/{len(results)} 通过")

    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    # GBK 控制台兜底：不可编码字符替换为 ? 而不是崩溃。
    # 注意：不要设置 encoding="utf-8"，否则 GBK 控制台下中文会乱码。
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except Exception:
            pass
    sys.exit(main())
