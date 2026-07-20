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

/* --------------------------- Rendering -------------------------- */
function renderSummary(data) {
  const s = data.summary;

  const headlineValue = document.getElementById("headline-value");
  headlineValue.textContent = currencyPrecise.format(s.final_economic_value);

  const note = document.getElementById("headline-note");
  if (s.favourable) {
    note.textContent = "Deferring is favourable versus taking the cash and investing it.";
  } else {
    note.textContent = "Deferring costs you money versus taking the cash and investing it.";
  }

  document.getElementById("s-deferred").textContent = currency.format(s.deferred_salary);
  document.getElementById("s-risk").textContent = currency.format(s.risk_adjusted_value);
  document.getElementById("s-foregone").textContent = currency.format(s.foregone_gain_gross);
  document.getElementById("s-taxeffect").textContent = currency.format(s.foregone_gain_net);

  document.getElementById("c-cash").textContent = currency.format(s.value_take_cash);
  document.getElementById("c-defer").textContent = currency.format(s.value_defer);
}

function renderDetails(data) {
  const list = document.getElementById("steps");
  list.innerHTML = "";
  data.steps.forEach((step) => {
    const li = document.createElement("li");
    const value = currencyPrecise.format(step.value);
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
