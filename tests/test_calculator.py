"""Unit tests for the yearly-risk / multi-employee deferred-salary model.

The risk adjustment divides the deferred salary by the success probability, so a
20% chance of success means five times the deferred salary.
"""

import unittest

from app.calculator import EmployeeInput, YearInput, calculate


def years(*probabilities):
    return [YearInput(success_probability_pct=p) for p in probabilities]


def employee(name="Ada", start_year=1, fictional=90000, actual=60000):
    return EmployeeInput(
        name=name, start_year=start_year, fictional_gross=fictional, actual_gross=actual
    )


class SingleEmployeeTests(unittest.TestCase):
    def test_one_year_divides_difference_by_probability(self):
        # 30,000 / 0.10 = 300,000
        result = calculate(years(10), [employee()])
        row = result["employees"][0]
        self.assertEqual(row["annual_deferred"], 30000.0)
        self.assertEqual(row["total_deferred"], 30000.0)
        self.assertEqual(row["total_risk_adjusted"], 300000.0)

    def test_twenty_percent_success_is_five_times(self):
        result = calculate(years(20), [employee()])
        self.assertEqual(result["employees"][0]["total_risk_adjusted"], 150000.0)

    def test_risk_differs_per_year(self):
        # Year 1: 10% -> 300,000; Year 2: 50% -> 60,000; Year 3: 100% -> 30,000
        result = calculate(years(10, 50, 100), [employee()])
        row = result["employees"][0]
        self.assertEqual(row["total_deferred"], 90000.0)
        self.assertEqual(row["total_risk_adjusted"], 390000.0)
        self.assertEqual(
            [y["risk_adjusted"] for y in row["by_year"]], [300000.0, 60000.0, 30000.0]
        )

    def test_full_probability_leaves_amount_unchanged(self):
        result = calculate(years(100, 100), [employee()])
        self.assertEqual(result["employees"][0]["total_risk_adjusted"], 60000.0)

    def test_lower_probability_never_decreases_the_amount(self):
        high = calculate(years(80), [employee()])["company"]["total_risk_adjusted"]
        low = calculate(years(5), [employee()])["company"]["total_risk_adjusted"]
        self.assertGreater(low, high)

    def test_fractional_probability(self):
        # 30,000 / 0.125 = 240,000
        result = calculate(years(12.5), [employee()])
        self.assertEqual(result["employees"][0]["total_risk_adjusted"], 240000.0)

    def test_no_deferral_when_salaries_equal(self):
        result = calculate(years(50), [employee(fictional=60000, actual=60000)])
        self.assertEqual(result["employees"][0]["total_deferred"], 0.0)
        self.assertEqual(result["employees"][0]["total_risk_adjusted"], 0.0)


class StartYearTests(unittest.TestCase):
    def test_employee_starting_later_only_counts_from_start_year(self):
        # Starts in year 3 of 4: only years 3 (25% -> 120,000) and 4 (100% -> 30,000).
        result = calculate(years(10, 20, 25, 100), [employee(start_year=3)])
        row = result["employees"][0]
        self.assertEqual(row["years_active"], 2)
        self.assertEqual(row["total_deferred"], 60000.0)
        self.assertEqual(row["total_risk_adjusted"], 150000.0)
        self.assertEqual([y["active"] for y in row["by_year"]], [False, False, True, True])
        self.assertEqual(row["by_year"][0]["deferred"], 0.0)
        self.assertEqual(row["by_year"][0]["risk_adjusted"], 0.0)

    def test_start_year_beyond_timeline_warns_and_counts_nothing(self):
        result = calculate(years(10, 20), [employee(name="Late", start_year=5)])
        row = result["employees"][0]
        self.assertEqual(row["years_active"], 0)
        self.assertEqual(row["total_deferred"], 0.0)
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("Late", result["warnings"][0])


class CompanyTests(unittest.TestCase):
    def setUp(self):
        # Two years at 10% / 40%.
        # Ada:   starts year 1, 90k vs 60k -> 30k/yr -> 30k/0.10 + 30k/0.40 = 375,000
        # Bruno: starts year 2, 120k vs 80k -> 40k/yr -> 40k/0.40 = 100,000
        self.result = calculate(
            years(10, 40),
            [
                employee("Ada", 1, 90000, 60000),
                employee("Bruno", 2, 120000, 80000),
            ],
        )

    def test_per_employee_totals(self):
        ada, bruno = self.result["employees"]
        self.assertEqual(ada["total_deferred"], 60000.0)
        self.assertEqual(ada["total_risk_adjusted"], 375000.0)
        self.assertEqual(bruno["total_deferred"], 40000.0)
        self.assertEqual(bruno["total_risk_adjusted"], 100000.0)

    def test_company_totals_are_sum_of_employees(self):
        company = self.result["company"]
        self.assertEqual(company["total_deferred"], 100000.0)
        self.assertEqual(company["total_risk_adjusted"], 475000.0)
        self.assertEqual(company["employee_count"], 2)
        self.assertEqual(company["year_count"], 2)

    def test_company_per_year(self):
        year1, year2 = self.result["years"]
        self.assertEqual(year1["active_employees"], 1)
        self.assertEqual(year1["deferred"], 30000.0)
        self.assertEqual(year1["risk_adjusted"], 300000.0)
        self.assertEqual(year2["active_employees"], 2)
        self.assertEqual(year2["deferred"], 70000.0)
        # 70,000 / 0.40
        self.assertEqual(year2["risk_adjusted"], 175000.0)

    def test_year_totals_match_company_totals(self):
        years_total = sum(y["risk_adjusted"] for y in self.result["years"])
        self.assertEqual(years_total, self.result["company"]["total_risk_adjusted"])

    def test_no_employees_gives_zero_company(self):
        result = calculate(years(10), [])
        self.assertEqual(result["company"]["total_deferred"], 0.0)
        self.assertEqual(result["company"]["total_risk_adjusted"], 0.0)
        self.assertEqual(result["employees"], [])

    def test_blank_name_gets_default(self):
        result = calculate(years(10), [employee(name="  ")])
        self.assertEqual(result["employees"][0]["name"], "Employee 1")


class ValidationTests(unittest.TestCase):
    def test_requires_a_year(self):
        with self.assertRaises(ValueError):
            calculate([], [employee()])

    def test_probability_must_be_above_zero_and_at_most_100(self):
        for bad in (-1, 0, 101):
            with self.assertRaises(ValueError):
                calculate(years(bad), [employee()])

    def test_zero_probability_message_names_the_year(self):
        with self.assertRaises(ValueError) as caught:
            calculate(years(10, 0), [employee()])
        self.assertIn("Year 2", str(caught.exception))
        self.assertIn("greater than 0", str(caught.exception))

    def test_actual_higher_than_fictional(self):
        with self.assertRaises(ValueError):
            calculate(years(10), [employee(fictional=50000, actual=60000)])

    def test_negative_salary(self):
        with self.assertRaises(ValueError):
            calculate(years(10), [employee(actual=-1)])

    def test_start_year_must_be_positive_whole_number(self):
        for bad in (0, -1, 1.5):
            with self.assertRaises(ValueError):
                calculate(years(10), [employee(start_year=bad)])


if __name__ == "__main__":
    unittest.main()
