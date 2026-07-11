"""FastAPI 服务：提供大屏页面与台风数据 API。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR
from app.fetcher import cache
from app.logger import get_logger
from app.models import DashboardData

logger = get_logger("server")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("服务启动，开始后台定时刷新任务（每 60 秒）")
    task = asyncio.create_task(cache.run_forever())
    yield
    task.cancel()
    logger.info("服务停止")


app = FastAPI(title="台风巴威实时监测大屏", lifespan=lifespan)


@app.get("/api/typhoon", response_model=DashboardData)
async def get_typhoon() -> DashboardData:
    if cache.data is None:
        await cache.refresh()
    if cache.data is None:
        raise HTTPException(status_code=503, detail="台风数据暂不可用，请稍后重试")
    return cache.data


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "data_ready": "1" if cache.data else "0"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
