from enum import StrEnum


class Currency(StrEnum):
    CNY = "CNY"
    HKD = "HKD"


class Market(StrEnum):
    SSE = "SSE"
    SZSE = "SZSE"
    HKEX = "HKEX"


class InstrumentType(StrEnum):
    STOCK = "STOCK"
    ETF = "ETF"
    LOF = "LOF"


class TradeAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class ProposalStatus(StrEnum):
    GENERATED = "GENERATED"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    HOLD = "HOLD"


class TradePlanStatus(StrEnum):
    DRAFT = "DRAFT"
    RISK_CHECKED = "RISK_CHECKED"
    FROZEN = "FROZEN"
    RECONCILED = "RECONCILED"
    ABORTED = "ABORTED"


class OrderStatus(StrEnum):
    PENDING_OPEN = "PENDING_OPEN"
    FILLED = "FILLED"
    UNFILLED = "UNFILLED"
    EXECUTION_REJECTED = "EXECUTION_REJECTED"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
