"""MockLLM —— 模拟真实 LLM 的行为，纯本地可运行，无需外部 API。

模拟能力：
- token 计数（复用 tokenizer.count_tokens）
- 上下文窗口限制（超限抛 ContextOverflowError）
- 输出 token 限制（截断到 max_output_tokens）
- 调用结果根据 prompt 模式生成（摘要用首尾拼接、问答用关键词附近段落）
- 累计 token 统计（方便 demo 展示节省效果）
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .exceptions import ContextOverflowError
from .tokenizer import count_tokens, truncate_to_tokens


@dataclass
class UsageStats:
    """一次 / 累计调用的 token 统计。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


# 摘要策略中挑选关键句时关注的关键词
_SUMMARY_KEYWORDS = [
    "是", "为", "包含", "采用", "基于", "核心", "关键", "主要",
    "includes", "uses", "based",
]

# _extract_body 中用来标记正文开始的 prompt 内关键字
_BODY_MARKERS = [
    "以下内容：", "以下内容:",
    "以下文本：", "以下文本:",
    "文档内容：", "文本内容：",
]


# Mock 与 Live 两种客户端共用的 prompt 构造器，保证两者的输入格式完全一致
DEFAULT_SUMMARY_INSTRUCTION = "请对以下内容生成简明摘要："


def build_summary_prompt(text: str, instruction: str = DEFAULT_SUMMARY_INSTRUCTION) -> str:
    return f"{instruction}\n以下内容：\n{text}"


def build_answer_prompt(text: str, question: str) -> str:
    return f"请根据以下内容回答问题。\n以下内容：\n{text}\n\n问题：{question}"


class MockLLM:
    """模拟 LLM，支持上下文窗口检查和多种模拟输出策略。"""

    def __init__(
        self,
        max_context_tokens: int = 8000,
        max_output_tokens: int = 1000,
    ) -> None:
        self.max_context_tokens = max_context_tokens
        self.max_output_tokens = max_output_tokens
        # 累计统计
        self.total_usage = UsageStats()
        # 最近一次调用统计
        self.last_usage = UsageStats()
        # 历史调用中单次最大的 prompt token（reset_usage 时清零），用于溢出演示
        self.max_prompt_tokens_seen = 0

    # ---- 公开 API ----

    def token_count(self, text: str) -> int:
        return count_tokens(text)

    def generate(self, prompt: str, mode: str = "auto") -> str:
        """调用 MockLLM 生成结果。

        Args:
            prompt: 输入上下文
            mode: "auto" 根据 prompt 特征自动选策略；
                  "summary" 摘要策略；"qa" 问答策略
        """
        prompt_tokens = count_tokens(prompt)
        if prompt_tokens > self.max_context_tokens:
            raise ContextOverflowError(
                f"prompt token {prompt_tokens} 超出 max_context_tokens={self.max_context_tokens}"
            )

        # 生成模拟输出
        answer = self._produce_output(prompt, mode)

        # 检查输出上限
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

    # ---- 内部 ----

    def _produce_output(self, prompt: str, mode: str) -> str:
        """根据 prompt 特征生成模拟输出。"""
        if mode == "summary" or (mode == "auto" and self._looks_like_summary_prompt(prompt)):
            return self._mock_summary(prompt)
        if mode == "qa" or (mode == "auto" and self._looks_like_qa_prompt(prompt)):
            return self._mock_qa(prompt)
        # 默认返回简单回显
        return self._mock_default(prompt)

    def _looks_like_summary_prompt(self, prompt: str) -> bool:
        keywords = ["摘要", "总结", "summary", "summarize", "总结一下", "要点"]
        lower = prompt.lower()
        return any(k.lower() in lower for k in keywords)

    def _looks_like_qa_prompt(self, prompt: str) -> bool:
        # 问答 prompt 通常长这样：「请根据以下内容回答：...\n问题：xxx」
        return "问题" in prompt or "question" in prompt.lower() or "回答" in prompt

    def _mock_summary(self, prompt: str) -> str:
        """模拟摘要：取 prompt 尾部的被摘要文本，截取首段 + 末段 + 若干关键语句。"""
        body = self._extract_body(prompt)
        if not body:
            return "（Mock 摘要）输入文本过长，已生成简化摘要。"

        # 按句子切分（中英文混合标点）
        sentences = re.split(r"(?<=[。！？.!?])\s+", body.strip())

        # 关键句筛选
        head = (
            " ".join(sentences[:2]) if len(sentences) >= 2
            else (sentences[0] if sentences else "")
        )
        tail = (
            " ".join(sentences[-2:]) if len(sentences) >= 2
            else (sentences[-1] if sentences else "")
        )
        middle: list[str] = []
        for s in sentences[2:-2]:
            if any(w in s.lower() for w in _SUMMARY_KEYWORDS):
                middle.append(s)
            if len(middle) >= 2:
                break

        parts = ["（Mock 摘要）"]
        if head:
            parts.append(f"要点一：{head[:120]}")
        if middle:
            parts.append(f"要点二：{' '.join(middle)[:120]}")
        if tail and tail != head:
            parts.append(f"要点三：{tail[:120]}")
        return "\n".join(parts)

    def _mock_qa(self, prompt: str) -> str:
        """模拟问答：找到 prompt 中的问题关键词，在正文中找包含它的句子。"""
        question_match = re.search(r"(?:问题|question)[:：]\s*(.+)", prompt, re.IGNORECASE)
        question = question_match.group(1).strip() if question_match else ""

        # 提取关键词（简单按空格/中文标点切）
        keywords = [w for w in re.split(r"[\s，,。.？?！!、;；]+", question) if len(w) >= 2]
        if not keywords:
            keywords = [question] if question else []

        body = self._extract_body(prompt)
        sentences = re.split(r"(?<=[。！？.!?])\s+", body.strip()) if body else []

        hits: list[str] = []
        for s in sentences:
            for kw in keywords:
                if kw in s:
                    hits.append(s)
                    break
            if len(hits) >= 2:
                break

        if hits:
            return "（Mock 回答）" + " ".join(hits)[:300]
        return f"（Mock 回答）正文中未找到关于「{question or '该问题'}」的明确信息。"

    def _mock_default(self, prompt: str) -> str:
        body = self._extract_body(prompt)
        if body:
            return f"（Mock 输出）已接收 {count_tokens(body)} token 的输入，此处生成占位回复。"
        return "（Mock 输出）空输入。"

    @staticmethod
    def _extract_body(prompt: str) -> str:
        """约定：prompt 中出现「以下内容：」或「以下文本」之后是正文。"""
        for marker in _BODY_MARKERS:
            idx = prompt.find(marker)
            if idx >= 0:
                return prompt[idx + len(marker):].strip()
        # 没有标记就直接返回整个 prompt
        return prompt

    # ---- 便捷方法 ----

    def summarize(self, text: str, instruction: str = DEFAULT_SUMMARY_INSTRUCTION) -> str:
        return self.generate(build_summary_prompt(text, instruction), mode="summary")

    def answer(self, text: str, question: str) -> str:
        return self.generate(build_answer_prompt(text, question), mode="qa")
