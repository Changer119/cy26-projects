"""进程内会话历史存储（MVP：内存 dict，不落库）。"""
from __future__ import annotations

import threading

from app.config import get_settings
from app.models import ChatMessage, MessageRole


class SessionStore:
    """线程安全的内存会话存储，key 为 session_id。"""

    def __init__(self, max_turns: int | None = None) -> None:
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._lock = threading.Lock()
        self._max_turns = max_turns or get_settings().session_max_turns

    def get_history(self, session_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def append(self, session_id: str, message: ChatMessage) -> None:
        with self._lock:
            history = self._sessions.setdefault(session_id, [])
            history.append(message)
            # 只保留最近 max_turns 条消息，防止长会话无限占用内存
            overflow = len(history) - self._max_turns
            if overflow > 0:
                del history[:overflow]

    def append_turn(self, session_id: str, user_text: str, assistant_text: str) -> None:
        self.append(session_id, ChatMessage(role=MessageRole.user, content=user_text))
        self.append(
            session_id, ChatMessage(role=MessageRole.assistant, content=assistant_text)
        )


# 进程级单例：FastAPI 应用生命周期内共享同一份会话存储
session_store = SessionStore()
