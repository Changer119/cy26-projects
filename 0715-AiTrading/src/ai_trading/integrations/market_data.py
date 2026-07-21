"""行情数据的强类型边界与双源质量门。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MarketDataStatus(StrEnum):
    """双源校验后的数据状态。"""

    VALID = "VALID"
    DATA_QUARANTINED = "DATA_QUARANTINED"


class MarketDataProviderErrorKind(StrEnum):
    """行情提供方错误的稳定分类。"""

    CONFIGURATION = "CONFIGURATION"
    AUTHENTICATION = "AUTHENTICATION"
    NOT_FOUND = "NOT_FOUND"
    UPSTREAM = "UPSTREAM"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class MarketDataProviderError(RuntimeError):
    """不携带上游响应正文或凭据的安全错误。"""

    def __init__(self, kind: MarketDataProviderErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class MarketDataRequest(BaseModel):
    """内部证券代码到外部提供方代码的显式请求。"""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    symbol: str = Field(min_length=1)
    provider_symbol: str = Field(min_length=1)
    trade_date: date
    currency: str = Field(min_length=3, max_length=3)


class MarketDataRangeRequest(BaseModel):
    """内部统一为起止日期均包含的历史行情区间。"""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    symbol: str = Field(min_length=1)
    provider_symbol: str = Field(min_length=1)
    start_date: date
    end_date: date
    currency: str = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_range(self) -> MarketDataRangeRequest:
        if self.start_date > self.end_date:
            raise ValueError("历史行情开始日期不得晚于结束日期")
        return self


class MarketBar(BaseModel):
    """单一数据源的一根日线。"""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    symbol: str = Field(min_length=1)
    trade_date: date
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_ohlc(self) -> MarketBar:
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("OHLC 中最高价低于开盘价、最低价或收盘价")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("OHLC 中最低价高于开盘价、最高价或收盘价")
        return self


class MarketDataQualityResult(BaseModel):
    """质量门输出; 隔离状态下不允许携带可交易行情。"""

    model_config = ConfigDict(frozen=True)

    status: MarketDataStatus
    canonical: MarketBar | None
    reason: str | None = None
    close_deviation_bps: Decimal | None = None


class MarketDataQualityGate:
    """要求两个独立来源在容差内相互印证。"""

    def __init__(
        self,
        max_close_deviation_bps: Decimal,
        max_intraday_deviation_bps: Decimal | None = None,
        max_volume_deviation_ratio: Decimal = Decimal("0.20"),
    ) -> None:
        intraday = (
            max_close_deviation_bps
            if max_intraday_deviation_bps is None
            else (max_intraday_deviation_bps)
        )
        if max_close_deviation_bps < 0 or intraday < 0:
            raise ValueError("价格偏差阈值不得为负数")
        if not Decimal(0) <= max_volume_deviation_ratio <= Decimal(1):
            raise ValueError("成交量偏差阈值必须在 0 到 1 之间")
        self._max_close_deviation_bps = max_close_deviation_bps
        self._max_intraday_deviation_bps = intraday
        self._max_volume_deviation_ratio = max_volume_deviation_ratio

    def validate(
        self,
        primary: MarketBar | None,
        secondary: MarketBar | None,
    ) -> MarketDataQualityResult:
        if primary is None:
            return MarketDataQualityResult(
                status=MarketDataStatus.DATA_QUARANTINED,
                canonical=None,
                reason="PRIMARY_SOURCE_MISSING",
            )
        if secondary is None:
            return MarketDataQualityResult(
                status=MarketDataStatus.DATA_QUARANTINED,
                canonical=None,
                reason="SECONDARY_SOURCE_MISSING",
            )

        if primary.source == secondary.source:
            return MarketDataQualityResult(
                status=MarketDataStatus.DATA_QUARANTINED,
                canonical=None,
                reason="SOURCES_NOT_INDEPENDENT",
            )

        if primary.symbol != secondary.symbol:
            return MarketDataQualityResult(
                status=MarketDataStatus.DATA_QUARANTINED,
                canonical=None,
                reason="SYMBOL_MISMATCH",
            )
        if primary.trade_date != secondary.trade_date:
            return MarketDataQualityResult(
                status=MarketDataStatus.DATA_QUARANTINED,
                canonical=None,
                reason="TRADE_DATE_MISMATCH",
            )
        if primary.currency != secondary.currency:
            return MarketDataQualityResult(
                status=MarketDataStatus.DATA_QUARANTINED,
                canonical=None,
                reason="CURRENCY_MISMATCH",
            )

        close_deviation_bps = self._price_deviation_bps(primary.close, secondary.close)
        if close_deviation_bps > self._max_close_deviation_bps:
            return MarketDataQualityResult(
                status=MarketDataStatus.DATA_QUARANTINED,
                canonical=None,
                reason="CLOSE_DEVIATION_EXCEEDED",
                close_deviation_bps=close_deviation_bps,
            )

        price_checks = (
            (primary.open, secondary.open, "OPEN_DEVIATION_EXCEEDED"),
            (primary.high, secondary.high, "HIGH_DEVIATION_EXCEEDED"),
            (primary.low, secondary.low, "LOW_DEVIATION_EXCEEDED"),
        )
        for primary_price, secondary_price, reason in price_checks:
            deviation_bps = self._price_deviation_bps(primary_price, secondary_price)
            if deviation_bps > self._max_intraday_deviation_bps:
                return MarketDataQualityResult(
                    status=MarketDataStatus.DATA_QUARANTINED,
                    canonical=None,
                    reason=reason,
                    close_deviation_bps=close_deviation_bps,
                )

        volume_deviation_ratio = self._volume_deviation_ratio(primary.volume, secondary.volume)
        if volume_deviation_ratio > self._max_volume_deviation_ratio:
            return MarketDataQualityResult(
                status=MarketDataStatus.DATA_QUARANTINED,
                canonical=None,
                reason="VOLUME_DEVIATION_EXCEEDED",
                close_deviation_bps=close_deviation_bps,
            )

        return MarketDataQualityResult(
            status=MarketDataStatus.VALID,
            canonical=self._conservative_bar(primary, secondary),
            close_deviation_bps=close_deviation_bps,
        )

    @staticmethod
    def _conservative_bar(primary: MarketBar, secondary: MarketBar) -> MarketBar:
        return MarketBar(
            symbol=primary.symbol,
            trade_date=primary.trade_date,
            open=primary.open,
            high=primary.high,
            low=primary.low,
            close=primary.close,
            volume=min(primary.volume, secondary.volume),
            currency=primary.currency,
            source=primary.source,
        )

    @staticmethod
    def _price_deviation_bps(primary: Decimal, secondary: Decimal) -> Decimal:
        return abs(primary - secondary) / secondary * Decimal("10000")

    @staticmethod
    def _volume_deviation_ratio(primary: int, secondary: int) -> Decimal:
        largest_volume = max(primary, secondary)
        if largest_volume == 0:
            return Decimal(0)
        return Decimal(abs(primary - secondary)) / Decimal(largest_volume)
