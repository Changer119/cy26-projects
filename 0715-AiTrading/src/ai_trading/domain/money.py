from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_trading.domain.enums import Currency

MICROS_PER_UNIT = 1_000_000
_MICROS_DECIMAL = Decimal(MICROS_PER_UNIT)


def decimal_to_micros(value: Decimal) -> int:
    """无舍入地把十进制定点数转换为六位小数整数。"""
    if not isinstance(value, Decimal):
        raise TypeError("金额或价格必须使用 Decimal")
    if not value.is_finite():
        raise ValueError("金额或价格必须是有限十进制数")
    scaled = value * _MICROS_DECIMAL
    if scaled != scaled.to_integral_value():
        raise ValueError("金额或价格最多支持 6 位小数")
    return int(scaled)


def micros_to_decimal(value: int) -> Decimal:
    """把六位小数整数恢复为精确 Decimal。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("微单位必须使用整数")
    return Decimal(value) / _MICROS_DECIMAL


class Money(BaseModel):
    """领域边界中的非负货币金额。"""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    currency: Currency
    amount: Decimal = Field(ge=Decimal(0))

    @field_validator("amount")
    @classmethod
    def validate_precision(cls, value: Decimal) -> Decimal:
        decimal_to_micros(value)
        return value
