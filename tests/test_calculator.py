"""Unit tests for the yearly-risk / multi-employee deferred-salary model."""

import unittest

from app.calculator import EmployeeInput, YearInput, calculate


def years(*probabilities):
    return [YearInput(success_probability_pct=p) for p in probabilities]


def employee(name="Ada", start_year=1, fictional=90000, actual=60000):
    return EmployeeInput(
        name=name, start_year=start_year, fictional_gross=fictional, actual_gross=actual
    )


class SingleEmployeeTests(unittest.TestCase):
    def test_one_year_applies_probability_to_difference(self):
        result = calculate(years(10), [employee()])
        row = result["employees"][0]
        self.assertEqual(row["annual_deferred"], 30000.0)
        self.assertEqual(row["total_deferred"], 30000.0)
        self.assertEqual(row["total_risk_adjusted"], 3000.0)

    def test_risk_differs_per_year(self):
        # Year 1: 10% -> 3,000; Year 2: 50% -> 15,000; Year 3: 100% -> 30,000
        result = calculate(years(10, 50, 100), [employee()])
        row = result["employees"][0]
        self.assertEqual(row["total_deferred"], 90000.0)
        self.assertEqual(row["total_risk_adjusted"], 48000.0)
        self.assertEqual(
            [y["risk_adjusted"] for y in row["by_year"]], [3000.0, 15000.0, 30000.0]
        )

    def test_zero_probability_counts_nothing(self):
        result = calculate(years(0), [employee()])
        self.assertEqual(result["employees"][0]["total_deferred"], 30000.0)
        self.assertEqual(result["employees"][0]["total_risk_adjusted"], 0.0)

    def test_full_probability_counts_everything(self):
        result = calculate(years(100, 100), [employee()])
        self.assertEqual(result["employees"][0]["total_risk_adjusted"], 60000.0)

    def test_no_deferral_when_salaries_equal(self):
        result = calculate(years(50), [employee(fictional=60000, actual=60000)])
        self.assertEqual(result["employees"][0]["total_deferred"], 0.0)


class StartYearTests(unittest.TestCase):
    def test_employee_starting_later_only_counts_from_start_year(self):
        # Starts in year 3 of 4: only years 3 and 4 count (25% and 100%).
        result = calculate(years(10, 20, 25, 100), [employee(start_year=3)])
        row = result["employees"][0]
        self.assertEqual(row["years_active"], 2)
        self.assertEqual(row["total_deferred"], 60000.0)
        self.assertEqual(row["total_risk_adjusted"], 0.25 * 30000 + 30000)
        self.assertEqual([y["active"] for y in row["by_year"]], [False, False, True, True])
        self.assertEqual(row["by_year"][0]["deferred"], 0.0)

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
        # Ada:   starts year 1, 90k vs 60k -> 30k/yr
        # Bruno: starts year 2, 120k vs 80k -> 40k/yr
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
        self.assertEqual(ada["total_risk_adjusted"], 3000.0 + 12000.0)
        self.assertEqual(bruno["total_deferred"], 40000.0)
        self.assertEqual(bruno["total_risk_adjusted"], 16000.0)

    def test_company_totals_are_sum_of_employees(self):
        company = self.result["company"]
        self.assertEqual(company["total_deferred"], 100000.0)
        self.assertEqual(company["total_risk_adjusted"], 31000.0)
        self.assertEqual(company["employee_count"], 2)
        self.assertEqual(company["year_count"], 2)

    def test_company_per_year(self):
        year1, year2 = self.result["years"]
        self.assertEqual(year1["active_employees"], 1)
        self.assertEqual(year1["deferred"], 30000.0)
        self.assertEqual(year1["risk_adjusted"], 3000.0)
        self.assertEqual(year2["active_employees"], 2)
        self.assertEqual(year2["deferred"], 70000.0)
        self.assertEqual(year2["risk_adjusted"], 28000.0)

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

    def test_probability_out_of_range(self):
        for bad in (-1, 101):
            with self.assertRaises(ValueError):
                calculate(years(bad), [employee()])

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
