import csv
import io

from .errors import DuplicateIdError, MissingColumnError
from .models import Order
from .validators import parse_amount

REQUIRED = ("id", "customer", "amount")


def read_orders(text):
    reader = csv.reader(io.StringIO(text))
    index = None
    seen = set()
    orders = []
    for row in reader:
        if not row or all(not cell.strip() for cell in row):
            continue
        if index is None:
            header = [cell.strip().lower() for cell in row]
            for name in REQUIRED:
                if name not in header:
                    raise MissingColumnError(name)
            index = {name: header.index(name) for name in REQUIRED}
            continue
        order_id = row[index["id"]].strip()
        if order_id in seen:
            raise DuplicateIdError(order_id, reader.line_num)
        seen.add(order_id)
        orders.append(Order(order_id, row[index["customer"]].strip(), parse_amount(row[index["amount"]])))
    return orders
