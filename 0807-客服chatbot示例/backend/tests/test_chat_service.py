"""ChatService 编排逻辑单元测试：mock 掉 DeepSeekClient，不发真实网络请求。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.chat_service import ChatService, ChatServiceError
from app.llm.deepseek_client import DeepSeekCallError, DeepSeekConfigError
from app.models import ChatRequest, RetrievedChunk
from app.session.store import SessionStore


def _make_retriever(chunks: list[RetrievedChunk]) -> MagicMock:
    retriever = MagicMock()
    retriever.search.return_value = chunks
    return retriever


def test_handle_chat_returns_reply_and_sources() -> None:
    chunks = [
        RetrievedChunk(source="请假流程.md", text="年假规则...", score=5.0),
        RetrievedChunk(source="请假流程.md", text="病假规则...", score=3.0),
    ]
    retriever = _make_retriever(chunks)
    llm_client = MagicMock()
    llm_client.chat.return_value = "年假需要提前在 OA 系统申请。"

    service = ChatService(retriever=retriever, llm_client=llm_client, store=SessionStore())
    response = service.handle_chat(ChatRequest(session_id="s1", message="年假怎么请"))

    assert response.session_id == "s1"
    assert response.reply == "年假需要提前在 OA 系统申请。"
    # 同一来源去重后只出现一次
    assert response.sources == ["请假流程.md"]


def test_handle_chat_persists_multi_turn_history() -> None:
    retriever = _make_retriever([])
    llm_client = MagicMock()
    llm_client.chat.side_effect = ["第一轮回复", "第二轮回复"]
    store = SessionStore()

    service = ChatService(retriever=retriever, llm_client=llm_client, store=store)
    service.handle_chat(ChatRequest(session_id="s1", message="第一个问题"))
    service.handle_chat(ChatRequest(session_id="s1", message="第二个问题"))

    history = store.get_history("s1")
    assert len(history) == 4  # 2 轮 user+assistant
    # 第二次调用时，历史里应包含第一轮的问答
    second_call_history = llm_client.chat.call_args_list[1].kwargs["history"]
    assert len(second_call_history) == 2


def test_handle_chat_raises_service_error_when_deepseek_not_configured() -> None:
    retriever = _make_retriever([])
    llm_client = MagicMock()
    llm_client.chat.side_effect = DeepSeekConfigError("缺少 API key")

    service = ChatService(retriever=retriever, llm_client=llm_client, store=SessionStore())

    with pytest.raises(ChatServiceError):
        service.handle_chat(ChatRequest(session_id="s1", message="报销怎么弄"))


def test_handle_chat_raises_service_error_on_api_failure() -> None:
    retriever = _make_retriever([])
    llm_client = MagicMock()
    llm_client.chat.side_effect = DeepSeekCallError("网络超时")

    service = ChatService(retriever=retriever, llm_client=llm_client, store=SessionStore())

    with pytest.raises(ChatServiceError):
        service.handle_chat(ChatRequest(session_id="s1", message="报销怎么弄"))
