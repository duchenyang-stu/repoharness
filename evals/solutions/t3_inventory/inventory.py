from errors import InsufficientStock


class Inventory:
    def __init__(self, stock):
        self._stock = dict(stock)

    def available(self, sku):
        return self._stock.get(sku, 0)

    def remove(self, sku, qty):
        available = self.available(sku)
        if qty > available:
            raise InsufficientStock(sku, qty, available)
        self._stock[sku] = available - qty
