"""本地轻量检索：BM25（rank-bm25）+ jieba 中文分词。

Demo 项目不接外部 embedding API（DeepSeek 不提供 embedding 接口），
用关键词检索即可满足内部客服知识库的召回需求。
"""
from __future__ import annotations

from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi

from app.models import RetrievedChunk
from app.rag.loader import KnowledgeChunk, load_documents

# 中文疑问/功能虚词：语料库里出现次数少导致 IDF 偏高，若不过滤会在 BM25
# 打分时反客为主，盖过真正表意的关键词（如"报销""材料"），拉偏检索结果。
_STOPWORDS = {
    "的", "了", "吗", "呢", "吧", "啊", "是", "在", "有", "和", "与", "及",
    "哪些", "哪个", "什么", "怎么", "如何", "为什么", "需要", "要", "请问",
    "请", "我", "你", "它", "这", "那", "都", "也", "就", "还", "又",
}


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in jieba.lcut(text)
        if token.strip() and token not in _STOPWORDS and token.isalnum()
    ]


class KnowledgeRetriever:
    """基于 BM25 的知识库检索器，构造时一次性加载并建立索引。"""

    def __init__(self, data_dir: Path) -> None:
        self._chunks: list[KnowledgeChunk] = load_documents(data_dir)
        self._corpus_tokens = [_tokenize(chunk.text) for chunk in self._chunks]
        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None

    @property
    def document_count(self) -> int:
        return len(self._chunks)

    def search(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """返回与 query 最相关的 top_k 个片段，按分数降序，过滤掉零分结果。"""
        if self._bm25 is None:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        ranked_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]

        results: list[RetrievedChunk] = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            chunk = self._chunks[idx]
            results.append(
                RetrievedChunk(source=chunk.source, text=chunk.text, score=score)
            )
        return results
