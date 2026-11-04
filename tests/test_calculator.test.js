"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { calculate } = require("../web/calculator.js");

test("README example", () => {
  const r = calculate({
    years: [10, 50, 100].map((p) => ({ success_probability_pct: p })),
    employees: [
      { name: "Ada", start_year: 1, fictional_gross: 90000, actual_gross: 60000 },
      { name: "Bruno", start_year: 2, fictional_gross: 120000, actual_gross: 80000 },
    ],
  });
  assert.equal(r.employees[0].total_risk_adjusted, 390000);
  assert.equal(r.employees[1].total_risk_adjusted, 120000);
  assert.equal(r.company.total_deferred, 170000);
  assert.equal(r.company.total_risk_adjusted, 510000);
});

test("rejects zero probability and actual > fictional", () => {
  const emp = { name: "A", start_year: 1, fictional_gross: 10, actual_gross: 5 };
  assert.throws(() => calculate({ years: [{ success_probability_pct: 0 }], employees: [emp] }));
  assert.throws(() =>
    calculate({
      years: [{ success_probability_pct: 50 }],
      employees: [{ ...emp, actual_gross: 20 }],
    })
  );
});

test("late start warns", () => {
  const r = calculate({
    years: [{ success_probability_pct: 50 }],
    employees: [{ name: "A", start_year: 3, fictional_gross: 10, actual_gross: 5 }],
  });
  assert.equal(r.warnings.length, 1);
});
