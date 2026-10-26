"""LiveLLM —— 真实 LLM 客户端，调用 DeepSeek chat API。

与 MockLLM 保持一致的调用签名和返回结构：
- generate / summarize / answer / token_count / reset_usage
- UsageStats 统计与 max_prompt_tokens_seen 记录
- token 统计复用 tokenizer.count_tokens，超窗口仍抛 ContextOverflowError
  （溢出检查在发起网络请求之前完成，不会浪费一次调用）

API Key 只从环境变量 DEEPSEEK_API_KEY 读取，不落代码、不落日志。
"""

from __future__ import annotations

import json
import os
import urllib.error
from urllib.request import Request, urlopen

from .exceptions import ContextOverflowError, LiveLLMError
from .mock_llm import (
    DEFAULT_SUMMARY_INSTRUCTION,
    UsageStats,
    build_answer_prompt,
    build_summary_prompt,
)
from .tokenizer import count_tokens, truncate_to_tokens

API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
REQUEST_TIMEOUT_SECONDS = 120


class LiveLLM:
    """调用 DeepSeek /chat/completions 的真实 LLM 客户端，接口与 MockLLM 一致。"""

    def __init__(
        self,
        max_context_tokens: int = 8000,
        max_output_tokens: int = 1000,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        api_key = os.environ.get(API_KEY_ENV, "")
        if not api_key:
            raise LiveLLMError(
                f"未在环境变量中找到 {API_KEY_ENV}，无法调用真实 LLM。"
                f"请先设置该环境变量：PowerShell 当前会话用 "
                f"$env:{API_KEY_ENV}=\"你的key\"；永久生效用 setx {API_KEY_ENV} \"你的key\""
                "（setx 后需重开终端）。"
                "注意：key 只通过环境变量注入，不要写进代码或提交到仓库。"
            )
        self.max_context_tokens = max_context_tokens
        self.max_output_tokens = max_output_tokens
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._api_key = api_key
        # 累计 / 最近一次统计，口径与 MockLLM 完全一致
        self.total_usage = UsageStats()
        self.last_usage = UsageStats()
        self.max_prompt_tokens_seen = 0

    # ---- 公开 API ----

    def token_count(self, text: str) -> int:
        return count_tokens(text)

    def generate(self, prompt: str, mode: str = "auto") -> str:
        """调用真实 LLM 生成结果。

        Args:
            prompt: 输入上下文
            mode: 仅为兼容 MockLLM 签名保留，真实 API 不区分模式
        """
        prompt_tokens = count_tokens(prompt)
        if prompt_tokens > self.max_context_tokens:
            raise ContextOverflowError(
                f"prompt token {prompt_tokens} 超出 max_context_tokens={self.max_context_tokens}"
            )

        answer = self._call_api(prompt)

        # 输出上限与统计口径和 MockLLM 一致
        answer_tokens = count_tokens(answer)
        if answer_tokens > self.max_output_tokens:
            answer = truncate_to_tokens(answer, self.max_output_tokens)
            answer_tokens = count_tokens(answer)

        self.last_usage = UsageStats(prompt_tokens, answer_tokens, prompt_tokens + answer_tokens)
        self.max_prompt_tokens_seen = max(self.max_prompt_tokens_seen, prompt_tokens)
        self.total_usage.prompt_tokens += prompt_tokens
        self.total_usage.completion_tokens += answer_tokens
        self.total_usage.total_tokens += prompt_tokens + answer_tokens

        return answer

    def reset_usage(self) -> None:
        self.total_usage = UsageStats()
        self.last_usage = UsageStats()
        self.max_prompt_tokens_seen = 0

    # ---- 便捷方法（与 MockLLM 相同的 prompt 格式） ----

    def summarize(self, text: str, instruction: str = DEFAULT_SUMMARY_INSTRUCTION) -> str:
        return self.generate(build_summary_prompt(text, instruction), mode="summary")

    def answer(self, text: str, question: str) -> str:
        return self.generate(build_answer_prompt(text, question), mode="qa")

    # ---- 内部 ----

    def _call_api(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_output_tokens,
        }
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise LiveLLMError(
                f"DeepSeek API 返回 HTTP {exc.code}，请检查 API Key 是否有效、"
                "账户余额与限流情况"
            ) from exc
        except urllib.error.URLError as exc:
            raise LiveLLMError(f"无法连接 DeepSeek API: {exc.reason}") from exc

        try:
            content = json.loads(raw)["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise LiveLLMError(
                "DeepSeek API 响应格式异常，无法解析 choices[0].message.content"
            ) from exc
        if not isinstance(content, str):
            raise LiveLLMError("DeepSeek API 响应格式异常，choices[0].message.content 不是字符串")
        return content
