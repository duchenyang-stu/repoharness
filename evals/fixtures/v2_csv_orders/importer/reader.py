from .models import Order
from .validators import parse_amount


def read_orders(text):
    lines = text.splitlines()
    if not lines:
        return []
    header = lines[0].split(",")
    index = {name: i for i, name in enumerate(header)}
    orders = []
    for line in lines[1:]:
        parts = line.split(",")
        orders.append(Order(parts[index["id"]], parts[index["customer"]], parse_amount(parts[index["amount"]])))
    return orders
