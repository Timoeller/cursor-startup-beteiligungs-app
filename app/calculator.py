"""Economic-value model for deferred startup salary.

The model answers a single employee-side question:

    "My real (intended) gross salary is higher than what the startup actually
     pays me. The difference is deferred and I only get it back if the startup
     succeeds. How large must that deferred pay-out be so that accepting it is
     *equivalent* to a person who received the same money as salary on day one
     and invested it?"

In other words, we do NOT compare "having the money vs. not having it". We take
the deferral as a given and compute the **fair required deferred compensation**:
the gross amount the startup must promise (payable only on success) to make the
employee whole for (a) the risk that the startup fails and (b) the investment
growth they give up by not receiving the cash today.

Core intuition
--------------
If the startup only succeeds with probability ``p`` (say 20%), then the promised
pay-out must be about ``1 / p`` times larger (5x) just to break even on risk in
expectation. On top of that, the employee loses the tax-advantaged investment
growth they could have earned on the cash, so a further premium is required.

Everything here is intentionally explicit and side-effect free so the model is
easy to read, unit-test and extend. Each step is returned as a structured record
(label + formula + value + explanation) so the frontend can render a fully
transparent, step-by-step breakdown.

All salary figures are ANNUAL GROSS amounts. Monthly salary is never used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Default modelling assumptions (all configurable / easy to extend)
# ---------------------------------------------------------------------------

DEFAULT_WAGE_TAX_PCT = 45.0           # top marginal wage/income tax rate
DEFAULT_CAPITAL_GAINS_TAX_PCT = 25.0  # flat capital-gains tax on investment gains
DEFAULT_YEARS = 1.0                   # investment horizon of the day-one investor


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
        Investment horizon in years of the day-one investor benchmark.
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
        # A zero success probability would require an infinite pay-out to
        # compensate for the risk, which is not a meaningful figure.
        if not 0 < self.success_probability_pct <= 100:
            raise ValueError(
                "Success probability must be greater than 0 and at most 100 percent."
            )
        if self.annual_return_pct < -100:
            raise ValueError("Annual investment return cannot be below -100 percent.")
        if not 0 <= self.wage_tax_pct < 100:
            raise ValueError("Wage tax rate must be between 0 and (below) 100 percent.")
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
    unit: str = "currency"  # "currency" or "multiplier"

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


def _mult(value: float) -> float:
    """Round a multiplier to 4 decimals."""

    return round(value, 4)


def calculate(inputs: CalculationInputs) -> CalculationResult:
    """Run the deferred-salary "required compensation" model.

    Returns a :class:`CalculationResult` with a headline summary and an ordered
    list of transparent steps:

    1. Deferred salary (the annual shortfall).
    2. Net amount a day-one earner could invest (after wage tax).
    3. Foregone investment gains (net of capital-gains tax) - what the cash would
       have grown into.
    4. Benchmark value: the end wealth of someone paid on day one who invests.
    5. Risk-compensation multiplier (1 / success probability).
    6. Required gross deferred compensation (payable only on success).
    7. Compensation multiple vs. the nominal deferred salary.
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
                "compensation and the basis for everything below."
            ),
        )
    )

    # -- Step 2: Net amount a day-one earner could invest -----------------
    net_deferred = deferred * (1 - t_wage)
    steps.append(
        Step(
            key="net_deferred_invested",
            label="Net amount investable on day one (after wage tax)",
            value=_money(net_deferred),
            formula="net_invested = deferred * (1 - wage_tax)",
            substitution=f"{deferred:,.2f} x (1 - {t_wage:.2f}) = {net_deferred:,.2f}",
            explanation=(
                "The benchmark is a colleague who is actually paid this salary on "
                "day one. They pay wage tax first and can invest what is left."
            ),
        )
    )

    # -- Step 3: Foregone investment gains (net of capital-gains tax) ------
    growth_factor = (1 + r) ** n
    gain_gross = net_deferred * (growth_factor - 1)
    gain_net = gain_gross * (1 - t_cg)
    tax_advantage = gain_gross * (t_wage - t_cg)
    steps.append(
        Step(
            key="foregone_gain_net",
            label="Foregone investment gains (after capital-gains tax)",
            value=_money(gain_net),
            formula="gain_net = net_invested * ((1 + return)^years - 1) * (1 - capital_gains_tax)",
            substitution=(
                f"{net_deferred:,.2f} x ((1 + {r:.4f})^{n:g} - 1) x (1 - {t_cg:.2f}) "
                f"= {gain_net:,.2f}"
            ),
            explanation=(
                "The investment growth the day-one earner enjoys and you give up. "
                "Investment gains are taxed at the (lower) capital-gains rate, not "
                "the wage-tax rate - a tax advantage of the investment route."
            ),
        )
    )
    steps.append(
        Step(
            key="tax_advantage",
            label="Tax advantage of gains vs. salary taxation",
            value=_money(tax_advantage),
            formula="tax_advantage = gain_pretax * (wage_tax - capital_gains_tax)",
            substitution=(
                f"{gain_gross:,.2f} x ({t_wage:.2f} - {t_cg:.2f}) = {tax_advantage:,.2f}"
            ),
            explanation=(
                "How much more the investment growth would be taxed if it were "
                "treated as salary instead of capital gains. This tax gap is part "
                "of what the deferred pay-out must make up for."
            ),
        )
    )

    # -- Step 4: Benchmark end wealth of the day-one investor -------------
    benchmark_value = net_deferred + gain_net
    steps.append(
        Step(
            key="benchmark_value",
            label="Benchmark value if paid & invested on day one",
            value=_money(benchmark_value),
            formula="benchmark = net_invested + gain_net",
            substitution=f"{net_deferred:,.2f} + {gain_net:,.2f} = {benchmark_value:,.2f}",
            explanation=(
                "The end wealth of the colleague who was paid on day one: their net "
                "salary plus its after-tax investment growth. Your deferred pay-out "
                "must be worth at least this much in expectation."
            ),
        )
    )

    # -- Step 5: Risk-compensation multiplier ----------------------------
    risk_multiplier = 1 / p
    steps.append(
        Step(
            key="risk_multiplier",
            label="Risk-compensation multiplier (1 / success probability)",
            value=_mult(risk_multiplier),
            unit="multiplier",
            formula="risk_multiplier = 1 / success_probability",
            substitution=f"1 / {p:.4f} = {risk_multiplier:,.4f}",
            explanation=(
                "Because the pay-out only happens if the startup succeeds, its "
                "promised size must be scaled up by 1 / probability so the expected "
                "value is fair. E.g. a 20% chance requires a 5x pay-out."
            ),
        )
    )

    # -- Step 6: Required gross deferred compensation --------------------
    # We need the expected, after-wage-tax pay-out to equal the benchmark value:
    #     p * required_gross * (1 - t_wage) = benchmark_value
    # Solving for required_gross gives the risk gross-up (1/p) and the wage-tax
    # gross-up (1/(1 - t_wage)).
    required_gross = benchmark_value / (p * (1 - t_wage))
    steps.append(
        Step(
            key="required_gross_compensation",
            label="Required deferred compensation (gross, paid on success)",
            value=_money(required_gross),
            formula="required = benchmark / (success_probability * (1 - wage_tax))",
            substitution=(
                f"{benchmark_value:,.2f} / ({p:.4f} x (1 - {t_wage:.2f})) "
                f"= {required_gross:,.2f}"
            ),
            explanation=(
                "The gross amount the startup must promise to pay on success so the "
                "deal is fair. It grosses up the benchmark value for the risk of "
                "failure (1 / probability) and for the wage tax you will owe when "
                "the deferred salary is finally paid out."
            ),
        )
    )

    # -- Step 7: Compensation multiple vs. nominal deferred salary --------
    compensation_multiple = required_gross / deferred if deferred else 0.0
    steps.append(
        Step(
            key="compensation_multiple",
            label="Compensation multiple vs. deferred salary",
            value=_mult(compensation_multiple),
            unit="multiplier",
            formula="multiple = required / deferred",
            substitution=(
                f"{required_gross:,.2f} / {deferred:,.2f} = {compensation_multiple:,.4f}"
                if deferred
                else "n/a (no deferred salary)"
            ),
            explanation=(
                "How many times the nominal deferred salary the startup must promise "
                "to make deferral fair. Pure risk alone gives 1 / probability; the "
                "extra above that is the foregone tax-advantaged investment growth."
            ),
        )
    )

    summary = {
        "deferred_salary": _money(deferred),
        "net_deferred_invested": _money(net_deferred),
        "foregone_gain_net": _money(gain_net),
        "tax_advantage": _money(tax_advantage),
        "benchmark_value": _money(benchmark_value),
        "risk_multiplier": _mult(risk_multiplier),
        "required_gross_compensation": _money(required_gross),
        "compensation_multiple": _mult(compensation_multiple),
    }

    assumptions = {
        "wage_tax_pct": inputs.wage_tax_pct,
        "capital_gains_tax_pct": inputs.capital_gains_tax_pct,
        "years": inputs.years,
        "notes": [
            "All salary figures are annual gross amounts (monthly salary is never used).",
            "Startup success probability is the only risk-adjustment input.",
            "Compensation is made 'fair' on an expected-value basis: expected "
            "after-tax pay-out equals the day-one investor's end wealth.",
            "The deferred pay-out, when made, is taxed as wage income.",
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
