"""核心业务逻辑：输入城市与日期，调用大模型生成结构化天气结果。

这是协议无关的纯函数，是整个系统的「单一真相源」——
CLI / MCP / HTTP 三层都只是把各自协议的输入翻译成对 get_weather() 的调用。
改业务规则，只动这里。

大模型统一用 DeepSeek（OpenAI 兼容格式），三个配置全部从环境变量获取：
DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL。
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

from .logger import get_logger
from .models import WeatherQuery, WeatherResult

load_dotenv()

logger = get_logger("weather.core")

_SYSTEM = (
    "你是一个天气信息助手。根据用户提供的城市与日期，给出该地点该日期合理的天气信息。"
    "所有文本字段都用简体中文填写。"
    "必须只返回一个 JSON 对象，不要包含任何额外文字，字段如下：\n"
    "city（字符串）、date（字符串）、condition（字符串，如“多云转晴”）、"
    "temp_high_c（整数）、temp_low_c（整数）、humidity_percent（整数）、"
    "summary（字符串，一句话天气概述与生活建议）。"
)


def _client() -> OpenAI:
    """构造 OpenAI 兼容客户端，指向 DeepSeek。"""
    return OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )


def get_weather(query: WeatherQuery) -> WeatherResult:
    """根据城市与日期返回结构化天气信息。"""
    logger.info("查询天气: city=%s date=%s", query.city, query.date)

    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    prompt = f"请给出 {query.city} 在 {query.date} 的天气信息，并以 JSON 返回。"

    completion = _client().chat.completions.create(
        model=model,
        max_tokens=1024,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )

    content = completion.choices[0].message.content or ""
    result = WeatherResult.model_validate_json(content)

    # 以入参为准，避免模型改写城市/日期
    result.city = query.city
    result.date = query.date
    logger.info("查询成功: %s", result.summary)
    return result
