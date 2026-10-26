"""结构化索引方案测试。"""

from context_engineering.data.codebase_mock import CODEBASE_TREE, flatten_tree
from context_engineering.mock_llm import MockLLM
from context_engineering.structured_index import StructuredIndexQA


def test_structured_index_builds():
    llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
    qa = StructuredIndexQA(llm, CODEBASE_TREE)

    flat = flatten_tree(CODEBASE_TREE)
    assert qa.total_files == len(flat)
    assert qa.nodes


def test_structured_index_loads_fewer_files_than_all():
    llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
    qa = StructuredIndexQA(llm, CODEBASE_TREE)

    _, stats, _ = qa.query("认证")
    # 只加载相关文件（认证相关的 auth_service.py, deps.py 等），而非全量
    assert stats["matched_files"] < stats["total_files"]
    assert stats["loaded_ratio"] < 0.5


def test_structured_index_answer_has_content():
    llm = MockLLM(max_context_tokens=2000, max_output_tokens=500)
    qa = StructuredIndexQA(llm, CODEBASE_TREE)

    ans, _, paths = qa.query("认证服务 authenticate")
    assert ans
    # 至少有一个文件被加载了
    assert len(paths) >= 1
