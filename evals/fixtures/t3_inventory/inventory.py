class Inventory:
    def __init__(self, stock):
        self._stock = dict(stock)

    def available(self, sku):
        return self._stock.get(sku, 0)

    def remove(self, sku, qty):
        self._stock[sku] = self.available(sku) - qty
