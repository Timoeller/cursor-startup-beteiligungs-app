"use strict";

const form = document.getElementById("calc-form");
const errorEl = document.getElementById("error");

const currency = new Intl.NumberFormat(undefined, {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});
const currencyPrecise = new Intl.NumberFormat(undefined, {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 2,
});

/* ----------------------------- Tabs ----------------------------- */
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("is-active"));
    document.querySelectorAll(".tab-panel").forEach((p) => {
      p.classList.remove("is-active");
      p.hidden = true;
    });
    tab.classList.add("is-active");
    const panel = document.getElementById("tab-" + tab.dataset.tab);
    panel.classList.add("is-active");
    panel.hidden = false;
  });
});

/* --------------------------- Helpers ---------------------------- */
function readInputs() {
  const fields = [
    "intended_gross",
    "actual_gross",
    "success_probability_pct",
    "annual_return_pct",
    "wage_tax_pct",
    "capital_gains_tax_pct",
    "years",
  ];
  const payload = {};
  fields.forEach((f) => {
    const el = document.getElementById(f);
    payload[f] = el.value === "" ? null : Number(el.value);
  });
  return payload;
}

function signedClass(value) {
  return value >= 0 ? "value-positive" : "value-negative";
}

function formatMultiplier(value) {
  return `${value.toFixed(2)}×`;
}

function formatByUnit(value, unit) {
  return unit === "multiplier" ? formatMultiplier(value) : currencyPrecise.format(value);
}

/* --------------------------- Rendering -------------------------- */
function renderSummary(data) {
  const s = data.summary;

  document.getElementById("headline-value").textContent = currencyPrecise.format(
    s.required_gross_compensation
  );

  const yearWord = s.years === 1 ? "year" : "years";
  document.getElementById("headline-note").textContent =
    `That is ${formatMultiplier(s.compensation_multiple)} the total deferred salary of ` +
    `${currency.format(s.total_deferred_salary)} over ${s.years} ${yearWord}, ` +
    `paid only if the startup succeeds.`;

  document.getElementById("s-deferred").textContent = currency.format(s.deferred_salary);
  document.getElementById("s-total-label").textContent =
    `Total deferred over ${s.years} ${yearWord} (gross)`;
  document.getElementById("s-total").textContent = currency.format(s.total_deferred_salary);
  document.getElementById("s-risk").textContent = formatMultiplier(s.risk_multiplier);
  document.getElementById("s-multiple").textContent = formatMultiplier(s.compensation_multiple);

  document.getElementById("c-netinvest").textContent = currency.format(s.net_deferred_invested);
  document.getElementById("c-foregone").textContent = currency.format(s.foregone_gain_net);
  document.getElementById("c-taxadv").textContent = currency.format(s.tax_advantage);
  document.getElementById("c-benchmark").textContent = currency.format(s.benchmark_value);
}

function renderDetails(data) {
  const list = document.getElementById("steps");
  list.innerHTML = "";
  data.steps.forEach((step) => {
    const li = document.createElement("li");
    const value = formatByUnit(step.value, step.unit);
    li.innerHTML = `
      <div class="step__head">
        <span class="step__label">${escapeHtml(step.label)}</span>
        <span class="step__value ${signedClass(step.value)}">${value}</span>
      </div>
      <div class="step__formula">${escapeHtml(step.formula)}</div>
      <div class="step__sub">${escapeHtml(step.substitution)}</div>
      <p class="step__explain">${escapeHtml(step.explanation)}</p>
    `;
    list.appendChild(li);
  });

  const assumptions = document.getElementById("assumptions");
  assumptions.innerHTML = "";
  const a = data.assumptions;
  const meta = [
    `Marginal wage/income tax: ${a.wage_tax_pct}%`,
    `Capital-gains tax: ${a.capital_gains_tax_pct}%`,
    `Investment / deferral horizon: ${a.years} year(s)`,
  ];
  meta.concat(a.notes).forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    assumptions.appendChild(li);
  });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/* --------------------------- Calculate -------------------------- */
async function calculate() {
  errorEl.hidden = true;
  const payload = readInputs();
  try {
    const res = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Calculation failed.");
    }
    renderSummary(data);
    renderDetails(data);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.hidden = false;
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  calculate();
});

// Calculate once on load so the user immediately sees a worked example.
calculate();
