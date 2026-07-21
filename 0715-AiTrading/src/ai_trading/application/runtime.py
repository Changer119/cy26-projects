from datetime import date
from decimal import Decimal

import httpx

from ai_trading.application.evidence import (
    DualSourceEvidenceLoader,
    UnavailableEvidenceLoader,
)
from ai_trading.application.models import EvidenceBatch
from ai_trading.application.planning import DeepSeekProposalSource
from ai_trading.application.postmarket import PostmarketService
from ai_trading.application.store import ApplicationStore
from ai_trading.application.workflows import TradingApplication
from ai_trading.config import Settings
from ai_trading.domain import Currency
from ai_trading.integrations.deepseek import DeepSeekClient
from ai_trading.integrations.market_data import MarketDataQualityGate
from ai_trading.integrations.tiingo import TiingoEodProvider
from ai_trading.integrations.yahoo import YahooEodProvider
from ai_trading.trading.fees import FeeSchedule


def build_application(settings: Settings) -> TradingApplication:
    store = ApplicationStore(settings.database_url)
    client = httpx.Client(timeout=httpx.Timeout(20))
    proposal_source = DeepSeekProposalSource(
        DeepSeekClient(settings.deepseek_api_key, client, max_retries=2)
    )
    evidence_loader = _build_evidence_loader(settings, store, client)
    fee_schedule = FeeSchedule(
        schedule_id="a-share-simulation-v1",
        effective_from=date(2026, 1, 1),
        currency=Currency.CNY,
        commission_rate=Decimal("0.0003"),
        minimum_commission=Decimal("5"),
        transfer_rate=Decimal("0.00001"),
        stock_buy_tax_rate=Decimal("0"),
        stock_sell_tax_rate=Decimal("0.0005"),
    )
    postmarket = PostmarketService(store, evidence_loader, fee_schedule, Decimal("0.001"))
    return TradingApplication(store, evidence_loader, proposal_source, postmarket)


def load_market_data(settings: Settings, trade_date: date) -> EvidenceBatch:
    """只读拉取并验证行情，不调用模型，也不创建计划或订单。"""

    store = ApplicationStore(settings.database_url)
    store.initialize()
    with httpx.Client(timeout=httpx.Timeout(20)) as client:
        loader = _build_evidence_loader(settings, store, client)
        return loader.load_current_session(trade_date)


def load_strategy_data(settings: Settings, trade_date: date) -> EvidenceBatch:
    """只读验证 V2 历史特征，不调用模型，也不创建计划或订单。"""

    store = ApplicationStore(settings.database_url)
    store.initialize()
    with httpx.Client(timeout=httpx.Timeout(20)) as client:
        loader = _build_evidence_loader(settings, store, client)
        return loader.load(trade_date)


def _build_evidence_loader(
    settings: Settings,
    store: ApplicationStore,
    client: httpx.Client,
) -> UnavailableEvidenceLoader | DualSourceEvidenceLoader:
    token = settings.tiingo_api_key
    evidence_loader: UnavailableEvidenceLoader | DualSourceEvidenceLoader
    if token is None or not token.get_secret_value().strip():
        evidence_loader = UnavailableEvidenceLoader(store, "TIINGO_TOKEN_MISSING")
    else:
        evidence_loader = DualSourceEvidenceLoader(
            store=store,
            yahoo=YahooEodProvider(),
            tiingo=TiingoEodProvider(token, client),
            quality_gate=MarketDataQualityGate(
                max_close_deviation_bps=Decimal("100"),
                max_intraday_deviation_bps=Decimal("200"),
                max_volume_deviation_ratio=Decimal("0.40"),
            ),
        )
    return evidence_loader
