"""Deferred-salary model: per-year risk, per-employee start year, company totals.

The model is deliberately small.

* The company runs for one or more **years** (year 1, year 2, ...). Each year has
  its own **startup success probability**.
* Each **employee** has a start year, a **fictional** (intended) annual gross
  salary and the **actual** annual gross salary that is really paid. The same two
  salaries apply in every year from the start year onwards.

For every employee and every year in which they are employed::

    deferred      = fictional_gross - actual_gross
    risk_adjusted = deferred / success_probability(year)

The deferred salary is only paid out if the startup succeeds, so to compensate for
that risk the amount has to be divided by the success probability (20% success
means 5 times the deferred salary). Because of this the probability must be
greater than zero.

Both values are accumulated per employee over all their years, and then summed
over all employees to give the company totals. Investment returns and taxes are
intentionally not part of the model.

All salary figures are ANNUAL GROSS amounts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class YearInput:
    """One year of the company timeline."""

    success_probability_pct: float


@dataclass
class EmployeeInput:
    """One employee on the deferred-salary plan."""

    name: str
    start_year: int
    fictional_gross: float
    actual_gross: float


def _money(value: float) -> float:
    """Round to whole cents to avoid floating-point noise."""

    return round(value, 2)


def validate(years: list[YearInput], employees: list[EmployeeInput]) -> None:
    """Raise ``ValueError`` with a user-readable message for invalid input."""

    if not years:
        raise ValueError("Add at least one year.")

    for index, year in enumerate(years, start=1):
        if not 0 < year.success_probability_pct <= 100:
            raise ValueError(
                f"Year {index}: success probability must be greater than 0 and "
                "at most 100 percent."
            )

    for employee in employees:
        label = employee.name or "Employee"
        if employee.start_year != int(employee.start_year) or employee.start_year < 1:
            raise ValueError(f"{label}: start year must be a whole number of 1 or more.")
        if employee.fictional_gross < 0 or employee.actual_gross < 0:
            raise ValueError(f"{label}: salaries cannot be negative.")
        if employee.actual_gross > employee.fictional_gross:
            raise ValueError(
                f"{label}: the actual salary cannot be higher than the fictional salary."
            )


def calculate(years: list[YearInput], employees: list[EmployeeInput]) -> dict[str, Any]:
    """Run the model and return a JSON-serialisable result.

    Result layout::

        {
          "years":     [{"year", "success_probability_pct", "active_employees",
                         "deferred", "risk_adjusted"}, ...],   # company per year
        "employees": [{"name", "start_year", "fictional_gross", "actual_gross",
                         "annual_deferred", "years_active", "total_deferred",
                         "total_risk_adjusted",
                         "by_year": [{"year", "active", "success_probability_pct",
                                      "deferred", "risk_adjusted"}, ...]}, ...],
          "company":   {"employee_count", "year_count", "total_deferred",
                         "total_risk_adjusted"},
          "warnings":  [str, ...]
        }
    """

    validate(years, employees)

    year_totals = [
        {
            "year": number,
            "success_probability_pct": year.success_probability_pct,
            "active_employees": 0,
            "deferred": 0.0,
            "risk_adjusted": 0.0,
        }
        for number, year in enumerate(years, start=1)
    ]

    employee_results: list[dict[str, Any]] = []
    warnings: list[str] = []

    for position, employee in enumerate(employees, start=1):
        name = employee.name.strip() or f"Employee {position}"
        annual_deferred = employee.fictional_gross - employee.actual_gross

        by_year: list[dict[str, Any]] = []
        total_deferred = 0.0
        total_risk_adjusted = 0.0
        years_active = 0

        for number, year in enumerate(years, start=1):
            active = number >= employee.start_year
            probability = year.success_probability_pct / 100.0
            deferred = annual_deferred if active else 0.0
            risk_adjusted = deferred / probability

            if active:
                years_active += 1
                total_deferred += deferred
                total_risk_adjusted += risk_adjusted
                year_totals[number - 1]["active_employees"] += 1
                year_totals[number - 1]["deferred"] += deferred
                year_totals[number - 1]["risk_adjusted"] += risk_adjusted

            by_year.append(
                {
                    "year": number,
                    "active": active,
                    "success_probability_pct": year.success_probability_pct,
                    "deferred": _money(deferred),
                    "risk_adjusted": _money(risk_adjusted),
                }
            )

        if years_active == 0:
            warnings.append(
                f"{name} starts in year {int(employee.start_year)}, but only "
                f"{len(years)} year(s) are defined, so nothing is counted for them."
            )

        employee_results.append(
            {
                "name": name,
                "start_year": int(employee.start_year),
                "fictional_gross": _money(employee.fictional_gross),
                "actual_gross": _money(employee.actual_gross),
                "annual_deferred": _money(annual_deferred),
                "years_active": years_active,
                "total_deferred": _money(total_deferred),
                "total_risk_adjusted": _money(total_risk_adjusted),
                "by_year": by_year,
            }
        )

    for row in year_totals:
        row["deferred"] = _money(row["deferred"])
        row["risk_adjusted"] = _money(row["risk_adjusted"])

    company = {
        "employee_count": len(employee_results),
        "year_count": len(years),
        "total_deferred": _money(sum(e["total_deferred"] for e in employee_results)),
        "total_risk_adjusted": _money(
            sum(e["total_risk_adjusted"] for e in employee_results)
        ),
    }

    return {
        "years": year_totals,
        "employees": employee_results,
        "company": company,
        "warnings": warnings,
    }
