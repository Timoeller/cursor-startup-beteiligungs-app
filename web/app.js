"use strict";

/* ------------------------------------------------------------------ */
/* State                                                               */
/* ------------------------------------------------------------------ */

const state = {
  years: [{ success_probability_pct: "10" }],
  employees: [
    { name: "Employee 1", start_year: "1", fictional_gross: "90000", actual_gross: "60000" },
  ],
};

const money = new Intl.NumberFormat(undefined, {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const $ = (id) => document.getElementById(id);

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(props).forEach(([key, value]) => {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  });
  [].concat(children).forEach((child) => node.append(child));
  return node;
}

function formatPercent(value) {
  return `${Number(value)}%`;
}

/* ------------------------------------------------------------------ */
/* Input rendering                                                     */
/* ------------------------------------------------------------------ */

function trimNumber(value) {
  return String(Math.round(value * 100) / 100);
}

function failureText(rawValue) {
  const value = Number(rawValue);
  if (rawValue === "" || Number.isNaN(value)) return "";
  if (value <= 0 || value > 100) return "Must be above 0% and at most 100%";
  return `${trimNumber(100 - value)}% risk of failure \u00b7 \u00d7${trimNumber(100 / value)}`;
}

function renderYears() {
  const list = $("years-list");
  list.replaceChildren();

  state.years.forEach((year, index) => {
    const risk = el("span", { class: "year-row__risk", text: failureText(year.success_probability_pct) });
    const input = el("input", {
      type: "number",
      min: "1",
      max: "100",
      step: "1",
      value: year.success_probability_pct,
      "aria-label": `Year ${index + 1} success probability in percent`,
      oninput: (event) => {
        year.success_probability_pct = event.target.value;
        risk.textContent = failureText(event.target.value);
        scheduleCalculate();
      },
    });

    const isLast = index === state.years.length - 1;
    const remove = el("button", {
      type: "button",
      class: "icon-btn",
      title: "Remove this year",
      "aria-label": `Remove year ${index + 1}`,
      text: "\u00d7",
      onclick: () => {
        state.years.pop();
        renderYears();
        scheduleCalculate();
      },
    });
    remove.disabled = !(isLast && state.years.length > 1);

    list.append(
      el("div", { class: "year-row" }, [
        el("span", { class: "year-row__label", text: `Year ${index + 1}` }),
        el("div", { class: "year-row__field" }, [
          el("div", { class: "suffix-wrap" }, [input, el("span", { text: "%" })]),
          risk,
        ]),
        remove,
      ])
    );
  });
}

function renderEmployees() {
  const list = $("employees-list");
  list.replaceChildren();

  state.employees.forEach((employee, index) => {
    const field = (key, props, className = "") =>
      el("div", { class: className }, [
        el("input", {
          ...props,
          value: employee[key],
          oninput: (event) => {
            employee[key] = event.target.value;
            scheduleCalculate();
          },
        }),
      ]);

    list.append(
      el("div", { class: "employee-grid" }, [
        field("name", { type: "text", placeholder: `Employee ${index + 1}`, "aria-label": "Name" }, "name-cell"),
        field("start_year", { type: "number", min: "1", step: "1", "aria-label": "Start year" }),
        field("fictional_gross", { type: "number", min: "0", step: "1000", "aria-label": "Fictional annual gross salary" }),
        field("actual_gross", { type: "number", min: "0", step: "1000", "aria-label": "Actual annual gross salary" }),
        el("button", {
          type: "button",
          class: "icon-btn",
          title: "Remove employee",
          "aria-label": `Remove ${employee.name || "employee"}`,
          text: "\u00d7",
          onclick: () => {
            state.employees.splice(index, 1);
            renderEmployees();
            scheduleCalculate();
          },
        }),
      ])
    );
  });
}

$("add-year").addEventListener("click", () => {
  const previous = state.years[state.years.length - 1];
  state.years.push({ success_probability_pct: previous ? previous.success_probability_pct : "10" });
  renderYears();
  scheduleCalculate();
});

$("add-employee").addEventListener("click", () => {
  const previous = state.employees[state.employees.length - 1];
  state.employees.push({
    name: `Employee ${state.employees.length + 1}`,
    start_year: "1",
    fictional_gross: previous ? previous.fictional_gross : "90000",
    actual_gross: previous ? previous.actual_gross : "60000",
  });
  renderEmployees();
  scheduleCalculate();
});

/* ------------------------------------------------------------------ */
/* Calculation                                                         */
/* ------------------------------------------------------------------ */

let debounceTimer = null;

function scheduleCalculate() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(calculate, 150);
}

function toNumberOrNull(value) {
  return value === "" || value === null ? null : Number(value);
}

function buildPayload() {
  return {
    years: state.years.map((year) => ({
      success_probability_pct: toNumberOrNull(year.success_probability_pct),
    })),
    employees: state.employees.map((employee) => ({
      name: employee.name,
      start_year: toNumberOrNull(employee.start_year),
      fictional_gross: toNumberOrNull(employee.fictional_gross),
      actual_gross: toNumberOrNull(employee.actual_gross),
    })),
  };
}

function calculate() {
  try {
    const data = window.DeferredSalary.calculate(buildPayload());
    clearError();
    renderResults(data);
  } catch (error) {
    showError(error.message || "Calculation failed.");
  }
}

/* ------------------------------------------------------------------ */
/* Result rendering                                                    */
/* ------------------------------------------------------------------ */

function showError(message) {
  const box = $("error");
  box.textContent = message;
  box.hidden = false;
  $("results").classList.add("is-stale");
}

function clearError() {
  $("error").hidden = true;
  $("results").classList.remove("is-stale");
}

function cell(text, className = "") {
  return el("td", { class: className, text });
}

function renderWarnings(warnings) {
  const box = $("warnings");
  box.replaceChildren(...warnings.map((text) => el("p", { text })));
  box.hidden = warnings.length === 0;
}

function renderResults(data) {
  const { company, employees, years, warnings } = data;

  $("company-deferred").textContent = money.format(company.total_deferred);
  $("company-risk").textContent = money.format(company.total_risk_adjusted);
  renderWarnings(warnings);

  renderEmployeeTable(employees, company);
  renderYearTable(years, company);
  renderBreakdown(employees);
}

function renderEmployeeTable(employees, company) {
  const body = document.querySelector("#employee-table tbody");
  const foot = document.querySelector("#employee-table tfoot");
  body.replaceChildren();
  foot.replaceChildren();

  if (employees.length === 0) {
    body.append(el("tr", {}, [el("td", { class: "empty", colspan: "6", text: "Add an employee to see results." })]));
    return;
  }

  employees.forEach((employee) => {
    body.append(
      el("tr", {}, [
        cell(employee.name),
        cell(employee.start_year, "num"),
        cell(money.format(employee.annual_deferred), "num"),
        cell(employee.years_active, "num"),
        cell(money.format(employee.total_deferred), "num"),
        cell(money.format(employee.total_risk_adjusted), "num"),
      ])
    );
  });

  foot.append(
    el("tr", {}, [
      cell("Company total"),
      cell(""),
      cell(""),
      cell(""),
      cell(money.format(company.total_deferred), "num"),
      cell(money.format(company.total_risk_adjusted), "num"),
    ])
  );
}

function renderYearTable(years, company) {
  const body = document.querySelector("#year-table tbody");
  const foot = document.querySelector("#year-table tfoot");
  body.replaceChildren();
  foot.replaceChildren();

  let accumulated = 0;
  years.forEach((year) => {
    accumulated += year.risk_adjusted;
    body.append(
      el("tr", {}, [
        cell(`Year ${year.year}`),
        cell(formatPercent(year.success_probability_pct), "num"),
        cell(year.active_employees, "num"),
        cell(money.format(year.deferred), "num"),
        cell(money.format(year.risk_adjusted), "num"),
        cell(money.format(accumulated), "num"),
      ])
    );
  });

  foot.append(
    el("tr", {}, [
      cell("Total"),
      cell(""),
      cell(""),
      cell(money.format(company.total_deferred), "num"),
      cell(money.format(company.total_risk_adjusted), "num"),
      cell(money.format(company.total_risk_adjusted), "num"),
    ])
  );
}

function renderBreakdown(employees) {
  const container = $("breakdown");
  const wasOpen = [...container.querySelectorAll("details")].map((node) => node.open);
  container.replaceChildren();

  employees.forEach((employee, index) => {
    const rows = employee.by_year.map((row) =>
      el("tr", { class: row.active ? "" : "inactive" }, [
        cell(`Year ${row.year}`),
        cell(row.active ? formatPercent(row.success_probability_pct) : "\u2013", "num"),
        cell(row.active ? money.format(row.deferred) : "\u2013", "num"),
        cell(row.active ? money.format(row.risk_adjusted) : "\u2013", "num"),
      ])
    );

    const table = el("table", {}, [
      el("thead", {}, [
        el("tr", {}, [
          el("th", { text: "Year" }),
          el("th", { class: "num", text: "Success probability" }),
          el("th", { class: "num", text: "Deferred" }),
          el("th", { class: "num", text: "Risk-adjusted" }),
        ]),
      ]),
      el("tbody", {}, rows),
      el("tfoot", {}, [
        el("tr", {}, [
          cell("Accumulated"),
          cell(""),
          cell(money.format(employee.total_deferred), "num"),
          cell(money.format(employee.total_risk_adjusted), "num"),
        ]),
      ]),
    ]);

    const details = el("details", { class: "person" }, [
      el("summary", {}, [
        el("span", { text: employee.name }),
        el("span", {
          text: `${money.format(employee.total_deferred)} deferred \u2192 ${money.format(employee.total_risk_adjusted)} risk-adjusted`,
        }),
      ]),
      el("div", { class: "table-wrap" }, [table]),
    ]);
    details.open = Boolean(wasOpen[index]);
    container.append(details);
  });
}

/* ------------------------------------------------------------------ */

renderYears();
renderEmployees();
calculate();
