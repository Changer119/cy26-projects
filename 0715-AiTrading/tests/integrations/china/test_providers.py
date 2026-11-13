import json
from datetime import date
from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr

from ai_trading.integrations.china.akshare import AkshareEodProvider
from ai_trading.integrations.china.tushare import TushareEodProvider
from ai_trading.integrations.market_data import (
    MarketDataProviderError,
    MarketDataRangeRequest,
    MarketDataRequest,
)

REQUEST = MarketDataRequest(
    symbol="600519.SH", provider_symbol="ignored", trade_date=date(2026, 10, 28), currency="CNY"
)


def test_tushare_maps_symbol_and_fractional_lots_to_shares() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["params"]["ts_code"] == "600519.SH"
        assert body["api_name"] == "daily"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "fields": body["fields"].split(","),
                    "items": [["600519.SH", "20261028", 10, 11, 9, 10, 123.45]],
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        bar = TushareEodProvider(SecretStr("private"), client).fetch(REQUEST)
    assert bar.volume == 12345
    assert bar.close == Decimal(10)


@pytest.mark.parametrize("code", [-2001, -2002, 40203])
def test_tushare_api_errors_are_sanitized(code: int) -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"code": code, "msg": "secret", "data": None},
                )
            )
        ) as client,
        pytest.raises(MarketDataProviderError) as error,
    ):
        TushareEodProvider(SecretStr("secret"), client).fetch(REQUEST)
    assert "secret" not in str(error.value)


def test_missing_token_makes_no_network_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("未配置凭据不应请求网络")

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(MarketDataProviderError, match="TUSHARE_TOKEN"),
    ):
        TushareEodProvider(None, client).fetch(REQUEST)


def test_tushare_range_adjusts_prices_but_preserves_volume() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        items = (
            [
                ["600519.SH", "20261027", 10, 11, 9, 10, 100],
                ["600519.SH", "20261028", 5, 6, 4, 5, 200],
            ]
            if body["api_name"] == "daily"
            else [["600519.SH", "20261027", 1], ["600519.SH", "20261028", 2]]
        )
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "fields": body["fields"].split(","),
                    "items": items,
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        bars = TushareEodProvider(SecretStr("token"), client).fetch_range(
            MarketDataRangeRequest(
                symbol=REQUEST.symbol,
                provider_symbol="ignored",
                start_date=date(2026, 10, 27),
                end_date=REQUEST.trade_date,
                currency="CNY",
            )
        )
    assert bars[0].close == bars[1].close == Decimal(5)
    assert bars[0].volume == 10000


def test_akshare_converts_frame_at_typed_boundary() -> None:
    import pandas as pd

    class Loader:
        def load(self, symbol: str, start: str, end: str, adjusted: bool) -> pd.DataFrame:
            assert symbol == "600519"
            assert not adjusted
            return pd.DataFrame(
                [[date(2026, 10, 28), 10, 11, 9, 10, 123]],
                columns=["日期", "开盘", "最高", "最低", "收盘", "成交量"],
            )

    assert AkshareEodProvider(Loader()).fetch(REQUEST).volume == 12300


def test_missing_adjustment_permission_never_returns_raw_history() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["api_name"] == "adj_factor":
            return httpx.Response(200, json={"code": -2002, "data": None})
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "fields": body["fields"].split(","),
                    "items": [["600519.SH", "20261028", 10, 11, 9, 10, 100]],
                },
            },
        )

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(MarketDataProviderError, match="权限"),
    ):
        TushareEodProvider(SecretStr("token"), client).fetch_range(
            MarketDataRangeRequest(
                symbol=REQUEST.symbol,
                provider_symbol="ignored",
                start_date=REQUEST.trade_date,
                end_date=REQUEST.trade_date,
                currency="CNY",
            )
        )


def test_tushare_reports_permission_denial_without_echoing_message() -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"code": 40203, "msg": "secret 没有访问该接口的权限", "data": None},
                )
            )
        ) as client,
        pytest.raises(MarketDataProviderError, match="接口权限不足") as error,
    ):
        TushareEodProvider(SecretStr("secret"), client).fetch(REQUEST)
    assert "secret" not in str(error.value)
    assert "40203" in str(error.value)
