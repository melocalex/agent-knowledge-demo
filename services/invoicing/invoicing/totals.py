"""Invoice totals in integer minor units (for example cents).

Rule from docs/agent-memory/decisions.md (2026-10-14): amounts are integers in
minor units everywhere. Tax is rounded once, half-up, on the tax line.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineItem:
    description: str
    quantity: int
    unit_price_minor: int

    def __post_init__(self) -> None:
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        if not isinstance(self.unit_price_minor, int) or self.unit_price_minor < 0:
            raise ValueError("unit_price_minor must be a non-negative integer")

    @property
    def amount_minor(self) -> int:
        return self.quantity * self.unit_price_minor


@dataclass(frozen=True)
class InvoiceTotals:
    subtotal_minor: int
    tax_minor: int
    total_minor: int


def compute_totals(items: list[LineItem], tax_rate_bp: int) -> InvoiceTotals:
    """Compute subtotal, tax and total.

    tax_rate_bp is the tax rate in basis points (1 bp = 0.01%), so 2000 is 20%.
    Tax is rounded half-up once on the whole subtotal, never per item.
    """
    if not isinstance(tax_rate_bp, int) or tax_rate_bp < 0:
        raise ValueError("tax_rate_bp must be a non-negative integer")
    subtotal = sum(item.amount_minor for item in items)
    tax = (subtotal * tax_rate_bp + 5000) // 10000
    return InvoiceTotals(subtotal_minor=subtotal, tax_minor=tax, total_minor=subtotal + tax)
