"""HTTP 适配层：给程序/服务集成用。重点是网络协议与契约。"""

from __future__ import annotations

from fastapi import FastAPI

from weather.core.models import WeatherQuery, WeatherResult
from weather.core.service import get_weather

app = FastAPI(title="天气查询 API", description="城市+日期 → 天气信息")


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok"}


@app.post("/weather", response_model=WeatherResult)
def weather(query: WeatherQuery) -> WeatherResult:
    """根据城市与日期返回天气信息。"""
    return get_weather(query)
