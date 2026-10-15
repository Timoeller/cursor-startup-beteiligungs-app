# Deferred Salary Calculator

A small **local web app** for startups that pay employees less than their intended
salary and defer the difference. For every employee and every year it works out
how much salary is deferred and how much of that remains after applying the
startup's **success probability** for that year, then adds everything up per
employee and for the whole company.

- Runs locally; the server is **pure Python standard library** (nothing to install).
- Plain HTML/CSS/JS frontend, no build step.
- Results update live as you type.

## Quick start

Requires **Python 3.10+** (tested on 3.12).

```bash
python3 server.py
```

Open <http://127.0.0.1:8000>. Options: `--port 9000`, `--host 0.0.0.0`.

Run the tests:

```bash
python3 -m unittest discover -s tests
```

## How to use it

1. **Years & success probability** – you start with one year. Enter the startup's
   success probability for that year and click **+ Add year** for each further
   year. Each year has its own probability. (10% success = 90% risk of failure.)
2. **Employees** – click **+ Add employee** for each person and enter:
   - **Start year** – the year the employee joins. `1` means from the very
     beginning, `2` from the second year, and so on. Whole years only.
   - **Fictional salary** – the annual gross salary the employee should earn.
   - **Actual salary** – the annual gross salary that is really paid.

   The same two salaries apply in every year from the start year onwards.

The page then shows:

- **Company totals** – total deferred salary, and deferred salary × risk factor.
- **Per employee** – deferred per year, years employed, accumulated deferred
  salary, and accumulated deferred salary × risk factor.
- **Company per year** – deferred and risk-adjusted amounts per year, plus the
  running accumulation.
- **Employee breakdown by year** – expandable year-by-year build-up for each person.

## The calculation

For every employee, in every year from their start year onwards:

```
deferred      = fictional salary − actual salary
risk adjusted = deferred × success probability of that year
```

- **Per employee:** `total deferred` and `total risk adjusted` are the sums of the
  yearly values over all years the employee is employed.
- **Company:** the sums of all employees' totals (also shown per year).

Example: success probabilities 10% / 50% / 100% for years 1–3.

| Employee | Start | Fictional | Actual | Deferred / year | Total deferred | × risk |
|----------|-------|-----------|--------|-----------------|----------------|--------|
| Ada      | 1     | 90,000    | 60,000 | 30,000          | 90,000         | 30,000 × (0.1 + 0.5 + 1.0) = **48,000** |
| Bruno    | 2     | 120,000   | 80,000 | 40,000          | 80,000         | 40,000 × (0.5 + 1.0) = **60,000** |
| **Company** |    |           |        |                 | **170,000**    | **108,000** |

Not part of the model on purpose: investment returns, opportunity cost and taxes.
Salaries are annual gross amounts only.

## Project structure

```
server.py              Python stdlib web server: static files + JSON API
app/calculator.py      The model (pure functions, no I/O)
static/                index.html, styles.css, app.js (frontend)
tests/                 Model tests and end-to-end server tests
```

## API

`POST /api/calculate`

```json
{
  "years": [
    { "success_probability_pct": 10 },
    { "success_probability_pct": 50 }
  ],
  "employees": [
    { "name": "Ada", "start_year": 1, "fictional_gross": 90000, "actual_gross": 60000 }
  ]
}
```

Returns `company` totals, per-`employees` results (with a `by_year` breakdown), the
company per-`years` rows and any `warnings`. Invalid input returns HTTP 400 with an
`error` message. `GET /api/health` returns `{"status": "ok"}`.
