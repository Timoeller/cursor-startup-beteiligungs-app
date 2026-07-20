# Deferred Salary Value Calculator

A small **local web app** that estimates the real, employee-side economic value
of deferred startup compensation — the case where your *intended* annual gross
salary is higher than what the startup *actually* pays you, and the difference is
treated as deferred compensation (unpaid salary) rather than traditional equity.

It answers: **"Given the risk that the startup fails, the opportunity cost of not
investing that money, and the way salary vs. investment gains are taxed — what is
that deferred salary actually worth to me?"**

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

Advanced (editable) assumptions, with sensible defaults:

| Assumption | Default | Meaning |
|------------|---------|---------|
| Marginal wage/income tax | 45% | Top marginal tax rate on salary. |
| Capital-gains tax | 25% | Tax on investment gains. |
| Investment / deferral horizon | 1 year | How long the money would have been invested. |

---

## Calculation model

Let:

- `D`  = deferred salary = `intended_gross − actual_gross`
- `p`  = success probability (as a fraction)
- `r`  = annual investment return (as a fraction)
- `n`  = horizon in years
- `t_wage` = wage tax (default 0.45)
- `t_cg`   = capital-gains tax (default 0.25)

**Step 1 — Deferred salary**

```
D = intended_gross − actual_gross
```

**Step 2 — Risk-adjusted expected value** (success probability is the only risk input)

```
risk_adjusted = D × p
```

**Step 3 — Net deferred salary you could have invested** (had you taken the cash)

```
net_deferred = D × (1 − t_wage)
```

**Step 4 — Foregone investment gains (pre-tax)** — the opportunity cost of deferring

```
gain_gross = net_deferred × ((1 + r)^n − 1)
```

**Step 5 — Tax-adjusted investment effect**

```
gain_net      = gain_gross × (1 − t_cg)            # gains taxed at 25%, not 45%
tax_advantage = gain_gross × (t_wage − t_cg)        # extra tax you'd pay if this were salary
```

Investment gains are taxed at the **lower** capital-gains rate (25%) instead of
the **higher** marginal wage-tax rate (up to 45%). `tax_advantage` makes that
benefit explicit.

**Step 6 — Final estimated economic value**

The final value compares two worlds:

- **World A — take the cash & invest it:**
  `value_A = net_deferred + gain_net`
- **World B — defer the salary** (only repaid, and taxed as wage income, if the
  startup succeeds; no growth meanwhile):
  `value_B = risk_adjusted × (1 − t_wage)`

```
final_economic_value = value_B − value_A
```

A **negative** result means deferring costs you money compared with taking the
cash and investing it; a **positive** result means deferring is favourable.

### Assumptions & simplifications

- All figures are annual gross; monthly salary is never used.
- Startup success probability is the sole risk adjustment.
- Deferred salary, when repaid, is taxed as wage income.
- Investment gains are taxed at the capital-gains rate.
- Wage/income tax uses the top marginal rate (up to 45%).
- The model is intentionally simple and transparent so it is easy to extend
  (e.g. add contribution timing, inflation, or a probability distribution).

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
