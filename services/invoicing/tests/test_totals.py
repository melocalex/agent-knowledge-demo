import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from invoicing import LineItem, compute_totals  # noqa: E402


class ComputeTotalsTest(unittest.TestCase):
    def test_basic_totals(self):
        items = [LineItem("Widget", 2, 1250), LineItem("Setup fee", 1, 5000)]
        totals = compute_totals(items, tax_rate_bp=2000)
        self.assertEqual(totals.subtotal_minor, 7500)
        self.assertEqual(totals.tax_minor, 1500)
        self.assertEqual(totals.total_minor, 9000)

    def test_tax_rounds_half_up_once(self):
        # 3 items of 1 minor unit at 50% tax: per-item rounding would give 3, whole-line gives 2.
        items = [LineItem("a", 1, 1), LineItem("b", 1, 1), LineItem("c", 1, 1)]
        self.assertEqual(compute_totals(items, tax_rate_bp=5000).tax_minor, 2)

    def test_empty_invoice(self):
        totals = compute_totals([], tax_rate_bp=2000)
        self.assertEqual((totals.subtotal_minor, totals.tax_minor, totals.total_minor), (0, 0, 0))

    def test_rejects_float_amounts(self):
        with self.assertRaises(ValueError):
            LineItem("Widget", 1, 12.5)

    def test_rejects_negative_tax_rate(self):
        with self.assertRaises(ValueError):
            compute_totals([], tax_rate_bp=-1)


if __name__ == "__main__":
    unittest.main()
