"""自定义异常类型。"""


class ContextOverflowError(Exception):
    """输入 prompt 的 token 数超过了模型上下文窗口限制。"""


class TokenLimitExceededError(Exception):
    """输出 token 数超过了模型 max_output_tokens 限制。"""


class LiveLLMError(Exception):
    """真实 LLM 调用失败：缺 API Key、网络错误、HTTP 错误或响应解析失败。"""
