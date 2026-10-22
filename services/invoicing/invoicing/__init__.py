"""Tiny example invoicing library used to demonstrate per-package agent files."""

from .totals import LineItem, InvoiceTotals, compute_totals

__all__ = ["LineItem", "InvoiceTotals", "compute_totals"]
