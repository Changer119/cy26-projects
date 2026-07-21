"""从现金、持仓和收盘标记生成幂等的每日人民币净值。"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ai_trading.domain import Currency, decimal_to_micros, micros_to_decimal
from ai_trading.storage.ledger_tables import DailyValuationRow, FillRow
from ai_trading.storage.repository import INITIAL_CASH_CNY_MICROS
from ai_trading.storage.tables import CashBalanceRow, PositionRow

MICRO_QUANTUM = Decimal("0.000001")


class ValuationError(ValueError):
    pass


class ValuationMark(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    instrument_id: str = Field(min_length=1)
    close: Decimal = Field(gt=Decimal(0))
    fx_to_cny: Decimal = Field(gt=Decimal(0))

    @field_validator("close", "fx_to_cny")
    @classmethod
    def validate_precision(cls, value: Decimal) -> Decimal:
        decimal_to_micros(value)
        return value


class ValuationOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    created: bool
    nav_cny: Decimal
    total_pnl_cny: Decimal
    daily_pnl_cny: Decimal
    realized_pnl_cny: Decimal
    unrealized_pnl_cny: Decimal
    fees_cny: Decimal
    drawdown: Decimal


class ValuationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record(
        self,
        account_id: str,
        trade_date: date,
        marks: tuple[ValuationMark, ...],
    ) -> ValuationOutcome:
        with self._session_factory() as session, session.begin():
            existing = session.get(DailyValuationRow, (account_id, trade_date))
            if existing is not None:
                previous = self._previous_nav_micros(session, account_id, trade_date)
                return self._outcome(existing, created=False, previous_nav_micros=previous)
            cash = session.get(CashBalanceRow, (account_id, Currency.CNY))
            if cash is None:
                raise ValuationError("人民币现金子账本不存在")
            positions = session.scalars(
                select(PositionRow).where(PositionRow.account_id == account_id)
            ).all()
            market_value_micros = 0
            unrealized_micros = 0
            for position in positions:
                mark = self._mark(marks, position.instrument_id)
                market_value_micros += self._rounded_micros(
                    mark.close * position.quantity * mark.fx_to_cny
                )
                cost = (
                    micros_to_decimal(position.average_cost_micros)
                    * position.quantity
                    * mark.fx_to_cny
                )
                unrealized_micros += self._rounded_micros(
                    mark.close * position.quantity * mark.fx_to_cny - cost
                )
            fees_micros = int(
                session.scalar(
                    select(func.coalesce(func.sum(FillRow.fee_cny_micros), 0)).where(
                        FillRow.account_id == account_id,
                        FillRow.trade_date <= trade_date,
                    )
                )
                or 0
            )
            nav_micros = cash.available_micros + market_value_micros
            total_pnl_micros = nav_micros - INITIAL_CASH_CNY_MICROS
            realized_micros = total_pnl_micros + fees_micros - unrealized_micros
            peak_micros = max(
                INITIAL_CASH_CNY_MICROS,
                int(
                    session.scalar(
                        select(func.max(DailyValuationRow.nav_cny_micros)).where(
                            DailyValuationRow.account_id == account_id,
                            DailyValuationRow.trade_date < trade_date,
                        )
                    )
                    or 0
                ),
                nav_micros,
            )
            drawdown = (
                Decimal(peak_micros - nav_micros) / peak_micros if peak_micros > 0 else Decimal(0)
            )
            row = DailyValuationRow(
                account_id=account_id,
                trade_date=trade_date,
                nav_cny_micros=nav_micros,
                cash_cny_micros=cash.available_micros,
                realized_pnl_cny_micros=realized_micros,
                unrealized_pnl_cny_micros=unrealized_micros,
                fees_cny_micros=fees_micros,
                drawdown_micros=self._rounded_micros(drawdown),
            )
            session.add(row)
            session.flush()
            previous = self._previous_nav_micros(session, account_id, trade_date)
            return self._outcome(row, created=True, previous_nav_micros=previous)

    @staticmethod
    def _mark(marks: tuple[ValuationMark, ...], instrument_id: str) -> ValuationMark:
        mark = next((item for item in marks if item.instrument_id == instrument_id), None)
        if mark is None:
            raise ValuationError(f"持仓缺少收盘估值: {instrument_id}")
        return mark

    @staticmethod
    def _rounded_micros(value: Decimal) -> int:
        rounded = value.quantize(MICRO_QUANTUM, rounding=ROUND_HALF_UP)
        return decimal_to_micros(rounded)

    @staticmethod
    def _previous_nav_micros(session: Session, account_id: str, trade_date: date) -> int:
        value = session.scalar(
            select(DailyValuationRow.nav_cny_micros)
            .where(
                DailyValuationRow.account_id == account_id,
                DailyValuationRow.trade_date < trade_date,
            )
            .order_by(DailyValuationRow.trade_date.desc())
            .limit(1)
        )
        return INITIAL_CASH_CNY_MICROS if value is None else value

    @staticmethod
    def _outcome(
        row: DailyValuationRow,
        created: bool,
        previous_nav_micros: int,
    ) -> ValuationOutcome:
        nav = micros_to_decimal(row.nav_cny_micros)
        return ValuationOutcome(
            created=created,
            nav_cny=nav,
            total_pnl_cny=nav - micros_to_decimal(INITIAL_CASH_CNY_MICROS),
            daily_pnl_cny=nav - micros_to_decimal(previous_nav_micros),
            realized_pnl_cny=micros_to_decimal(row.realized_pnl_cny_micros),
            unrealized_pnl_cny=micros_to_decimal(row.unrealized_pnl_cny_micros),
            fees_cny=micros_to_decimal(row.fees_cny_micros),
            drawdown=micros_to_decimal(row.drawdown_micros),
        )
