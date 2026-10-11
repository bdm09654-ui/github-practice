"""Behavior tests for the Decimal revenue calculator."""

from decimal import Decimal, Inexact, localcontext
from pathlib import Path
import subprocess
import sys
import unittest

from revenue_calculator import calculate_revenue


class RevenueCalculatorTests(unittest.TestCase):
    def test_normal_calculation(self):
        result = calculate_revenue("100", 10, "60")
        self.assertEqual(result.revenue, Decimal("1000"))
        self.assertEqual(result.total_cost, Decimal("600"))
        self.assertEqual(result.gross_profit, Decimal("400"))
        self.assertEqual(result.gross_margin, Decimal("40"))

    def test_decimal_precision(self):
        result = calculate_revenue(Decimal("0.30"), 3, "0.10")
        self.assertEqual(result.revenue, Decimal("0.90"))
        self.assertEqual(result.total_cost, Decimal("0.30"))
        self.assertEqual(result.gross_profit, Decimal("0.60"))
        self.assertIsInstance(result.gross_margin, Decimal)
        self.assertEqual(result.gross_margin, Decimal("66.6667"))

    def test_extreme_finite_input_is_rejected(self):
        for values in [("1e999999", 10, 0), (1, "1e999999", 0), (1, 1, "1e999999")]:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    calculate_revenue(*values)

    def test_cli_rejects_extreme_input_without_traceback(self):
        script = Path(__file__).resolve().parents[1] / "revenue_calculator.py"
        result = subprocess.run(
            [sys.executable, "-B", str(script), "1e999999", "10", "0"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unit_price", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_caller_context_cannot_erase_small_profit(self):
        with localcontext() as context:
            context.prec = 6
            context.Emax = 9
            context.traps[Inexact] = True
            result = calculate_revenue("1000000.01", 1, "1000000.00")
            self.assertEqual(result.gross_profit, Decimal("0.01"))
            self.assertEqual(context.prec, 6)
            self.assertTrue(context.traps[Inexact])

    def test_float_inputs_are_rejected(self):
        for index in range(3):
            values = [1, 1, 0]
            values[index] = 0.1 + 0.2
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    calculate_revenue(*values)

    def test_repeating_margin_is_rounded(self):
        self.assertEqual(calculate_revenue(3, 1, 2).gross_margin, Decimal("33.3333"))
        self.assertEqual(calculate_revenue(3, 1, 1).gross_margin, Decimal("66.6667"))

    def test_margin_rounds_ties_to_even(self):
        self.assertEqual(calculate_revenue(20000, 1, "19999.99").gross_margin,
                         Decimal("0.0000"))
        self.assertEqual(calculate_revenue(20000, 1, "19999.97").gross_margin,
                         Decimal("0.0002"))

    def test_maximum_inputs_preserve_small_profit(self):
        result = calculate_revenue("1000000000000", "1000000000", "999999999999.99")
        self.assertEqual(result.revenue, Decimal("1000000000000000000000"))
        self.assertEqual(result.gross_profit, Decimal("10000000"))

    def test_input_range_and_scale_limits(self):
        for values in [("1000000000000.01", 1, 0), (1, "1000000000.001", 0),
                       (1, 1, "1000000000000.01"), ("0.001", 1, 0),
                       (1, "0.0001", 0), (1, 1, "0.001")]:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    calculate_revenue(*values)

    def test_minimum_units_and_trailing_zeros(self):
        result = calculate_revenue("0.0100", "0.0010", 0)
        self.assertEqual(result.revenue, Decimal("0.00001"))
        self.assertEqual(result.gross_margin, Decimal("100.0000"))

    def test_input_size_and_bool_are_rejected(self):
        for value in ["0" * 129, Decimal("1." + "0" * 128), True]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    calculate_revenue(value, 1, 0)

    def test_large_negative_margin(self):
        result = calculate_revenue("0.01", "0.001", "1000000000000")
        self.assertEqual(result.gross_margin, Decimal("-9999999999999900.0000"))

    def test_zero_quantity(self):
        result = calculate_revenue(100, 0, 60)
        self.assertEqual(result.revenue, Decimal("0"))
        self.assertEqual(result.total_cost, Decimal("0"))
        self.assertEqual(result.gross_profit, Decimal("0"))
        self.assertIsNone(result.gross_margin)

    def test_zero_price_with_cost(self):
        result = calculate_revenue(0, 5, 2)
        self.assertEqual(result.revenue, Decimal("0"))
        self.assertEqual(result.total_cost, Decimal("10"))
        self.assertEqual(result.gross_profit, Decimal("-10"))
        self.assertIsNone(result.gross_margin)

    def test_negative_inputs(self):
        for values in [(-1, 10, 6), (10, -1, 6), (10, 1, -6)]:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    calculate_revenue(*values)

    def test_loss_is_allowed(self):
        result = calculate_revenue(10, 2, 15)
        self.assertEqual(result.gross_profit, Decimal("-10"))
        self.assertEqual(result.gross_margin, Decimal("-50"))

    def test_fractional_quantity(self):
        result = calculate_revenue("10", "1.5", "4")
        self.assertEqual(result.revenue, Decimal("15"))
        self.assertEqual(result.total_cost, Decimal("6"))
        self.assertEqual(result.gross_margin, Decimal("60"))

    def test_invalid_and_nonfinite_inputs(self):
        for invalid in ["abc", "NaN", "Infinity", "-Infinity"]:
            for index in range(3):
                values = [10, 2, 6]
                values[index] = invalid
                with self.subTest(invalid=invalid, index=index):
                    with self.assertRaises(ValueError):
                        calculate_revenue(*values)


if __name__ == "__main__":
    unittest.main()
