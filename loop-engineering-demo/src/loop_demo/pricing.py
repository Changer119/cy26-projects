"""订单价格计算模块。"""


def apply_discount(price: float, discount_rate: float) -> float:
    """根据折扣率计算折后价格。"""
    return price - price * discount_rate


def calculate_tax(price: float, tax_rate: float = 0.1) -> float:
    """计算含税价格。"""
    return round(price * (1 + tax_rate), 2)


def calculate_total(price: float, discount_rate: float, tax_rate: float = 0.1) -> float:
    """计算最终总价：先打折，再加税。"""
    discounted = apply_discount(price, discount_rate)
    return calculate_tax(discounted, tax_rate)
