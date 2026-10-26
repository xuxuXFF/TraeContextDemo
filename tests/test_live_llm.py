"""LiveLLM（真实 API 客户端）的测试。

全部用 monkeypatch 替换 urlopen 返回假响应，不打真网络；
key 一律用假的 "fake-key-for-test"，通过 monkeypatch.setenv 注入。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
from collections.abc import Callable
from pathlib import Path

import pytest

import context_engineering.live_llm as live_llm_module
from context_engineering.exceptions import ContextOverflowError, LiveLLMError
from context_engineering.live_llm import LiveLLM
from context_engineering.mock_llm import build_answer_prompt, build_summary_prompt

REPO_ROOT = Path(__file__).resolve().parent.parent

FAKE_KEY = "fake-key-for-test"


class _FakeResponse:
    """替代 urlopen 返回值的假响应，支持 with 上下文。"""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _payload_bytes(content: str) -> bytes:
    return json.dumps(
        {"choices": [{"message": {"role": "assistant", "content": content}}]}
    ).encode("utf-8")


def _ok_responder(content: str) -> Callable[[object], _FakeResponse]:
    def responder(_request: object) -> _FakeResponse:
        return _FakeResponse(_payload_bytes(content))

    return responder


def _install_fake_urlopen(
    monkeypatch: pytest.MonkeyPatch, responder: Callable[[object], object]
) -> list[object]:
    calls: list[object] = []

    def fake_urlopen(request: object, timeout: float | None = None) -> object:
        calls.append(request)
        return responder(request)

    monkeypatch.setattr(live_llm_module, "urlopen", fake_urlopen)
    return calls


def test_init_without_key_gives_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """没设 DEEPSEEK_API_KEY 时构造客户端，必须抛出含环境变量名的中文报错。"""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(LiveLLMError, match="DEEPSEEK_API_KEY"):
        LiveLLM()


def test_generate_overflow_raised_before_any_network_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """超窗口输入必须在发起任何网络请求之前抛 ContextOverflowError。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)
    llm = LiveLLM(max_context_tokens=10, max_output_tokens=5)
    calls = _install_fake_urlopen(monkeypatch, _ok_responder("x"))

    with pytest.raises(ContextOverflowError):
        llm.generate(
            "这段输入文本特意写得非常长，用来确保它的估算 token 数远超这个小模型的"
            "上下文窗口上限，从而在发起任何网络请求之前就触发溢出保护。"
        )

    assert calls == []


def test_generate_calls_deepseek_api_and_tracks_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """generate 发起的请求与 DeepSeek API 约定一致，统计口径与 MockLLM 相同。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)
    llm = LiveLLM(max_context_tokens=1000, max_output_tokens=100)
    calls = _install_fake_urlopen(monkeypatch, _ok_responder("真实回答内容"))

    answer = llm.generate("以下内容：\n正文内容")

    assert answer == "真实回答内容"
    assert len(calls) == 1
    request = calls[0]
    assert request.full_url == "https://api.deepseek.com/chat/completions"
    assert request.get_header("Authorization") == f"Bearer {FAKE_KEY}"
    body = json.loads(request.data.decode("utf-8"))
    assert body["model"] == "deepseek-chat"
    assert body["max_tokens"] == 100
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][0]["content"] == "以下内容：\n正文内容"

    assert llm.last_usage.prompt_tokens > 0
    assert llm.last_usage.completion_tokens > 0
    assert llm.total_usage.total_tokens == llm.last_usage.total_tokens
    assert llm.max_prompt_tokens_seen == llm.last_usage.prompt_tokens


def test_summarize_and_answer_share_mock_prompt_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LiveLLM 的 summarize/answer 与 MockLLM 用完全相同的 prompt 格式。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)
    llm = LiveLLM(max_context_tokens=1000, max_output_tokens=100)
    captured: list[str] = []

    def responder(request: object) -> _FakeResponse:
        body = json.loads(request.data.decode("utf-8"))
        captured.append(body["messages"][0]["content"])
        return _FakeResponse(_payload_bytes("ok"))

    _install_fake_urlopen(monkeypatch, responder)

    llm.summarize("正文甲", instruction="请摘要：")
    llm.answer("正文乙", "问题丙")

    assert captured[0] == build_summary_prompt("正文甲", instruction="请摘要：")
    assert captured[1] == build_answer_prompt("正文乙", "问题丙")


def test_http_error_wrapped_as_live_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 错误（如 401）包装为 LiveLLMError，且错误信息包含状态码。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)
    llm = LiveLLM()

    def responder(_request: object) -> object:
        raise urllib.error.HTTPError(
            "https://api.deepseek.com/chat/completions", 401, "Unauthorized", None, None
        )

    _install_fake_urlopen(monkeypatch, responder)
    with pytest.raises(LiveLLMError, match="401"):
        llm.generate("正文")


def test_url_error_wrapped_as_live_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """网络不可达等 URLError 包装为 LiveLLMError。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)
    llm = LiveLLM()

    def responder(_request: object) -> object:
        raise urllib.error.URLError("无法连接目标主机")

    _install_fake_urlopen(monkeypatch, responder)
    with pytest.raises(LiveLLMError, match="无法连接"):
        llm.generate("正文")


def test_malformed_response_wrapped_as_live_llm_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """非 JSON 响应包装为 LiveLLMError。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)
    llm = LiveLLM()
    _install_fake_urlopen(monkeypatch, lambda _req: _FakeResponse(b"not-json"))

    with pytest.raises(LiveLLMError, match="响应格式异常"):
        llm.generate("正文")


def test_reset_usage_clears_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)
    llm = LiveLLM(max_context_tokens=1000, max_output_tokens=100)
    _install_fake_urlopen(monkeypatch, _ok_responder("回答"))

    llm.generate("正文")
    llm.reset_usage()

    assert llm.last_usage.total_tokens == 0
    assert llm.total_usage.total_tokens == 0
    assert llm.max_prompt_tokens_seen == 0


def test_overflow_demo_live_without_key_fails() -> None:
    """--live 且无 key 时，demo 脚本以非零退出码结束并给出含环境变量名的提示。"""
    env = {k: v for k, v in os.environ.items() if k != "DEEPSEEK_API_KEY"}
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "run_demo_overflow.py"), "--live"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        timeout=60,
    )
    err = proc.stderr.decode("utf-8", errors="replace")
    out = proc.stdout.decode("utf-8", errors="replace")
    assert proc.returncode != 0
    assert "DEEPSEEK_API_KEY" in (err + out)
