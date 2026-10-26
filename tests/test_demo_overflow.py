"""上下文溢出演示的测试。"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from context_engineering.data.tech_whitepaper import WHITEPAPER_TEXT
from context_engineering.exceptions import ContextOverflowError
from context_engineering.mock_llm import MockLLM
from context_engineering.sliding_window import sliding_window_summarize
from context_engineering.tokenizer import count_tokens

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_oversized_input_raises_overflow():
    """超长输入直接塞进小窗口模型，必须抛 ContextOverflowError，且报错含实际 token 数与上限。"""
    llm = MockLLM(max_context_tokens=500)
    assert count_tokens(WHITEPAPER_TEXT) > llm.max_context_tokens

    with pytest.raises(ContextOverflowError) as exc_info:
        llm.summarize(WHITEPAPER_TEXT)

    msg = str(exc_info.value)
    # 报错必须同时给出实际 prompt token 数和窗口上限，且实际值确实超限
    match = re.search(r"prompt token (\d+)", msg)
    assert match, msg
    assert int(match.group(1)) > llm.max_context_tokens
    assert str(llm.max_context_tokens) in msg


def test_sliding_window_same_input_stays_within_window():
    """同一输入换滑动窗口策略后跑通，且全程单次调用 prompt 不超窗口上限。"""
    llm = MockLLM(max_context_tokens=500, max_output_tokens=300)
    final, stats = sliding_window_summarize(llm, WHITEPAPER_TEXT, chunk_max_tokens=300)

    assert llm.max_prompt_tokens_seen <= llm.max_context_tokens
    assert stats["final_tokens"] < stats["original_tokens"]
    assert final


def test_demo_script_runs_and_reports_overflow():
    """demo 脚本作为子进程运行退出码 0，输出包含溢出捕获与规避结论。"""
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "run_demo_overflow.py")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        timeout=120,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    assert proc.returncode == 0, out
    assert "ContextOverflowError" in out
    assert "[OK]" in out
