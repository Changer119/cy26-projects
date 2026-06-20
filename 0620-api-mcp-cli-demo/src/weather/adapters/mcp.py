"""MCP 适配层：给 AI / Agent 用。重点是工具的「自描述」——

模型看不到实现，只能靠 description 和参数说明来决定要不要调、怎么调。
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from weather.core.models import WeatherQuery, WeatherResult
from weather.core.service import get_weather

mcp = FastMCP("weather")


@mcp.tool()
def get_city_weather(city: str, date: str) -> WeatherResult:
    """查询指定城市在指定日期的天气信息。

    当用户询问某城市某一天的天气、气温、湿度或穿衣/出行建议时使用本工具。

    Args:
        city: 城市名称，例如「杭州」「北京」。
        date: 日期，ISO 格式，例如「2026-06-20」。
    """
    return get_weather(WeatherQuery(city=city, date=date))


if __name__ == "__main__":
    mcp.run()
