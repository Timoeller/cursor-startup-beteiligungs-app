"""Economic-value model for deferred startup salary.

The model answers a single employee-side question:

    "My real (intended) gross salary is higher than what the startup actually
     pays me. The difference is deferred and I only get it back if the startup
     succeeds. What is that arrangement really worth to me, once I account for
     risk, the opportunity cost of not investing the money, and taxes?"

Everything in this module is intentionally explicit and side-effect free so the
model is easy to read, unit-test and extend. Each calculation step is returned
as a structured record (label + formula + value + explanation) so the frontend
can render a fully transparent, step-by-step breakdown.

All salary figures are ANNUAL GROSS amounts. Monthly salary is never used.

Sign convention for the final economic value
---------------------------------------------
The final value compares two worlds:

  * World A - "Take the cash":  you receive the deferred portion as normal
    salary now, pay wage tax on it, and invest the net amount. Investment gains
    are taxed at the (lower) capital-gains rate.

  * World B - "Defer the salary": you receive nothing now. You only get the
    deferred amount back (taxed as wage income) if the startup succeeds, which
    happens with the given success probability. The money cannot grow in the
    meantime.

    final_economic_value = value(World B) - value(World A)

A negative number therefore means the deferral costs you money relative to
simply taking the cash and investing it; a positive number means it is
favourable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Default modelling assumptions (all configurable / easy to extend)
# ---------------------------------------------------------------------------

DEFAULT_WAGE_TAX_PCT = 45.0          # top marginal wage/income tax rate
DEFAULT_CAPITAL_GAINS_TAX_PCT = 25.0  # flat capital-gains tax on investment gains
DEFAULT_YEARS = 1.0                   # investment / deferral horizon in years


@dataclass
class CalculationInputs:
    """Validated inputs for a single calculation.

    Attributes
    ----------
    intended_gross:
        Intended (real) annual gross salary.
    actual_gross:
        Annual gross salary actually paid out.
    success_probability_pct:
        Probability the startup succeeds and repays the deferred salary, in
        percent (0-100). This is the ONLY risk-adjustment input.
    annual_return_pct:
        Expected annual investment return, in percent.
    wage_tax_pct:
        Marginal wage/income tax rate applied to salary, in percent.
    capital_gains_tax_pct:
        Capital-gains tax rate applied to investment gains, in percent.
    years:
        Investment / deferral horizon in years.
    """

    intended_gross: float
    actual_gross: float
    success_probability_pct: float
    annual_return_pct: float
    wage_tax_pct: float = DEFAULT_WAGE_TAX_PCT
    capital_gains_tax_pct: float = DEFAULT_CAPITAL_GAINS_TAX_PCT
    years: float = DEFAULT_YEARS

    def validate(self) -> None:
        """Raise ``ValueError`` if any input is out of range."""

        if self.intended_gross < 0:
            raise ValueError("Intended annual gross salary cannot be negative.")
        if self.actual_gross < 0:
            raise ValueError("Actual annual gross salary cannot be negative.")
        if self.actual_gross > self.intended_gross:
            raise ValueError(
                "Actual salary paid cannot be higher than the intended salary; "
                "there would be no deferred compensation."
            )
        if not 0 <= self.success_probability_pct <= 100:
            raise ValueError("Success probability must be between 0 and 100 percent.")
        if self.annual_return_pct < -100:
            raise ValueError("Annual investment return cannot be below -100 percent.")
        if not 0 <= self.wage_tax_pct <= 100:
            raise ValueError("Wage tax rate must be between 0 and 100 percent.")
        if not 0 <= self.capital_gains_tax_pct <= 100:
            raise ValueError("Capital-gains tax rate must be between 0 and 100 percent.")
        if self.years < 0:
            raise ValueError("Investment horizon (years) cannot be negative.")


@dataclass
class Step:
    """A single, human-readable calculation step for the detailed breakdown."""

    key: str
    label: str
    value: float
    formula: str
    substitution: str
    explanation: str
    unit: str = "currency"

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "formula": self.formula,
            "substitution": self.substitution,
            "explanation": self.explanation,
            "unit": self.unit,
        }


@dataclass
class CalculationResult:
    """Full result: headline summary + ordered, transparent breakdown."""

    summary: dict[str, Any] = field(default_factory=dict)
    steps: list[Step] = field(default_factory=list)
    assumptions: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "steps": [step.as_dict() for step in self.steps],
            "assumptions": self.assumptions,
            "inputs": self.inputs,
        }


def _money(value: float) -> float:
    """Round to whole cents to avoid noisy floating-point tails."""

    return round(value, 2)


def calculate(inputs: CalculationInputs) -> CalculationResult:
    """Run the full deferred-salary economic-value model.

    Returns a :class:`CalculationResult` with a headline summary and an ordered
    list of transparent steps that mirror the required output breakdown:
    deferred salary, risk-adjusted expected value, foregone investment gains,
    tax-adjusted investment effect and the final estimated economic value.
    """

    inputs.validate()

    # Convert percentages to fractions once, up front.
    p = inputs.success_probability_pct / 100.0
    r = inputs.annual_return_pct / 100.0
    t_wage = inputs.wage_tax_pct / 100.0
    t_cg = inputs.capital_gains_tax_pct / 100.0
    n = inputs.years

    steps: list[Step] = []

    # -- Step 1: Deferred salary (gross) ----------------------------------
    deferred = inputs.intended_gross - inputs.actual_gross
    steps.append(
        Step(
            key="deferred_salary",
            label="Deferred salary (annual, gross)",
            value=_money(deferred),
            formula="deferred = intended_gross - actual_gross",
            substitution=(
                f"{inputs.intended_gross:,.2f} - {inputs.actual_gross:,.2f} "
                f"= {deferred:,.2f}"
            ),
            explanation=(
                "The part of your intended annual gross salary that you are not "
                "actually being paid. This is the amount treated as deferred "
                "compensation."
            ),
        )
    )

    # -- Step 2: Risk-adjusted expected value (gross) ---------------------
    risk_adjusted = deferred * p
    steps.append(
        Step(
            key="risk_adjusted_value",
            label="Risk-adjusted expected value (gross)",
            value=_money(risk_adjusted),
            formula="risk_adjusted = deferred * success_probability",
            substitution=f"{deferred:,.2f} x {p:.4f} = {risk_adjusted:,.2f}",
            explanation=(
                "You only get the deferred salary back if the startup succeeds. "
                "Weighting by the success probability gives the expected gross "
                "amount you can realistically expect to recover."
            ),
        )
    )

    # -- Step 3: Net deferred salary (the amount you could invest) --------
    # World A alternative: had you received the deferred salary, you would pay
    # wage tax on it and invest what is left.
    net_deferred = deferred * (1 - t_wage)
    steps.append(
        Step(
            key="net_deferred_salary",
            label="Net deferred salary available to invest",
            value=_money(net_deferred),
            formula="net_deferred = deferred * (1 - wage_tax)",
            substitution=f"{deferred:,.2f} x (1 - {t_wage:.2f}) = {net_deferred:,.2f}",
            explanation=(
                "If you had been paid the deferred salary instead, wage tax would "
                "apply first. Only the net amount could actually be invested."
            ),
        )
    )

    # -- Step 4: Foregone investment gains (pre-tax) ----------------------
    growth_factor = (1 + r) ** n
    foregone_gain_gross = net_deferred * (growth_factor - 1)
    steps.append(
        Step(
            key="foregone_gain_gross",
            label="Foregone investment gains (pre-tax)",
            value=_money(foregone_gain_gross),
            formula="gain_gross = net_deferred * ((1 + return)^years - 1)",
            substitution=(
                f"{net_deferred:,.2f} x ((1 + {r:.4f})^{n:g} - 1) "
                f"= {foregone_gain_gross:,.2f}"
            ),
            explanation=(
                "The investment growth you give up by not having the net deferred "
                "salary in hand to invest over the horizon. This is the core "
                "opportunity cost of deferring."
            ),
        )
    )

    # -- Step 5: Tax-adjusted investment effect ---------------------------
    # Investment gains are taxed at the (lower) capital-gains rate, not the
    # (higher) wage-tax rate. That difference is the tax advantage of earning
    # money via investment gains rather than as additional salary.
    foregone_gain_net = foregone_gain_gross * (1 - t_cg)
    tax_advantage = foregone_gain_gross * (t_wage - t_cg)
    steps.append(
        Step(
            key="foregone_gain_net",
            label="Foregone investment gains (after 25% capital-gains tax)",
            value=_money(foregone_gain_net),
            formula="gain_net = gain_gross * (1 - capital_gains_tax)",
            substitution=(
                f"{foregone_gain_gross:,.2f} x (1 - {t_cg:.2f}) "
                f"= {foregone_gain_net:,.2f}"
            ),
            explanation=(
                "Investment gains are taxed at the capital-gains rate. This is the "
                "net growth you actually forgo by deferring."
            ),
        )
    )
    steps.append(
        Step(
            key="tax_advantage",
            label="Tax advantage: investment vs. salary taxation",
            value=_money(tax_advantage),
            formula="tax_advantage = gain_gross * (wage_tax - capital_gains_tax)",
            substitution=(
                f"{foregone_gain_gross:,.2f} x ({t_wage:.2f} - {t_cg:.2f}) "
                f"= {tax_advantage:,.2f}"
            ),
            explanation=(
                "Money earned as investment gains is taxed at the capital-gains "
                "rate instead of the higher marginal wage-tax rate. This is how "
                "much extra tax you would have paid if the same gain had been "
                "taxed as salary - i.e. the tax advantage of the investment route."
            ),
        )
    )

    # -- World A vs World B: the two comparison scenarios ------------------
    # World A - take the cash and invest it: keep the net principal plus the
    # after-tax investment gains.
    value_take_cash = net_deferred + foregone_gain_net
    steps.append(
        Step(
            key="value_take_cash",
            label="Value if you take the cash and invest it (World A)",
            value=_money(value_take_cash),
            formula="value_A = net_deferred + gain_net",
            substitution=(
                f"{net_deferred:,.2f} + {foregone_gain_net:,.2f} "
                f"= {value_take_cash:,.2f}"
            ),
            explanation=(
                "Your end wealth in the alternative world: the net deferred salary "
                "you keep plus its after-tax investment growth."
            ),
        )
    )

    # World B - defer: you only recover the (wage-taxed) deferred salary if the
    # startup succeeds, and it cannot grow in the meantime.
    expected_net_repayment = risk_adjusted * (1 - t_wage)
    value_defer = expected_net_repayment
    steps.append(
        Step(
            key="value_defer",
            label="Value if you defer the salary (World B)",
            value=_money(value_defer),
            formula="value_B = risk_adjusted * (1 - wage_tax)",
            substitution=(
                f"{risk_adjusted:,.2f} x (1 - {t_wage:.2f}) = {value_defer:,.2f}"
            ),
            explanation=(
                "Your expected end wealth if you defer: the risk-adjusted deferred "
                "salary, taxed as wage income when it is finally repaid, with no "
                "investment growth in the meantime."
            ),
        )
    )

    # -- Step 6: Final estimated economic value ---------------------------
    final_value = value_defer - value_take_cash
    steps.append(
        Step(
            key="final_economic_value",
            label="Final estimated economic value of deferring",
            value=_money(final_value),
            formula="final_value = value_B - value_A",
            substitution=(
                f"{value_defer:,.2f} - {value_take_cash:,.2f} = {final_value:,.2f}"
            ),
            explanation=(
                "The net economic value of accepting deferred salary compared with "
                "taking the cash and investing it. Negative means deferring costs "
                "you money; positive means it is favourable."
            ),
        )
    )

    summary = {
        "deferred_salary": _money(deferred),
        "risk_adjusted_value": _money(risk_adjusted),
        "foregone_gain_gross": _money(foregone_gain_gross),
        "foregone_gain_net": _money(foregone_gain_net),
        "tax_advantage": _money(tax_advantage),
        "value_take_cash": _money(value_take_cash),
        "value_defer": _money(value_defer),
        "final_economic_value": _money(final_value),
        "favourable": final_value >= 0,
    }

    assumptions = {
        "wage_tax_pct": inputs.wage_tax_pct,
        "capital_gains_tax_pct": inputs.capital_gains_tax_pct,
        "years": inputs.years,
        "notes": [
            "All salary figures are annual gross amounts (monthly salary is never used).",
            "Startup success probability is the only risk-adjustment input.",
            "Deferred salary, when repaid, is taxed as wage income.",
            "Investment gains are taxed at the capital-gains rate (default 25%).",
            "Wage/income tax uses the top marginal rate (default up to 45%).",
        ],
    }

    inputs_echo = {
        "intended_gross": inputs.intended_gross,
        "actual_gross": inputs.actual_gross,
        "success_probability_pct": inputs.success_probability_pct,
        "annual_return_pct": inputs.annual_return_pct,
    }

    return CalculationResult(
        summary=summary,
        steps=steps,
        assumptions=assumptions,
        inputs=inputs_echo,
    )
