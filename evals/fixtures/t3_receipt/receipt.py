from cart import total_cents
from money import format_cents


def receipt(items):
    lines = []
    for item in items:
        line_total = item["price_cents"] * item["qty"]
        lines.append(f"{item['name']} x{item['qty']}  {format_cents(line_total)}")
    lines.append(f"Total: {format_cents(total_cents(items))}")
    return "\n".join(lines)
