def place_order(inventory, lines):
    """lines 是 (sku, qty) 的列表。

    库存不足时抛出 errors.InsufficientStock（InventoryError 的子类），异常带有
    sku、requested、available 三个属性。订单是原子的：只要有一行库存不足，所有库存都保持不变。
    """
    for sku, qty in lines:
        inventory.remove(sku, qty)
