from decimal import Decimal

import pytest
from pydantic import ValidationError

from ai_trading.domain import Currency, Money, decimal_to_micros, micros_to_decimal


def test_decimal_and_micros_round_trip_exactly() -> None:
    amount = Decimal("100000.000001")

    micros = decimal_to_micros(amount)

    assert micros == 100_000_000_001
    assert micros_to_decimal(micros) == amount


def test_decimal_to_micros_rejects_precision_loss() -> None:
    with pytest.raises(ValueError, match="6 位小数"):
        decimal_to_micros(Decimal("1.0000001"))


def test_money_rejects_negative_amount_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Money(currency=Currency.CNY, amount=Decimal("-0.000001"))

    with pytest.raises(ValidationError):
        Money.model_validate({"currency": "CNY", "amount": "1", "unexpected": "forbidden"})
