from datetime import date
from decimal import Decimal

from ai_trading.integrations.market_data import (
    MarketBar,
    MarketDataQualityGate,
    MarketDataStatus,
)


def make_bar(
    source: str,
    close: str = "10.00",
    symbol: str = "603005.SH",
    trade_date: date = date(2026, 7, 15),
    currency: str = "CNY",
    *,
    open_price: str = "9.80",
    high: str = "10.20",
    low: str = "9.70",
    volume: int = 1_000_000,
) -> MarketBar:
    return MarketBar(
        symbol=symbol,
        trade_date=trade_date,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=volume,
        currency=currency,
        source=source,
    )


def test_two_consistent_sources_are_accepted() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary"),
        make_bar("secondary", "10.03"),
    )

    assert result.status is MarketDataStatus.VALID
    assert result.canonical is not None
    assert result.canonical.source == "primary"


def test_valid_high_precision_prices_are_normalized_to_six_decimals() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar(
            "primary",
            close="84.69000244140625",
            open_price="76.69999694824219",
            high="84.69000244140625",
            low="69.29000091552734",
        ),
        make_bar(
            "secondary",
            close="84.69",
            open_price="76.70",
            high="84.69",
            low="69.29",
        ),
    )

    assert result.status is MarketDataStatus.VALID
    assert result.canonical is not None
    assert result.canonical.open == Decimal("76.699997")
    assert result.canonical.high == Decimal("84.690002")
    assert result.canonical.low == Decimal("69.290001")
    assert result.canonical.close == Decimal("84.690002")


def test_missing_secondary_source_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary"),
        None,
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.canonical is None
    assert result.reason == "SECONDARY_SOURCE_MISSING"


def test_missing_primary_source_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        None,
        make_bar("secondary"),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.canonical is None
    assert result.reason == "PRIMARY_SOURCE_MISSING"


def test_same_named_sources_are_not_considered_independent() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("same-provider"),
        make_bar("same-provider"),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.reason == "SOURCES_NOT_INDEPENDENT"


def test_excessive_close_deviation_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary"),
        make_bar("secondary", "10.10"),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.reason == "CLOSE_DEVIATION_EXCEEDED"


def test_excessive_open_deviation_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary"),
        make_bar("secondary", open_price="9.90"),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.canonical is None
    assert result.reason == "OPEN_DEVIATION_EXCEEDED"


def test_excessive_high_deviation_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary"),
        make_bar("secondary", high="10.30"),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.canonical is None
    assert result.reason == "HIGH_DEVIATION_EXCEEDED"


def test_excessive_low_deviation_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary"),
        make_bar("secondary", low="9.80"),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.canonical is None
    assert result.reason == "LOW_DEVIATION_EXCEEDED"


def test_close_and_intraday_fields_support_separate_public_source_tolerances() -> None:
    result = MarketDataQualityGate(
        max_close_deviation_bps=Decimal("100"),
        max_intraday_deviation_bps=Decimal("200"),
    ).validate(
        make_bar("primary"),
        make_bar("secondary", "10.09", open_price="9.95", high="10.30", low="9.84"),
    )

    assert result.status is MarketDataStatus.VALID


def test_excessive_volume_deviation_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary", volume=1_000_000),
        make_bar("secondary", volume=700_000),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.canonical is None
    assert result.reason == "VOLUME_DEVIATION_EXCEEDED"


def test_configured_volume_tolerance_uses_lower_source_volume() -> None:
    result = MarketDataQualityGate(
        max_close_deviation_bps=Decimal("50"),
        max_volume_deviation_ratio=Decimal("0.40"),
    ).validate(
        make_bar("primary", volume=1_000_000),
        make_bar("secondary", volume=700_000),
    )

    assert result.status is MarketDataStatus.VALID
    assert result.canonical is not None
    assert result.canonical.volume == 700_000


def test_two_zero_volumes_are_accepted() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary", volume=0),
        make_bar("secondary", volume=0),
    )

    assert result.status is MarketDataStatus.VALID
    assert result.canonical is not None


def test_only_one_zero_volume_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary", volume=0),
        make_bar("secondary", volume=1_000_000),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.canonical is None
    assert result.reason == "VOLUME_DEVIATION_EXCEEDED"


def test_invalid_ohlc_is_rejected_at_boundary() -> None:
    try:
        MarketBar(
            symbol="603005.SH",
            trade_date=date(2026, 7, 15),
            open=Decimal("10"),
            high=Decimal("9"),
            low=Decimal("8"),
            close=Decimal("8.5"),
            volume=10,
            currency="CNY",
            source="broken",
        )
    except ValueError as exc:
        assert "OHLC" in str(exc)
    else:
        raise AssertionError("非法 OHLC 必须在数据边界被拒绝")


def test_symbol_mismatch_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary"),
        make_bar("secondary", symbol="600584.SH"),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.reason == "SYMBOL_MISMATCH"


def test_trade_date_mismatch_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary"),
        make_bar("secondary", trade_date=date(2026, 7, 14)),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.reason == "TRADE_DATE_MISMATCH"


def test_currency_mismatch_is_quarantined() -> None:
    result = MarketDataQualityGate(max_close_deviation_bps=Decimal("50")).validate(
        make_bar("primary"),
        make_bar("secondary", currency="HKD"),
    )

    assert result.status is MarketDataStatus.DATA_QUARANTINED
    assert result.reason == "CURRENCY_MISMATCH"
