"""简化版 token 计数 —— 用字符数 / 4 近似估算 token 数。

英文约 4 字符 = 1 token，中文约 1.5 字符 = 1 token，
这里统一用 char_count / 4 做近似，便于 demo 展示。
"""


def count_tokens(text: str) -> int:
    """估算 text 的 token 数（非负整数）。"""
    if not text:
        return 0
    return max(0, len(text) // 4)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """将 text 截断到不超过 max_tokens（按字符 / 4 估算）。

    尽量保留文本头部，返回完整字符（不会在中间截断 UTF-8 字符）。
    """
    if max_tokens <= 0:
        return ""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip()
