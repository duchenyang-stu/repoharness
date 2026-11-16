FREE_SHIPPING_THRESHOLD = 5000
FLAT_SHIPPING = 599


def shipping_cents(subtotal_cents):
    return 0 if subtotal_cents >= FREE_SHIPPING_THRESHOLD else FLAT_SHIPPING
