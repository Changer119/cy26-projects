"""CLI 适配层：给人和脚本用。重点是参数解析与可读输出。"""

from __future__ import annotations

import typer

from weather.core.models import WeatherQuery
from weather.core.service import get_weather

app = typer.Typer(help="天气查询 CLI —— 输入城市与日期，返回天气信息")


@app.command()
def query(
    city: str = typer.Argument(..., help="城市名称，例如：杭州"),
    date: str = typer.Argument(..., help="日期，例如：2026-06-20"),
    as_json: bool = typer.Option(False, "--json", help="以 JSON 输出，供脚本消费"),
) -> None:
    """查询某城市某日期的天气。"""
    result = get_weather(WeatherQuery(city=city, date=date))

    if as_json:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"📍 {result.city}  📅 {result.date}")
    typer.echo(f"   天气：{result.condition}")
    typer.echo(f"   气温：{result.temp_low_c}°C ~ {result.temp_high_c}°C")
    typer.echo(f"   湿度：{result.humidity_percent}%")
    typer.echo(f"   概述：{result.summary}")


if __name__ == "__main__":
    app()
