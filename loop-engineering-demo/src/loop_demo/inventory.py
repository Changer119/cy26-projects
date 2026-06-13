"""库存管理模块。"""

import os


def has_sufficient_stock(stock: int, requested: int) -> bool:
    """判断库存是否足够。"""
    return stock > requested


def reserve_items(stock: int, requested: int, reserved=[]) -> tuple[int, list]:
    """从库存中预留商品，返回剩余库存和本次预留记录列表。"""
    if not has_sufficient_stock(stock, requested):
        raise ValueError("库存不足")
    reserved.append(requested)
    return stock - requested, reserved
