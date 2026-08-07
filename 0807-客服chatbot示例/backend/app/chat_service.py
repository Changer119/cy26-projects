"""对话业务编排：检索知识库 -> 拼接上下文 -> 调用 DeepSeek -> 更新会话历史。

拆成独立模块（而不是塞进 API 路由函数）是为了不依赖真实 HTTP/DeepSeek 也能
做单元测试：注入 mock 的 retriever / llm_client 即可。
"""
from __future__ import annotations

from app.config import get_settings
from app.llm.deepseek_client import DeepSeekCallError, DeepSeekClient, DeepSeekConfigError
from app.logger import get_logger
from app.models import ChatRequest, ChatResponse
from app.rag.retriever import KnowledgeRetriever
from app.session.store import SessionStore, session_store

logger = get_logger(__name__)


class ChatServiceError(RuntimeError):
    """对话处理失败，携带对用户友好的错误信息。"""


class ChatService:
    def __init__(
        self,
        retriever: KnowledgeRetriever,
        llm_client: DeepSeekClient | None = None,
        store: SessionStore | None = None,
    ) -> None:
        self._retriever = retriever
        self._llm_client = llm_client or DeepSeekClient()
        self._store = store or session_store
        self._top_k = get_settings().rag_top_k

    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        history = self._store.get_history(request.session_id)

        retrieved = self._retriever.search(request.message, top_k=self._top_k)
        sources = _dedup_preserve_order([chunk.source for chunk in retrieved])

        try:
            reply = self._llm_client.chat(
                history=history,
                user_message=request.message,
                knowledge_snippets=[chunk.text for chunk in retrieved],
            )
        except DeepSeekConfigError as exc:
            logger.warning("DeepSeek 未配置: %s", exc)
            raise ChatServiceError(str(exc)) from exc
        except DeepSeekCallError as exc:
            logger.error("DeepSeek 调用失败: %s", exc)
            raise ChatServiceError(str(exc)) from exc

        self._store.append_turn(
            session_id=request.session_id,
            user_text=request.message,
            assistant_text=reply,
        )

        return ChatResponse(
            session_id=request.session_id,
            reply=reply,
            sources=sources,
        )


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
