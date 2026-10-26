"""纯 Python 实现的简化版 TF-IDF + 余弦相似度，用于 RAG-lite 方案。

不依赖 numpy，所有向量运算用 Python 列表 + math.sqrt。
中文使用 2-gram 分词（把连续中文字符切成长度为 2 的滑动窗口），
英文按单词（空格/标点分隔）切分。
"""

from __future__ import annotations

import math
from collections import Counter


def _is_cjk(ch: str) -> bool:
    """判断字符是否为中文字符（CJK Unified Ideographs 基本区 + 扩展 A）。"""
    return "\u4e00" <= ch <= "\u9fff"


def tokenize(text: str) -> list[str]:
    """中文 2-gram + 英文按单词切分。

    示例："下一代智能客服" → "下代", "一代", "代智", "智能", "能客", "客服"
    """
    if not text:
        return []

    lower = text.lower()
    result: list[str] = []
    # 先把中文片段和英文片段分开处理
    cjk_buf: list[str] = []
    eng_buf: list[str] = []

    def flush_cjk() -> None:
        if len(cjk_buf) >= 2:
            s = "".join(cjk_buf)
            for i in range(len(s) - 1):
                result.append(s[i : i + 2])
        elif len(cjk_buf) == 1:
            result.append("".join(cjk_buf))
        cjk_buf.clear()

    def flush_eng() -> None:
        if len(eng_buf) >= 2:
            result.append("".join(eng_buf))
        eng_buf.clear()

    for ch in lower:
        if _is_cjk(ch):
            flush_eng()
            cjk_buf.append(ch)
        elif ch.isalnum():
            flush_cjk()
            eng_buf.append(ch)
        else:
            # 标点/空白：两个 buffer 都 flush
            flush_cjk()
            flush_eng()

    flush_cjk()
    flush_eng()
    return result


def build_idf(documents: list[list[str]]) -> dict[str, float]:
    """计算 IDF：log((N+1)/(df+1)) + 1。"""
    n = len(documents)
    df: Counter[str] = Counter()
    for tokens in documents:
        df.update(set(tokens))
    return {word: math.log((n + 1) / (count + 1)) + 1.0 for word, count in df.items()}


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """计算 TF-IDF 向量（稀疏 dict）。"""
    if not tokens:
        return {}
    tf = Counter(tokens)
    total = max(len(tokens), 1)
    return {
        word: (count / total) * idf.get(word, 0.0)
        for word, count in tf.items()
        if word in idf
    }


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """计算两个稀疏向量的余弦相似度。"""
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class TfidfIndex:
    """对一组文档构建 TF-IDF 索引，支持 query 检索 top-k。"""

    def __init__(self, documents: list[str]) -> None:
        self._documents = documents
        self._tokenized = [tokenize(d) for d in documents]
        self._idf = build_idf(self._tokenized)
        self._vectors = [tfidf_vector(tokens, self._idf) for tokens in self._tokenized]

    def search(self, query: str, top_k: int = 3) -> list[tuple[int, float]]:
        """返回 [(doc_index, score), ...] 按分数降序。"""
        q_vec = tfidf_vector(tokenize(query), self._idf)
        scored = [(i, cosine(q_vec, v)) for i, v in enumerate(self._vectors)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
