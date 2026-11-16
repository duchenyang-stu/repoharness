from .shipping import shipping_cents
from .tax import line_tax


class Cart:
    def __init__(self, tax_rate=0.0):
        self.tax_rate = tax_rate
        self.lines = []

    def add(self, name, unit_cents, qty=1):
        if qty <= 0:
            raise ValueError("qty must be positive")
        self.lines.append((name, unit_cents, qty))

    def subtotal(self):
        return sum(unit * qty for _, unit, qty in self.lines)

    def tax(self):
        return sum(line_tax(unit * qty, self.tax_rate) for _, unit, qty in self.lines)

    def total(self):
        subtotal = self.subtotal()
        return subtotal + self.tax() + shipping_cents(subtotal)
