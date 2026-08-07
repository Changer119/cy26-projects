"""全局强类型数据模型（Pydantic）。

包含对外接口契约模型，以及内部模块间传递数据用的强类型模型。
接口契约模型（ChatRequest / ChatResponse / HealthResponse）已与前端 Agent
锁定，字段不可变更。
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------- 对外接口契约（锁死，勿改字段） ----------


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    sources: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"


# ---------- 内部强类型模型 ----------


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatMessage(BaseModel):
    """会话历史中的一条消息。"""

    role: MessageRole
    content: str


class RetrievedChunk(BaseModel):
    """RAG 检索命中的一个知识片段。"""

    source: str
    text: str
    score: float
