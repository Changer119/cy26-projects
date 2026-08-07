"""FastAPI 应用工厂。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.logger import get_logger, setup_logging

logger = get_logger(__name__)


def create_app() -> FastAPI:
    setup_logging()
    logger.info("正在初始化客服 chatbot 后端服务")

    app = FastAPI(title="内部客服 Chatbot 后端", version="0.1.0")

    # Demo 项目内网使用，前端跑在本地 Next.js dev server，放开跨域
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(chat_router)

    return app
