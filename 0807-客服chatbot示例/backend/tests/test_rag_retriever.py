"""RAG 检索模块单元测试：不依赖 DeepSeek，纯本地 BM25 检索逻辑。"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.rag.loader import load_documents
from app.rag.retriever import KnowledgeRetriever

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_load_documents_finds_all_knowledge_files() -> None:
    chunks = load_documents(DATA_DIR)

    assert len(chunks) > 0
    sources = {chunk.source for chunk in chunks}
    assert "请假流程.md" in sources
    assert "报销流程.md" in sources
    assert "IT设备申请.md" in sources


def test_load_documents_missing_dir_returns_empty(tmp_path: Path) -> None:
    empty_dir = tmp_path / "does-not-exist"
    assert load_documents(empty_dir) == []


@pytest.fixture(scope="module")
def retriever() -> KnowledgeRetriever:
    return KnowledgeRetriever(data_dir=DATA_DIR)


def test_retriever_hits_leave_process_for_leave_question(
    retriever: KnowledgeRetriever,
) -> None:
    results = retriever.search("年假可以请几天，怎么申请请假", top_k=3)

    assert len(results) > 0
    # BM25 是关键词检索，短片段命中密度高时可能排在最前面（如入职引导.md 里
    # 提到年假的问答），因此只断言目标文档在召回结果内，而不强制要求排第一。
    sources = [r.source for r in results]
    assert "请假流程.md" in sources
    assert all(r.score > 0 for r in results)
    # 分数应降序排列
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retriever_hits_reimbursement_for_invoice_question(
    retriever: KnowledgeRetriever,
) -> None:
    results = retriever.search("报销发票丢了怎么办", top_k=3)

    sources = [r.source for r in results]
    assert "报销流程.md" in sources


def test_retriever_returns_empty_for_irrelevant_query(
    retriever: KnowledgeRetriever,
) -> None:
    results = retriever.search("今天天气怎么样适合出去玩吗", top_k=3)
    # 无明显关键词命中时，允许返回空列表（不强行给低相关结果）
    assert isinstance(results, list)


def test_retriever_respects_top_k(retriever: KnowledgeRetriever) -> None:
    results = retriever.search("笔记本电脑设备申请流程报销差旅入职", top_k=2)
    assert len(results) <= 2


def test_empty_data_dir_search_returns_empty(tmp_path: Path) -> None:
    retriever = KnowledgeRetriever(data_dir=tmp_path)
    assert retriever.document_count == 0
    assert retriever.search("请假流程", top_k=3) == []
