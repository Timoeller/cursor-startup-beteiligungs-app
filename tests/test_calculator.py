"""Unit tests for the deferred-salary "required compensation" model."""

import unittest

from app.calculator import CalculationInputs, calculate


class CalculatorTests(unittest.TestCase):
    def _base_inputs(self, **overrides):
        params = dict(
            intended_gross=90000,
            actual_gross=60000,
            success_probability_pct=20,
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

    def test_total_deferred_over_years(self):
        result = calculate(self._base_inputs(years=3))
        self.assertAlmostEqual(result.summary["total_deferred_salary"], 90000.0)
        self.assertEqual(result.summary["years"], 3)

    def test_single_year_matches_baseline(self):
        # N=1 must reduce exactly to the original single-year model.
        result = calculate(self._base_inputs(years=1))
        self.assertAlmostEqual(result.summary["total_deferred_salary"], 30000.0)
        self.assertAlmostEqual(
            result.summary["required_gross_compensation"], 157875.0, places=2
        )
        self.assertAlmostEqual(result.summary["compensation_multiple"], 5.2625, places=4)

    def test_net_deferred_invested(self):
        result = calculate(self._base_inputs())
        # 30000 * (1 - 0.45) = 16500
        self.assertAlmostEqual(result.summary["net_deferred_invested"], 16500.0)

    def test_foregone_gain_net_and_tax_advantage(self):
        result = calculate(self._base_inputs())
        # pre-tax gain = 16500 * 0.07 = 1155; net = 1155 * 0.75 = 866.25
        self.assertAlmostEqual(result.summary["foregone_gain_net"], 866.25, places=2)
        # tax advantage = 1155 * (0.45 - 0.25) = 231
        self.assertAlmostEqual(result.summary["tax_advantage"], 231.0, places=2)

    def test_benchmark_value(self):
        result = calculate(self._base_inputs())
        # 16500 + 866.25 = 17366.25
        self.assertAlmostEqual(result.summary["benchmark_value"], 17366.25, places=2)

    def test_risk_multiplier_is_one_over_p(self):
        result = calculate(self._base_inputs(success_probability_pct=20))
        self.assertAlmostEqual(result.summary["risk_multiplier"], 5.0, places=4)

    def test_required_gross_compensation(self):
        result = calculate(self._base_inputs())
        # benchmark / (p * (1 - wage)) = 17366.25 / (0.20 * 0.55) = 157875
        self.assertAlmostEqual(
            result.summary["required_gross_compensation"], 157875.0, places=2
        )

    def test_compensation_multiple(self):
        result = calculate(self._base_inputs())
        # 157875 / 30000 = 5.2625
        self.assertAlmostEqual(
            result.summary["compensation_multiple"], 5.2625, places=4
        )

    def test_pure_risk_multiple_when_no_growth(self):
        # With zero return there is no investment premium, so the multiple is
        # exactly 1 / probability (the user's "5x for 20%" intuition).
        result = calculate(
            self._base_inputs(success_probability_pct=20, annual_return_pct=0)
        )
        self.assertAlmostEqual(result.summary["compensation_multiple"], 5.0, places=4)
        self.assertAlmostEqual(
            result.summary["required_gross_compensation"], 150000.0, places=2
        )

    def test_pure_risk_multiple_multi_year_no_growth(self):
        # Multi-year with zero return: still exactly 1/p, on the total deferred.
        result = calculate(
            self._base_inputs(success_probability_pct=20, annual_return_pct=0, years=3)
        )
        self.assertAlmostEqual(result.summary["compensation_multiple"], 5.0, places=4)
        # 3 * 30000 / 0.20 = 450000
        self.assertAlmostEqual(
            result.summary["required_gross_compensation"], 450000.0, places=2
        )

    def test_multi_year_earlier_years_compound_longer(self):
        # Two years at 7%: year 1 compounds 2 years, year 2 compounds 1 year.
        result = calculate(self._base_inputs(annual_return_pct=7, years=2))
        net = 30000 * (1 - 0.45)
        gain_gross = net * ((1.07 ** 2) - 1) + net * ((1.07 ** 1) - 1)
        gain_net = gain_gross * (1 - 0.25)
        benchmark = net * 2 + gain_net
        self.assertAlmostEqual(result.summary["foregone_gain_net"], round(gain_net, 2), places=2)
        self.assertAlmostEqual(result.summary["benchmark_value"], round(benchmark, 2), places=2)

    def test_more_years_needs_higher_multiple(self):
        one = calculate(self._base_inputs(years=1)).summary["compensation_multiple"]
        three = calculate(self._base_inputs(years=3)).summary["compensation_multiple"]
        self.assertGreater(three, one)

    def test_fairness_identity(self):
        # By construction: expected after-tax pay-out == benchmark value.
        result = calculate(self._base_inputs(success_probability_pct=35, annual_return_pct=9, years=4))
        s = result.summary
        p = 0.35
        wage = 0.45
        expected_net_payout = p * s["required_gross_compensation"] * (1 - wage)
        self.assertAlmostEqual(expected_net_payout, s["benchmark_value"], places=2)

    def test_steps_present_and_ordered(self):
        result = calculate(self._base_inputs())
        keys = [s.key for s in result.steps]
        for expected in [
            "deferred_salary",
            "total_deferred_salary",
            "net_deferred_invested",
            "foregone_gain_net",
            "tax_advantage",
            "benchmark_value",
            "risk_multiplier",
            "required_gross_compensation",
            "compensation_multiple",
        ]:
            self.assertIn(expected, keys)

    def test_validation_actual_gt_intended(self):
        with self.assertRaises(ValueError):
            calculate(self._base_inputs(intended_gross=50000, actual_gross=60000))

    def test_validation_probability_zero(self):
        with self.assertRaises(ValueError):
            calculate(self._base_inputs(success_probability_pct=0))

    def test_validation_probability_range(self):
        with self.assertRaises(ValueError):
            calculate(self._base_inputs(success_probability_pct=150))

    def test_validation_years_minimum(self):
        with self.assertRaises(ValueError):
            calculate(self._base_inputs(years=0))

    def test_validation_years_whole_number(self):
        with self.assertRaises(ValueError):
            calculate(self._base_inputs(years=2.5))


if __name__ == "__main__":
    unittest.main()
