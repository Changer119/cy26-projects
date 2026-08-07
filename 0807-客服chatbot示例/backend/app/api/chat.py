"""POST /api/chat"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.chat_service import ChatService, ChatServiceError
from app.dependencies import get_chat_service
from app.logger import get_logger
from app.models import ChatRequest, ChatResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/api/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="message 不能为空")

    try:
        return service.handle_chat(request)
    except ChatServiceError as exc:
        # DeepSeek 未配置或调用失败：返回清晰的 502，而不是让进程崩溃
        logger.error("对话处理失败 session_id=%s: %s", request.session_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
