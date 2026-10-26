"""方案三：向量检索（RAG-lite）问答。

问题背景：
面对超长文档，不能把全文塞进 prompt，但模型需要回答关于文档中特定片段的问题。
RAG-lite 把长文档切成 chunks，用简化版 TF-IDF + 余弦相似度检索最相关的几个 chunks，
送入 MockLLM 回答。相比直接切窗口处理，检索只取相关片段，节省 token。
"""

from __future__ import annotations

from context_engineering.mock_llm import MockLLM
from context_engineering.tokenizer import count_tokens
from context_engineering.utils.tfidf import TfidfIndex


def chunk_by_tokens(text: str, chunk_max_tokens: int, overlap_chars: int = 60) -> list[str]:
    """按 token 限制切 chunk。

    与 sliding_window 里的 chunk_text 实现类似，独立实现避免循环依赖。
    """
    if count_tokens(text) <= chunk_max_tokens:
        return [text]

    max_chars = chunk_max_tokens * 4
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            cutoff = max(start + max_chars - 50, start + max_chars // 2)
            for sep in ["\n\n", "\n", "。", ".", "！", "!", "？", "?"]:
                pos = text.rfind(sep, cutoff, end)
                if pos > 0:
                    end = pos + len(sep)
                    break
        chunks.append(text[start:end].strip())
        next_start = end - overlap_chars
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks


class RagLite:
    """轻量 RAG 问答器。"""

    def __init__(
        self,
        llm: MockLLM,
        document: str,
        chunk_max_tokens: int | None = None,
        top_k: int = 3,
    ) -> None:
        self.llm = llm
        if chunk_max_tokens is None:
            chunk_max_tokens = int(llm.max_context_tokens * 0.3)
        self.top_k = top_k
        self.chunks = chunk_by_tokens(document, chunk_max_tokens)
        self.index = TfidfIndex(self.chunks)

    def query(self, question: str) -> tuple[str, dict, list[int]]:
        """检索 + 问答。返回 (回答, 统计信息, 命中的 chunk 索引列表)。"""
        self.llm.reset_usage()

        hits = self.index.search(question, top_k=self.top_k)
        # 只取 score > 0 的索引
        hit_indices = [idx for idx, score in hits if score > 0]

        context_chunks = [self.chunks[i] for i in hit_indices]
        context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else ""

        # 如果检索到的上下文也超限，只取 top-1
        while context_text and count_tokens(context_text) > self.llm.max_context_tokens * 0.6:
            hit_indices = hit_indices[: max(1, len(hit_indices) // 2)]
            context_chunks = [self.chunks[i] for i in hit_indices]
            context_text = "\n\n---\n\n".join(context_chunks)

        if context_text:
            answer = self.llm.answer(context_text, question)
        else:
            # 没检索到相关内容，用第一个 chunk 兜底
            fallback = self.chunks[0] if self.chunks else "（无可用文档）"
            answer = self.llm.answer(fallback, question)

        stats = {
            "num_chunks": len(self.chunks),
            "hit_indices": hit_indices,
            "hit_token_count": sum(count_tokens(c) for c in context_chunks),
            "context_ratio": round(
                sum(count_tokens(c) for c in context_chunks)
                / max(count_tokens("\n".join(self.chunks)), 1),
                3,
            ),
            "llm_prompt_tokens": self.llm.total_usage.prompt_tokens,
        }
        return answer, stats, hit_indices
