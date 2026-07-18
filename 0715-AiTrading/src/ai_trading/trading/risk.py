"""模拟交易组合级确定性风险闸门。"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from ai_trading.domain import Instrument, InstrumentType, TradeAction, TradePlan


class RiskCode(StrEnum):
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    SINGLE_INSTRUMENT_LIMIT = "SINGLE_INSTRUMENT_LIMIT"
    MARKET_LIMIT = "MARKET_LIMIT"
    INDUSTRY_LIMIT = "INDUSTRY_LIMIT"
    DAILY_NEW_RISK_LIMIT = "DAILY_NEW_RISK_LIMIT"
    DAILY_TURNOVER_LIMIT = "DAILY_TURNOVER_LIMIT"
    NEW_RISK_STOPPED = "NEW_RISK_STOPPED"
    HARD_DRAWDOWN_ONLY_REDUCTION = "HARD_DRAWDOWN_ONLY_REDUCTION"
    NOT_SELLABLE = "NOT_SELLABLE"
    INVALID_PROPOSAL = "INVALID_PROPOSAL"


@dataclass(frozen=True, slots=True)
class RiskInstrument:
    instrument: Instrument
    fx_to_cny: Decimal
    estimated_fee_rate: Decimal = Decimal("0")

    @property
    def industry(self) -> str:
        industry = self.instrument.industry
        if industry is None:
            raise ValueError(f"缺少行业分类: {self.instrument.instrument_id}")
        return industry


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    instrument: Instrument
    quantity: int
    sellable_quantity: int
    mark_price: Decimal
    fx_to_cny: Decimal
    average_cost: Decimal | None = None
    stop_price: Decimal | None = None

    @property
    def market_value_cny(self) -> Decimal:
        return self.quantity * self.mark_price * self.fx_to_cny


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    cash_available_cny: Decimal
    nav_cny: Decimal
    peak_nav_cny: Decimal
    positions: tuple[PortfolioPosition, ...]

    @property
    def drawdown(self) -> Decimal:
        if self.peak_nav_cny <= 0:
            return Decimal("0")
        return (self.peak_nav_cny - self.nav_cny) / self.peak_nav_cny


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    single_stock_limit: Decimal = Decimal("0.30")
    single_fund_limit: Decimal = Decimal("0.50")
    single_market_limit: Decimal = Decimal("0.85")
    industry_limit: Decimal = Decimal("0.60")
    daily_new_risk_limit: Decimal = Decimal("0.50")
    daily_turnover_limit: Decimal = Decimal("1.00")
    stop_new_risk_drawdown: Decimal = Decimal("0.25")
    hard_drawdown: Decimal = Decimal("0.30")


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    approved: bool
    codes: tuple[RiskCode, ...]
    required_buying_power_cny: Decimal
    daily_new_risk_cny: Decimal
    daily_turnover_cny: Decimal


def _profile(
    profiles: tuple[RiskInstrument, ...],
    instrument_id: str,
) -> RiskInstrument | None:
    return next(
        (item for item in profiles if item.instrument.instrument_id == instrument_id),
        None,
    )


def _position(
    snapshot: PortfolioSnapshot,
    instrument_id: str,
) -> PortfolioPosition | None:
    return next(
        (item for item in snapshot.positions if item.instrument.instrument_id == instrument_id),
        None,
    )


def _append(codes: tuple[RiskCode, ...], code: RiskCode) -> tuple[RiskCode, ...]:
    return codes if code in codes else (*codes, code)


def _buy_notional(
    trade_plan: TradePlan,
    profile: RiskInstrument,
) -> Decimal:
    return sum(
        (
            proposal.delta_quantity * proposal.limit_price * profile.fx_to_cny
            for proposal in trade_plan.proposals
            if proposal.instrument_id == profile.instrument.instrument_id
            and proposal.action is TradeAction.BUY
            and proposal.limit_price is not None
        ),
        Decimal("0"),
    )


def _existing_exposure(snapshot: PortfolioSnapshot, instrument_id: str) -> Decimal:
    position = _position(snapshot, instrument_id)
    return Decimal("0") if position is None else position.market_value_cny


def _belongs_to_industry(
    position: PortfolioPosition,
    profiles: tuple[RiskInstrument, ...],
    industry: str,
) -> bool:
    matched = _profile(profiles, position.instrument.instrument_id)
    return matched is not None and matched.industry == industry


def evaluate_trade_plan(
    trade_plan: TradePlan,
    snapshot: PortfolioSnapshot,
    profiles: tuple[RiskInstrument, ...],
    policy: RiskPolicy,
) -> RiskAssessment:
    """按所有买入成交、所有卖出不成交的最坏情形原子审核整个计划。"""

    codes: tuple[RiskCode, ...] = ()
    buying_power = Decimal("0")
    new_risk = Decimal("0")
    turnover = Decimal("0")
    drawdown = snapshot.drawdown

    for proposal in trade_plan.proposals:
        if proposal.action is TradeAction.HOLD:
            continue
        profile = _profile(profiles, proposal.instrument_id)
        if profile is None or proposal.limit_price is None:
            codes = _append(codes, RiskCode.INVALID_PROPOSAL)
            continue
        notional = abs(proposal.delta_quantity) * proposal.limit_price * profile.fx_to_cny
        turnover += notional
        if proposal.action is TradeAction.BUY:
            new_risk += notional
            buying_power += notional * (Decimal("1") + profile.estimated_fee_rate)
            if drawdown >= policy.hard_drawdown:
                codes = _append(codes, RiskCode.HARD_DRAWDOWN_ONLY_REDUCTION)
            elif drawdown >= policy.stop_new_risk_drawdown:
                codes = _append(codes, RiskCode.NEW_RISK_STOPPED)
        elif proposal.action is TradeAction.SELL:
            position = _position(snapshot, proposal.instrument_id)
            requested = abs(proposal.delta_quantity)
            if position is None or requested > position.sellable_quantity:
                codes = _append(codes, RiskCode.NOT_SELLABLE)

    if buying_power > snapshot.cash_available_cny:
        codes = _append(codes, RiskCode.INSUFFICIENT_CASH)

    for profile in profiles:
        purchase = _buy_notional(trade_plan, profile)
        exposure = _existing_exposure(snapshot, profile.instrument.instrument_id) + purchase
        limit = (
            policy.single_fund_limit
            if profile.instrument.instrument_type in (InstrumentType.ETF, InstrumentType.LOF)
            else policy.single_stock_limit
        )
        if purchase > 0 and exposure > snapshot.nav_cny * limit:
            codes = _append(codes, RiskCode.SINGLE_INSTRUMENT_LIMIT)

    for profile in profiles:
        market_purchase = sum(
            (
                _buy_notional(trade_plan, item)
                for item in profiles
                if item.instrument.market is profile.instrument.market
            ),
            Decimal("0"),
        )
        market_exposure = (
            sum(
                (
                    item.market_value_cny
                    for item in snapshot.positions
                    if item.instrument.market is profile.instrument.market
                ),
                Decimal("0"),
            )
            + market_purchase
        )
        if market_purchase > 0 and market_exposure > snapshot.nav_cny * policy.single_market_limit:
            codes = _append(codes, RiskCode.MARKET_LIMIT)

        industry_purchase = sum(
            (
                _buy_notional(trade_plan, item)
                for item in profiles
                if item.industry == profile.industry
            ),
            Decimal("0"),
        )
        industry_exposure = (
            sum(
                (
                    item.market_value_cny
                    for item in snapshot.positions
                    if _belongs_to_industry(item, profiles, profile.industry)
                ),
                Decimal("0"),
            )
            + industry_purchase
        )
        if industry_purchase > 0 and industry_exposure > snapshot.nav_cny * policy.industry_limit:
            codes = _append(codes, RiskCode.INDUSTRY_LIMIT)

    if new_risk > snapshot.nav_cny * policy.daily_new_risk_limit:
        codes = _append(codes, RiskCode.DAILY_NEW_RISK_LIMIT)
    if turnover > snapshot.nav_cny * policy.daily_turnover_limit:
        codes = _append(codes, RiskCode.DAILY_TURNOVER_LIMIT)
    return RiskAssessment(not codes, codes, buying_power, new_risk, turnover)
