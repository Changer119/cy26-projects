import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from ai_trading.application.models import EvidenceBatch, QualifiedMarketEvidence
from ai_trading.application.store import ApplicationStore
from ai_trading.domain import Currency, Instrument, Market
from ai_trading.integrations.market_data import (
    MarketBar,
    MarketDataProviderError,
    MarketDataQualityGate,
    MarketDataRangeRequest,
    MarketDataRequest,
    MarketDataStatus,
)
from ai_trading.strategy_v2.features import calculate_features
from ai_trading.strategy_v2.history import has_complete_history, previous_session_date
from ai_trading.strategy_v2.models import HistoricalBar, StrategyFeatures

logger = logging.getLogger(__name__)


class HistoricalMarketProvider(Protocol):
    def fetch(self, request: MarketDataRequest) -> MarketBar: ...

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]: ...


class UnavailableEvidenceLoader:
    def __init__(self, store: ApplicationStore, reason: str) -> None:
        self._store = store
        self._reason = reason

    def load(self, trade_date: date) -> EvidenceBatch:
        return EvidenceBatch(
            trade_date=trade_date,
            qualified=(),
            unavailable_instrument_ids=tuple(
                item.instrument_id for item in self._store.watchlist()
            ),
            reason=self._reason,
        )

    def load_current_session(self, trade_date: date) -> EvidenceBatch:
        return self.load(trade_date)


class DualSourceEvidenceLoader:
    def __init__(
        self,
        store: ApplicationStore,
        yahoo: HistoricalMarketProvider,
        tiingo: HistoricalMarketProvider,
        quality_gate: MarketDataQualityGate,
    ) -> None:
        self._store = store
        self._yahoo = yahoo
        self._tiingo = tiingo
        self._quality_gate = quality_gate

    def load(self, trade_date: date) -> EvidenceBatch:
        evidence_date = previous_session_date(Market.SSE, trade_date)
        return self._load_premarket_batch(trade_date, evidence_date)

    def load_current_session(self, trade_date: date) -> EvidenceBatch:
        return self._load_batch(trade_date, trade_date)

    def _load_batch(self, trade_date: date, evidence_date: date) -> EvidenceBatch:
        qualified: tuple[QualifiedMarketEvidence, ...] = ()
        unavailable: tuple[str, ...] = ()
        for instrument in self._store.watchlist():
            evidence = self._load_one(instrument, evidence_date)
            if evidence is None:
                unavailable += (instrument.instrument_id,)
            else:
                qualified += (evidence,)
        if not qualified:
            reason = "DUAL_SOURCE_DATA_UNAVAILABLE"
        elif unavailable:
            reason = "PARTIAL_DATA"
        else:
            reason = "DUAL_SOURCE_DATA_VALID"
        return EvidenceBatch(
            trade_date=trade_date,
            qualified=qualified,
            strategy_features=(),
            unavailable_instrument_ids=unavailable,
            reason=reason,
        )

    def _load_premarket_batch(self, trade_date: date, evidence_date: date) -> EvidenceBatch:
        qualified: tuple[QualifiedMarketEvidence, ...] = ()
        features: tuple[StrategyFeatures, ...] = ()
        unavailable: tuple[str, ...] = ()
        for instrument in self._store.watchlist():
            result = self._load_strategy_one(instrument, trade_date, evidence_date)
            if result is None:
                unavailable += (instrument.instrument_id,)
            else:
                market, feature = result
                qualified += (market,)
                features += (feature,)
        if not qualified:
            reason = "DUAL_SOURCE_DATA_UNAVAILABLE"
        elif unavailable:
            reason = "PARTIAL_DATA"
        else:
            reason = "DUAL_SOURCE_DATA_VALID"
        return EvidenceBatch(
            trade_date=trade_date,
            qualified=qualified,
            strategy_features=features,
            unavailable_instrument_ids=unavailable,
            reason=reason,
        )

    def _load_strategy_one(
        self,
        instrument: Instrument,
        trade_date: date,
        evidence_date: date,
    ) -> tuple[QualifiedMarketEvidence, StrategyFeatures] | None:
        if instrument.currency is not Currency.CNY:
            return None
        start_date = evidence_date - timedelta(days=180)
        yahoo_request = MarketDataRangeRequest(
            symbol=instrument.instrument_id,
            provider_symbol=self._provider_symbol(instrument, yahoo=True),
            start_date=start_date,
            end_date=evidence_date,
            currency=instrument.currency.value,
        )
        tiingo_request = MarketDataRangeRequest(
            symbol=instrument.instrument_id,
            provider_symbol=self._provider_symbol(instrument, yahoo=False),
            start_date=start_date,
            end_date=evidence_date,
            currency=instrument.currency.value,
        )
        try:
            primary = self._yahoo.fetch_range(yahoo_request)
            secondary = self._tiingo.fetch_range(tiingo_request)
        except MarketDataProviderError as exc:
            logger.warning(
                "V2 历史行情源失败 instrument=%s kind=%s",
                instrument.instrument_id,
                exc.kind.value,
            )
            return None
        canonical = self._qualified_history(primary, secondary)
        if len(canonical) < 60 or canonical[-1].trade_date != evidence_date:
            return None
        selected = canonical[-60:]
        if not has_complete_history(
            instrument.market,
            evidence_date,
            tuple(item.trade_date for item in selected),
        ):
            return None
        historical = tuple(
            HistoricalBar(
                trade_date=item.trade_date,
                open=item.open,
                high=item.high,
                low=item.low,
                close=item.close,
                volume=item.volume,
                available_at=datetime.combine(
                    item.trade_date,
                    time(18),
                    ZoneInfo("Asia/Shanghai"),
                ),
            )
            for item in selected
        )
        decision_asof = datetime.combine(trade_date, time(7, 50), ZoneInfo("Asia/Shanghai"))
        feature = calculate_features(instrument.instrument_id, historical, decision_asof)
        latest = selected[-1]
        return (
            QualifiedMarketEvidence(
                instrument_id=instrument.instrument_id,
                open=latest.open,
                high=latest.high,
                low=latest.low,
                close=latest.close,
                volume=latest.volume,
                fx_to_cny=Decimal(1),
                current_quantity=self._store.quantity(instrument.instrument_id),
                evidence_date=evidence_date,
            ),
            feature,
        )

    def _qualified_history(
        self,
        primary: tuple[MarketBar, ...],
        secondary: tuple[MarketBar, ...],
    ) -> tuple[MarketBar, ...]:
        dates = sorted(
            {item.trade_date for item in primary} | {item.trade_date for item in secondary}
        )
        result: tuple[MarketBar, ...] = ()
        rejections: tuple[str, ...] = ()
        for session_date in dates:
            first = next((item for item in primary if item.trade_date == session_date), None)
            second = next((item for item in secondary if item.trade_date == session_date), None)
            quality = self._quality_gate.validate(first, second)
            if quality.status is MarketDataStatus.VALID and quality.canonical is not None:
                result += (quality.canonical,)
            else:
                first_values = "missing" if first is None else f"{first.close}/{first.volume}"
                second_values = "missing" if second is None else f"{second.close}/{second.volume}"
                rejections += (
                    f"{session_date}:{quality.reason or 'UNKNOWN'}:"
                    f"p={first_values}:s={second_values}",
                )
        if rejections:
            logger.warning(
                "V2 双源历史隔离 primary=%d secondary=%d valid=%d reasons=%s",
                len(primary),
                len(secondary),
                len(result),
                ",".join(sorted(set(rejections))),
            )
        return result

    def _load_one(
        self,
        instrument: Instrument,
        evidence_date: date,
    ) -> QualifiedMarketEvidence | None:
        if instrument.currency is not Currency.CNY:
            return None
        request = MarketDataRequest(
            symbol=instrument.instrument_id,
            provider_symbol=self._provider_symbol(instrument, yahoo=True),
            trade_date=evidence_date,
            currency=instrument.currency.value,
        )
        tiingo_request = MarketDataRequest(
            symbol=instrument.instrument_id,
            provider_symbol=self._provider_symbol(instrument, yahoo=False),
            trade_date=evidence_date,
            currency=instrument.currency.value,
        )
        try:
            primary = self._yahoo.fetch(request)
        except MarketDataProviderError as exc:
            cause = exc.__cause__
            logger.warning(
                "行情源失败 provider=yahoo instrument=%s kind=%s cause=%s detail=%s",
                instrument.instrument_id,
                exc.kind.value,
                "none" if cause is None else type(cause).__name__,
                "none" if cause is None else str(cause)[:200],
            )
            return None
        try:
            secondary = self._tiingo.fetch(tiingo_request)
        except MarketDataProviderError as exc:
            logger.warning(
                "行情源失败 provider=tiingo instrument=%s kind=%s",
                instrument.instrument_id,
                exc.kind.value,
            )
            return None
        quality = self._quality_gate.validate(primary, secondary)
        if quality.status is not MarketDataStatus.VALID or quality.canonical is None:
            logger.warning(
                "行情质量门拒绝 instrument=%s reason=%s",
                instrument.instrument_id,
                quality.reason,
            )
            return None
        bar = quality.canonical
        return QualifiedMarketEvidence(
            instrument_id=instrument.instrument_id,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            fx_to_cny=Decimal(1),
            current_quantity=self._store.quantity(instrument.instrument_id),
            evidence_date=evidence_date,
        )

    @staticmethod
    def _provider_symbol(instrument: Instrument, *, yahoo: bool) -> str:
        numeric = instrument.instrument_id.split(".", maxsplit=1)[0]
        if not yahoo:
            return numeric
        suffix = (
            "SS"
            if instrument.market is Market.SSE
            else ("SZ" if instrument.market is Market.SZSE else "HK")
        )
        return f"{numeric}.{suffix}"
