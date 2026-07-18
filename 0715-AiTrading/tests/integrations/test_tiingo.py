from datetime import date
from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr

from ai_trading.integrations.market_data import (
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    MarketDataRangeRequest,
    MarketDataRequest,
)
from ai_trading.integrations.tiingo import TiingoEodProvider


def make_request() -> MarketDataRequest:
    return MarketDataRequest(
        symbol="603005.SH",
        provider_symbol="603005",
        trade_date=date(2026, 7, 15),
        currency="CNY",
    )


def make_range_request() -> MarketDataRangeRequest:
    return MarketDataRangeRequest(
        symbol="603005.SH",
        provider_symbol="603005",
        start_date=date(2026, 7, 14),
        end_date=date(2026, 7, 15),
        currency="CNY",
    )


def test_missing_token_fails_closed_without_http_request() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = TiingoEodProvider(api_token=None, client=client)

    with pytest.raises(MarketDataProviderError) as error:
        provider.fetch(make_request())

    assert error.value.kind is MarketDataProviderErrorKind.CONFIGURATION
    assert call_count == 0


def test_fetch_parses_exact_trade_date_into_market_bar() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Token token-value"
        assert request.url.params["startDate"] == "2026-07-15"
        assert request.url.params["endDate"] == "2026-07-15"
        return httpx.Response(
            200,
            content=(
                b'[{"date":"2026-07-15T00:00:00.000Z","open":9.8,'
                b'"high":10.2,"low":9.7,"close":10.0,"volume":1000000}]'
            ),
            headers={"Content-Type": "application/json"},
        )

    provider = TiingoEodProvider(
        api_token=SecretStr("token-value"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    bar = provider.fetch(make_request())

    assert bar.symbol == "603005.SH"
    assert bar.trade_date == date(2026, 7, 15)
    assert bar.close == Decimal("10.0")
    assert bar.source == "tiingo"


def test_authentication_failure_is_classified_without_leaking_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, content=b'{"detail":"invalid token"}')

    provider = TiingoEodProvider(
        api_token=SecretStr("top-secret"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(MarketDataProviderError) as error:
        provider.fetch(make_request())

    assert error.value.kind is MarketDataProviderErrorKind.AUTHENTICATION
    assert "top-secret" not in str(error.value)
    assert "top-secret" not in repr(provider)


def test_missing_trade_date_is_not_silently_replaced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"[]")

    provider = TiingoEodProvider(
        api_token=SecretStr("token-value"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(MarketDataProviderError) as error:
        provider.fetch(make_request())

    assert error.value.kind is MarketDataProviderErrorKind.NOT_FOUND


def test_fetch_range_uses_one_request_and_sorts_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["startDate"] == "2026-07-14"
        assert request.url.params["endDate"] == "2026-07-15"
        return httpx.Response(
            200,
            json=[
                {
                    "date": "2026-07-15T00:00:00.000Z",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10.5,
                    "volume": 2000,
                    "adjOpen": 9.8,
                    "adjHigh": 10.8,
                    "adjLow": 8.8,
                    "adjClose": 10.3,
                    "adjVolume": 2100,
                },
                {
                    "date": "2026-07-14T00:00:00.000Z",
                    "open": 9,
                    "high": 10,
                    "low": 8,
                    "close": 9.5,
                    "volume": 1000,
                    "adjOpen": 8.8,
                    "adjHigh": 9.8,
                    "adjLow": 7.8,
                    "adjClose": 9.3,
                    "adjVolume": 1100,
                },
            ],
        )

    provider = TiingoEodProvider(
        SecretStr("token-value"),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    bars = provider.fetch_range(make_range_request())

    assert tuple(item.trade_date for item in bars) == (date(2026, 7, 14), date(2026, 7, 15))
    assert all(item.source == "tiingo" for item in bars)
    assert bars[0].close == Decimal("9.3")
    assert bars[0].volume == 1100


def test_fetch_range_rejects_duplicate_dates() -> None:
    payload = [
        {
            "date": "2026-07-14T00:00:00.000Z",
            "open": 9,
            "high": 10,
            "low": 8,
            "close": 9.5,
            "volume": 1000,
        }
    ]
    provider = TiingoEodProvider(
        SecretStr("token-value"),
        httpx.Client(
            transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=payload * 2))
        ),
    )

    with pytest.raises(MarketDataProviderError) as error:
        provider.fetch_range(make_range_request())

    assert error.value.kind is MarketDataProviderErrorKind.INVALID_RESPONSE
