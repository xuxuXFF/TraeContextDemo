"""MockLLM 的基础单元测试。"""

import pytest

from context_engineering.exceptions import ContextOverflowError
from context_engineering.mock_llm import MockLLM
from context_engineering.tokenizer import count_tokens


class TestMockLLMTokenCount:
    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_ascii_text(self):
        # 8 字符 ≈ 2 token
        assert count_tokens("hello !!") == 2

    def test_chinese_text(self):
        # 中文按字符 / 4 近似，100 中文字符 ≈ 25 token
        text = "这是一段" * 25  # 100 字符
        assert count_tokens(text) == 25


class TestMockLLMBasic:
    def test_generate_short_prompt(self):
        llm = MockLLM(max_context_tokens=1000)
        res = llm.generate("你好")
        assert isinstance(res, str)
        assert len(res) > 0

    def test_generate_overflow_raises(self):
        llm = MockLLM(max_context_tokens=10)  # 40 字符
        long_prompt = "你好" * 50  # 100 字符 ≈ 25 token > 10
        with pytest.raises(ContextOverflowError):
            llm.generate(long_prompt)

    def test_summary_mode(self):
        llm = MockLLM()
        text = (
            "本项目采用了基于 Transformer 架构的深度学习模型，"
            "在自然语言处理任务上取得了显著提升。"
            "模型训练使用了大规模数据集，并通过对比学习增强了泛化能力。"
            "实验表明，在多个基准测试中该模型均优于现有方案，"
            "具备良好的实用价值和推广前景。"
            "下一步计划上线 A/B 实验并逐步替换旧模型。"
        )
        res = llm.summarize(text)
        assert "Mock 摘要" in res

    def test_qa_mode(self):
        llm = MockLLM()
        body = "Python 是一种解释型编程语言，由 Guido van Rossum 于 1991 年发布。"
        res = llm.answer(body, "Python 是谁发明的？")
        assert "Mock 回答" in res

    def test_usage_tracking(self):
        llm = MockLLM()
        llm.generate("你好世界" * 10)
        assert llm.last_usage.prompt_tokens > 0
        assert llm.last_usage.completion_tokens > 0
        assert llm.last_usage.total_tokens > 0

    def test_reset_usage(self):
        llm = MockLLM()
        llm.generate("测试测试测试测试测试测试测试测试测试测试")
        llm.reset_usage()
        assert llm.total_usage.prompt_tokens == 0
        assert llm.total_usage.completion_tokens == 0

    def test_multiple_calls_accumulate(self):
        llm = MockLLM()
        long_enough = "这是一段足够长的测试文本，至少要有十几个字符才能让 token 计数不为零。"
        llm.generate(long_enough)
        llm.generate(long_enough)
        assert llm.total_usage.prompt_tokens > 0
        assert llm.total_usage.prompt_tokens >= llm.last_usage.prompt_tokens


class TestMockLLMOutputTruncation:
    def test_output_truncated_to_max(self):
        llm = MockLLM(max_context_tokens=8000, max_output_tokens=5)
        text = "这是" * 1000  # 2000 字符
        llm.summarize(text)
        assert llm.last_usage.completion_tokens <= 5
