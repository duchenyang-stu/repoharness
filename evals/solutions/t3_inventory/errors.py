class InventoryError(Exception):
    """库存相关错误的基类。"""


class InsufficientStock(InventoryError):
    def __init__(self, sku, requested, available):
        super().__init__(f"insufficient stock for {sku}: requested {requested}, available {available}")
        self.sku = sku
        self.requested = requested
        self.available = available
