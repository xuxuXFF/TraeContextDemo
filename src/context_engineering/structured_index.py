"""方案四：结构化索引（Structured Index）代码库问答。

问题背景：
面对大型代码库，把所有文件拼起来送 LLM 是不现实的。
结构化索引先按文件路径和内容特征建立索引，查询时只加载最相关的少数文件，
避免了全量加载。

方案优势：
- 路径信息天然包含目录层级语义（api/routes.py → API 路由）
- 能按需只加载相关子树，token 使用量远小于全量
"""

from __future__ import annotations

from context_engineering.mock_llm import MockLLM
from context_engineering.tokenizer import count_tokens
from context_engineering.utils.tree_index import (
    FileNode,
    build_tree_index,
    search_nodes,
)


class StructuredIndexQA:
    """结构化索引问答器。"""

    def __init__(
        self,
        llm: MockLLM,
        codebase_tree: dict,
        max_load_tokens: int | None = None,
    ) -> None:
        self.llm = llm
        self.nodes: list[FileNode] = build_tree_index(codebase_tree)
        self.total_files = len(self.nodes)
        self.total_chars = sum(n.size for n in self.nodes)
        if max_load_tokens is None:
            max_load_tokens = int(llm.max_context_tokens * 0.5)
        self.max_load_tokens = max_load_tokens

    def query(self, question: str, top_k: int = 5) -> tuple[str, dict, list[str]]:
        self.llm.reset_usage()

        matched = search_nodes(self.nodes, question, top_k=top_k)

        # 逐个加入，直到 token 上限
        loaded: list[str] = []
        loaded_paths: list[str] = []
        loaded_tokens = 0
        for node in matched:
            t = count_tokens(node.content)
            if loaded_tokens + t > self.max_load_tokens and loaded:
                break
            loaded.append(f"=== {node.path} ===\n{node.content}")
            loaded_paths.append(node.path)
            loaded_tokens += t

        context = "\n\n".join(loaded) if loaded else ""

        if context:
            answer = self.llm.answer(context, question)
        else:
            answer = self.llm.generate("（没有找到相关文件）", mode="qa")

        stats = {
            "total_files": self.total_files,
            "total_chars": self.total_chars,
            "matched_files": len(loaded_paths),
            "loaded_paths": loaded_paths,
            "loaded_token_count": loaded_tokens,
            "loaded_ratio": round(len(loaded_paths) / max(self.total_files, 1), 3),
            "llm_prompt_tokens": self.llm.total_usage.prompt_tokens,
        }
        return answer, stats, loaded_paths
