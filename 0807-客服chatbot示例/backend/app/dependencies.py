"""FastAPI 依赖注入：进程级单例（检索器构建一次索引即可复用）。"""
from __future__ import annotations

from functools import lru_cache

from app.chat_service import ChatService
from app.config import get_settings
from app.rag.retriever import KnowledgeRetriever


@lru_cache
def get_retriever() -> KnowledgeRetriever:
    return KnowledgeRetriever(data_dir=get_settings().data_dir)


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService(retriever=get_retriever())
