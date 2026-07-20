# Deferred Salary Compensation Calculator

A small **local web app** for deferred startup compensation — the case where your
*intended* annual gross salary is higher than what the startup *actually* pays
you, and the difference is treated as deferred (unpaid) salary rather than equity.

It answers: **"The deferred salary is only paid back if the startup succeeds. How
large must that promised pay-out be so that accepting the deferral is *equivalent*
to a colleague who was paid the same money on day one and invested it?"**

The core intuition: if the startup only succeeds with probability `p` (say 20%),
the promised pay-out must be about **`1 / p` (5×)** just to break even on risk in
expectation — plus an extra premium for the tax-advantaged investment growth you
give up by not having the cash today.

- Runs entirely locally.
- The web server is **pure Python standard library** — nothing to `pip install`.
- The frontend is plain HTML/CSS/JS (no build step).
- Transparent, step-by-step calculation breakdown with visible formulas.

---

## Quick start

Requires **Python 3.10+** (tested on 3.12). No third-party packages.

```bash
python3 server.py
```

Then open <http://127.0.0.1:8000> in your browser.

Options:

```bash
python3 server.py --port 9000        # use a different port
python3 server.py --host 0.0.0.0     # expose on your LAN
```

Stop the server with `Ctrl+C`.

### Run the tests

```bash
python3 -m unittest discover -s tests -v
```

---

## Project structure

```
.
├── server.py              # Python stdlib web server (static files + JSON API)
├── app/
│   ├── __init__.py
│   └── calculator.py      # Pure, documented, testable calculation model
├── static/
│   ├── index.html         # UI markup (summary + detailed views)
│   ├── styles.css         # Clean, modern styling
│   └── app.js             # Fetches /api/calculate and renders results
├── tests/
│   └── test_calculator.py # Unit tests for the model
└── README.md
```

The calculation logic lives entirely in `app/calculator.py` and is side-effect
free, so it is easy to unit-test, reuse, or swap out. The server is a thin layer
that validates inputs and returns the model's result as JSON.

---

## Inputs

All salaries are **annual gross** amounts (monthly salary is never used).

| Input | Meaning |
|-------|---------|
| **Intended annual gross salary** | Your real target salary — the full annual gross you should earn. |
| **Actual annual gross salary paid** | What the startup actually pays you per year (gross). |
| **Startup success probability (%)** | Chance the startup succeeds and repays the deferred salary. **The only risk input.** |
| **Expected annual investment return (%)** | Return you could earn by investing the money instead. |
| **Number of years (deferral period)** | How many years the same reduced salary is deferred (whole number ≥ 1). Earlier years' money compounds longer. |

Advanced (editable) assumptions, with sensible defaults:

| Assumption | Default | Meaning |
|------------|---------|---------|
| Marginal wage/income tax | 45% | Top marginal tax rate on salary. |
| Capital-gains tax | 25% | Tax on investment gains. |

---

## Calculation model

Let:

- `D`  = deferred salary = `intended_gross − actual_gross`
- `p`  = success probability (as a fraction)
- `r`  = annual investment return (as a fraction)
- `N`  = number of years the arrangement runs
- `t_wage` = wage tax (default 0.45)
- `t_cg`   = capital-gains tax (default 0.25)

**Step 1 — Deferred salary per year, and total over `N` years**

```
D              = intended_gross − actual_gross
total_deferred = D × N
```

The same amount `D` is deferred in every year of the arrangement.

**Step 2 — Net amount a day-one earner could invest each year** (the benchmark
colleague is actually paid `D` each year, pays wage tax, and invests the rest)

```
net_invested = D × (1 − t_wage)
```

**Step 3 — Foregone investment gains (after capital-gains tax)**

Each year's net salary compounds until the end of the arrangement, so money from
year 1 grows for `N` years and money from the final year grows for 1 year:

```
gain_net = net_invested × Σ_{y=1..N} ((1 + r)^y − 1) × (1 − t_cg)
```

Investment gains are taxed at the **lower** capital-gains rate (25%) rather than
the **higher** marginal wage-tax rate (up to 45%). The tax advantage this creates
is shown explicitly as `tax_advantage = gain_pretax × (t_wage − t_cg)`.

**Step 4 — Benchmark value** (end wealth of the colleague paid each year)

```
benchmark = (net_invested × N) + gain_net
```

**Step 5 — Risk-compensation multiplier**

Because the pay-out only happens if the startup succeeds, its size must scale up
by `1 / p` so the *expected* value is fair (20% success → 5×):

```
risk_multiplier = 1 / p
```

**Step 6 — Required deferred compensation (the headline number)**

We require the expected, after-wage-tax pay-out to equal the benchmark value:

```
p × required_gross × (1 − t_wage) = benchmark
```

Solving for the gross amount the startup must promise (payable only on success,
taxed as wage income when paid):

```
required_gross = benchmark / ( p × (1 − t_wage) )
```

**Step 7 — Compensation multiple**

```
multiple = required_gross / total_deferred
```

With zero investment return this equals exactly `1 / p` (pure risk), regardless of
`N`. Any excess above that is the foregone tax-advantaged investment growth, which
grows with `N` because earlier years compound longer.

### Worked example

Intended `90,000`, actual `60,000`, success `20%`, return `7%`,
wage tax `45%`, capital-gains tax `25%`:

**1 year:**

- `D = 30,000`, `total_deferred = 30,000`
- `net_invested = 16,500`
- `gain_net = 866.25`, `tax_advantage = 231`
- `benchmark = 17,366.25`
- `risk_multiplier = 5.0`
- **`required_gross = 157,875`  (multiple ≈ 5.26×)**

**3 years:**

- `total_deferred = 90,000`
- `gain_net = 5,444.29` (year 1 compounds 3yr, year 2 2yr, year 3 1yr)
- `benchmark = 54,944.29`
- **`required_gross = 499,493.59`  (multiple ≈ 5.55×)**

With `return = 0%` the required pay-out is exactly `150,000` (5×), matching the
pure `1 / p` intuition.

### Assumptions & simplifications

- All figures are annual gross; monthly salary is never used.
- Startup success probability is the sole risk adjustment.
- Compensation is "fair" on an expected-value basis: expected after-tax pay-out
  equals the day-one investor's end wealth.
- The deferred pay-out, when made, is taxed as wage income.
- Investment gains are taxed at the capital-gains rate.
- Wage/income tax uses the top marginal rate (up to 45%).
- The model is intentionally simple and transparent so it is easy to extend
  (e.g. add contribution timing, inflation, or risk-aversion beyond expected value).

---

## API

`POST /api/calculate` with a JSON body:

```json
{
  "intended_gross": 90000,
  "actual_gross": 60000,
  "success_probability_pct": 30,
  "annual_return_pct": 7,
  "wage_tax_pct": 45,
  "capital_gains_tax_pct": 25,
  "years": 1
}
```

Returns a `summary`, an ordered `steps` breakdown (each with formula,
substitution and explanation), the `assumptions`, and the echoed `inputs`.
The last three fields are optional and fall back to the defaults above.
