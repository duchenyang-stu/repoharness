from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    id: str
    customer: str
    amount_cents: int
