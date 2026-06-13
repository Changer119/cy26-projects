from loop_demo.pricing import apply_discount, calculate_tax, calculate_total


def test_apply_discount():
    """8折后价格应低于原价。"""
    assert apply_discount(100, 0.2) == 80


def test_calculate_tax():
    """加税后价格应高于原价。"""
    assert calculate_tax(100, 0.1) == 110.0


def test_calculate_total():
    """100元商品打8折后为80，再加10%税应为88。"""
    assert calculate_total(100, 0.2) == 88.0
