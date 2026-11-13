"""两源共用的证券代码和数值边界。"""

import re
from datetime import date, datetime
from decimal import Decimal
from numbers import Real

from ai_trading.integrations.market_data import (
    MarketDataProviderError,
    MarketDataProviderErrorKind,
)


def stock_code(symbol: str, currency: str) -> tuple[str, str]:
    match = re.fullmatch(r"(\d{6})\.(SH|SS|SZ|SSE|SZSE)", symbol.upper())
    if currency != "CNY" or match is None:
        raise MarketDataProviderError(
            MarketDataProviderErrorKind.CONFIGURATION, "当前双源入口仅支持沪深 A 股日线"
        )
    numeric, suffix = match.groups()
    return numeric, f"{numeric}.{'SZ' if suffix in ('SZ', 'SZSE') else 'SH'}"


def number(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, Real, Decimal)):
        raise ValueError("行情数值类型无效")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("行情包含非有限数值")
    return result


def shares(value: object) -> int:
    result = number(value) * 100
    if result < 0 or result != result.to_integral_value():
        raise ValueError("成交量不能转换为整数股数")
    return int(result)


def trading_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError("交易日期格式无效")
