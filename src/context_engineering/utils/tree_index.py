"""目录树索引构建与查询，用于结构化索引方案。

从嵌套 dict 构建索引树，按文件路径中的目录层级和文件名关键词快速定位。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class FileNode:
    path: str
    name: str
    parent_path: str
    content: str
    size: int  # 字符数
    keywords: list[str] = field(default_factory=list)

    def match_score(self, query: str) -> int:
        """把 query 拆成关键词后分别匹配：路径里权重 ×3，文件名 ×5，关键词 ×4，内容头部 ×1。"""
        score = 0
        # 简单拆词：标点切分 + 2-gram（中文）
        lower_q = query.lower().strip()
        terms = [t for t in re.split(r"[\s，,。.；;：:！!？?、\(\)\[\]{}\"'<>]+", lower_q) if t]

        def _score_term(term: str) -> None:
            if not term:
                return
            tl = term.lower()
            score_val = 0
            if tl in self.path.lower():
                score_val += 3
            if tl in self.name.lower():
                score_val += 5
            for kw in self.keywords:
                if tl in kw.lower() or kw.lower() in tl:
                    score_val += 4
            head = self.content[:200].lower()
            score_val += head.count(tl)
            score_val += self.parent_path.lower().count(tl) * 2
            if score_val > 0:
                nonlocal score
                score += score_val

        for term in terms:
            _score_term(term)
        return score


def _extract_name_from_path(path: str) -> str:
    parts = path.rstrip("/").split("/")
    return parts[-1] if parts else path


def build_tree_index(tree: dict) -> list[FileNode]:
    """从嵌套 dict（路径前缀 -> 内容）构建文件节点列表。"""
    nodes: list[FileNode] = []
    flat = _flatten(tree)
    for path, content in flat.items():
        name = _extract_name_from_path(path)
        parent = "/".join(path.rstrip("/").split("/")[:-1]) or ""
        keywords = _extract_keywords(content)
        nodes.append(
            FileNode(
                path=path,
                name=name,
                parent_path=parent,
                content=content,
                size=len(content),
                keywords=keywords,
            )
        )
    return nodes


def _flatten(tree: dict, prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in tree.items():
        full = prefix + key
        if isinstance(value, dict):
            result.update(_flatten(value, full))
        else:
            result[full] = value
    return result


def _extract_keywords(content: str) -> list[str]:
    """从文件内容中提取若干关键词（简单规则：取前若干 import/def/class）。"""
    keywords: list[str] = []
    for line in content.splitlines()[:10]:
        stripped = line.strip()
        if stripped.startswith("class "):
            keywords.append(stripped[6:].split("(")[0].split(":")[0])
        elif stripped.startswith("def "):
            keywords.append(stripped[4:].split("(")[0])
        elif stripped.startswith("from ") and " import" in stripped:
            keywords.append(stripped.split(" import ")[0][5:].split(".")[-1])
        elif stripped.startswith("import "):
            for m in stripped[7:].split(","):
                keywords.append(m.strip().split(" as ")[-1].split(".")[-1])
    # 最多保留 5 个关键词
    return keywords[:5]


def search_nodes(nodes: list[FileNode], query: str, top_k: int = 5) -> list[FileNode]:
    """按 query 对所有 FileNode 评分，返回 top-k。"""
    scored = [(n, n.match_score(query)) for n in nodes]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [n for n, s in scored if s > 0][:top_k]
