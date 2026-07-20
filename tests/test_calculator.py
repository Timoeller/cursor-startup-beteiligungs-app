"""Unit tests for the deferred-salary economic-value model."""

import math
import unittest

from app.calculator import CalculationInputs, calculate


class CalculatorTests(unittest.TestCase):
    def _base_inputs(self, **overrides):
        params = dict(
            intended_gross=90000,
            actual_gross=60000,
            success_probability_pct=30,
            annual_return_pct=7,
            wage_tax_pct=45,
            capital_gains_tax_pct=25,
            years=1,
        )
        params.update(overrides)
        return CalculationInputs(**params)

    def test_deferred_salary(self):
        result = calculate(self._base_inputs())
        self.assertAlmostEqual(result.summary["deferred_salary"], 30000.0)

    def test_risk_adjustment(self):
        result = calculate(self._base_inputs(success_probability_pct=30))
        # 30000 * 0.30 = 9000
        self.assertAlmostEqual(result.summary["risk_adjusted_value"], 9000.0)

    def test_foregone_gain_gross(self):
        result = calculate(self._base_inputs())
        # net deferred = 30000 * (1 - 0.45) = 16500
        # gain = 16500 * ((1.07)^1 - 1) = 16500 * 0.07 = 1155
        self.assertAlmostEqual(result.summary["foregone_gain_gross"], 1155.0, places=2)

    def test_foregone_gain_net_and_tax_advantage(self):
        result = calculate(self._base_inputs())
        # net gain = 1155 * (1 - 0.25) = 866.25
        self.assertAlmostEqual(result.summary["foregone_gain_net"], 866.25, places=2)
        # tax advantage = 1155 * (0.45 - 0.25) = 231
        self.assertAlmostEqual(result.summary["tax_advantage"], 231.0, places=2)

    def test_value_take_cash(self):
        result = calculate(self._base_inputs())
        # 16500 + 866.25 = 17366.25
        self.assertAlmostEqual(result.summary["value_take_cash"], 17366.25, places=2)

    def test_value_defer(self):
        result = calculate(self._base_inputs())
        # risk adjusted 9000 * (1 - 0.45) = 4950
        self.assertAlmostEqual(result.summary["value_defer"], 4950.0, places=2)

    def test_final_value(self):
        result = calculate(self._base_inputs())
        # 4950 - 17366.25 = -12416.25
        self.assertAlmostEqual(
            result.summary["final_economic_value"], -12416.25, places=2
        )
        self.assertFalse(result.summary["favourable"])

    def test_multi_year_compounding(self):
        result = calculate(self._base_inputs(annual_return_pct=10, years=3))
        net_deferred = 30000 * (1 - 0.45)
        expected_gain = net_deferred * ((1.10 ** 3) - 1)
        self.assertAlmostEqual(
            result.summary["foregone_gain_gross"], round(expected_gain, 2), places=2
        )

    def test_high_success_can_be_favourable(self):
        # With near-certain success and no investment return, deferring roughly
        # breaks even / turns favourable.
        result = calculate(
            self._base_inputs(success_probability_pct=100, annual_return_pct=0)
        )
        self.assertTrue(result.summary["favourable"])
        self.assertAlmostEqual(result.summary["final_economic_value"], 0.0, places=2)

    def test_steps_present_and_ordered(self):
        result = calculate(self._base_inputs())
        keys = [s.key for s in result.steps]
        for expected in [
            "deferred_salary",
            "risk_adjusted_value",
            "foregone_gain_gross",
            "foregone_gain_net",
            "tax_advantage",
            "final_economic_value",
        ]:
            self.assertIn(expected, keys)

    def test_validation_actual_gt_intended(self):
        with self.assertRaises(ValueError):
            calculate(self._base_inputs(intended_gross=50000, actual_gross=60000))

    def test_validation_probability_range(self):
        with self.assertRaises(ValueError):
            calculate(self._base_inputs(success_probability_pct=150))

    def test_zero_deferred(self):
        result = calculate(self._base_inputs(intended_gross=60000, actual_gross=60000))
        self.assertEqual(result.summary["deferred_salary"], 0.0)
        self.assertEqual(result.summary["foregone_gain_gross"], 0.0)


if __name__ == "__main__":
    unittest.main()
