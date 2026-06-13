from loop_demo.inventory import has_sufficient_stock, reserve_items


def test_has_sufficient_stock_enough():
    """库存恰好等于请求量时应视为足够。"""
    assert has_sufficient_stock(10, 10) is True


def test_has_sufficient_stock_not_enough():
    """库存少于请求量时应视为不足。"""
    assert has_sufficient_stock(5, 10) is False


def test_reserve_items_does_not_leak_between_calls():
    """不同订单的预留记录不应互相串联。"""
    remaining_a, reserved_a = reserve_items(10, 3)
    remaining_b, reserved_b = reserve_items(20, 5)

    assert remaining_a == 7
    assert remaining_b == 15
    assert reserved_a == [3]
    assert reserved_b == [5]
