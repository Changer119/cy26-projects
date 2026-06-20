"""核心数据结构：全部强类型，协议无关。

CLI / MCP / HTTP 三层都复用这里定义的入参与结果结构。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WeatherQuery(BaseModel):
    """天气查询入参。"""

    city: str = Field(..., description="城市名称，例如：杭州")
    date: str = Field(..., description="日期，ISO 格式，例如：2026-06-20")


class WeatherResult(BaseModel):
    """天气查询结果。"""

    city: str = Field(..., description="城市名称")
    date: str = Field(..., description="日期")
    condition: str = Field(..., description="天气状况，例如：多云转晴")
    temp_high_c: int = Field(..., description="最高气温（摄氏度）")
    temp_low_c: int = Field(..., description="最低气温（摄氏度）")
    humidity_percent: int = Field(..., description="相对湿度（百分比）")
    summary: str = Field(..., description="一句话天气概述与生活建议")
