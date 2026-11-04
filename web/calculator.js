"use strict";

/* Deferred-salary model (port of app/calculator.py). Runs fully in the browser. */
(function (root) {
  const money = (value) => Math.round((value + Number.EPSILON) * 100) / 100;

  function validate(years, employees) {
    if (!years.length) throw new Error("Add at least one year.");

    years.forEach((year, i) => {
      const p = year.success_probability_pct;
      if (p === null || p === undefined || Number.isNaN(p)) {
        throw new Error(`Year ${i + 1}: success probability is required.`);
      }
      if (!(p > 0 && p <= 100)) {
        throw new Error(
          `Year ${i + 1}: success probability must be greater than 0 and at most 100 percent.`
        );
      }
    });

    employees.forEach((employee, i) => {
      const label = (employee.name || "").trim() || `Employee ${i + 1}`;
      const fields = [
        ["start_year", "start year"],
        ["fictional_gross", "fictional salary"],
        ["actual_gross", "actual salary"],
      ];
      for (const [key, text] of fields) {
        const v = employee[key];
        if (v === null || v === undefined || Number.isNaN(v)) {
          throw new Error(`${label}: ${text} is required.`);
        }
      }
      if (!Number.isInteger(employee.start_year) || employee.start_year < 1) {
        throw new Error(`${label}: start year must be a whole number of 1 or more.`);
      }
      if (employee.fictional_gross < 0 || employee.actual_gross < 0) {
        throw new Error(`${label}: salaries cannot be negative.`);
      }
      if (employee.actual_gross > employee.fictional_gross) {
        throw new Error(`${label}: the actual salary cannot be higher than the fictional salary.`);
      }
    });
  }

  function calculate(payload) {
    const years = payload.years || [];
    const employees = payload.employees || [];
    validate(years, employees);

    const yearTotals = years.map((year, i) => ({
      year: i + 1,
      success_probability_pct: year.success_probability_pct,
      active_employees: 0,
      deferred: 0,
      risk_adjusted: 0,
    }));
    const employeeResults = [];
    const warnings = [];

    employees.forEach((employee, index) => {
      const name = (employee.name || "").trim() || `Employee ${index + 1}`;
      const annualDeferred = employee.fictional_gross - employee.actual_gross;
      const byYear = [];
      let totalDeferred = 0;
      let totalRiskAdjusted = 0;
      let yearsActive = 0;

      years.forEach((year, i) => {
        const number = i + 1;
        const active = number >= employee.start_year;
        const probability = year.success_probability_pct / 100;
        const deferred = active ? annualDeferred : 0;
        const riskAdjusted = deferred / probability;
        if (active) {
          yearsActive += 1;
          totalDeferred += deferred;
          totalRiskAdjusted += riskAdjusted;
          yearTotals[i].active_employees += 1;
          yearTotals[i].deferred += deferred;
          yearTotals[i].risk_adjusted += riskAdjusted;
        }
        byYear.push({
          year: number,
          active,
          success_probability_pct: year.success_probability_pct,
          deferred: money(deferred),
          risk_adjusted: money(riskAdjusted),
        });
      });

      if (yearsActive === 0) {
        warnings.push(
          `${name} starts in year ${employee.start_year}, but only ${years.length} year(s) are defined, so nothing is counted for them.`
        );
      }

      employeeResults.push({
        name,
        start_year: employee.start_year,
        fictional_gross: money(employee.fictional_gross),
        actual_gross: money(employee.actual_gross),
        annual_deferred: money(annualDeferred),
        years_active: yearsActive,
        total_deferred: money(totalDeferred),
        total_risk_adjusted: money(totalRiskAdjusted),
        by_year: byYear,
      });
    });

    yearTotals.forEach((row) => {
      row.deferred = money(row.deferred);
      row.risk_adjusted = money(row.risk_adjusted);
    });

    const sum = (key) => money(employeeResults.reduce((acc, e) => acc + e[key], 0));
    return {
      years: yearTotals,
      employees: employeeResults,
      company: {
        employee_count: employeeResults.length,
        year_count: years.length,
        total_deferred: sum("total_deferred"),
        total_risk_adjusted: sum("total_risk_adjusted"),
      },
      warnings,
    };
  }

  const api = { calculate };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.DeferredSalary = api;
})(typeof window !== "undefined" ? window : globalThis);
