# Deferred Salary Calculator

A small **local web app** for startups that pay employees less than their intended
salary and defer the difference. For every employee and every year it works out
how much salary is deferred and what that amounts to once it is **divided by the
startup's success probability** for that year (a 20% chance of success means 5
times the deferred salary), then adds everything up per employee and for the whole
company.

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

## Static web version (GitHub Pages)

The `web/` folder contains the same calculator as a purely static site: the model
is ported to JavaScript (`web/calculator.js`) and runs in the browser, so no server
is needed and nothing you type leaves your machine.

**Deploy on GitHub Pages:** in the repository go to *Settings -> Pages* and set
*Source* to **GitHub Actions**. Every push to `main` then runs the JS tests
(`node --test tests/*.test.js`) and publishes `web/` via
`.github/workflows/pages.yml`. The site appears at
`https://<user>.github.io/<repo>/`.

**Elsewhere:** upload the `web/` folder to any static host (Netlify, Cloudflare
Pages, S3, ...), or preview locally with `python3 -m http.server -d web`.

## How to use it

1. **Years & success probability** – you start with one year. Enter the startup's
   success probability for that year and click **+ Add year** for each further
   year. Each year has its own probability, which must be above 0% and at most
   100%. Next to each probability the page shows the risk of failure and the
   resulting factor (10% success = 90% risk of failure, factor ×10).
2. **Employees** – click **+ Add employee** for each person and enter:
   - **Start year** – the year the employee joins. `1` means from the very
     beginning, `2` from the second year, and so on. Whole years only.
   - **Fictional salary** – the annual gross salary the employee should earn.
   - **Actual salary** – the annual gross salary that is really paid.

   The same two salaries apply in every year from the start year onwards.

The page then shows:

- **Company totals** – total deferred salary, and the risk-adjusted deferred salary.
- **Per employee** – deferred per year, years employed, accumulated deferred
  salary, and accumulated risk-adjusted deferred salary.
- **Company per year** – deferred and risk-adjusted amounts per year, plus the
  running accumulation.
- **Employee breakdown by year** – expandable year-by-year build-up for each person.

## The calculation

For every employee, in every year from their start year onwards:

```
deferred      = fictional salary − actual salary
risk adjusted = deferred ÷ success probability of that year
```

The deferred salary is only paid if the startup succeeds, so it is divided by the
success probability: 50% success doubles it, 20% multiplies it by 5, 100% leaves it
unchanged. This is why a probability of 0% is not allowed.

- **Per employee:** `total deferred` and `total risk adjusted` are the sums of the
  yearly values over all years the employee is employed.
- **Company:** the sums of all employees' totals (also shown per year).

Example: success probabilities 10% / 50% / 100% for years 1–3.

| Employee | Start | Fictional | Actual | Deferred / year | Total deferred | Risk-adjusted |
|----------|-------|-----------|--------|-----------------|----------------|---------------|
| Ada      | 1     | 90,000    | 60,000 | 30,000          | 90,000         | 30,000 × (10 + 2 + 1) = **390,000** |
| Bruno    | 2     | 120,000   | 80,000 | 40,000          | 80,000         | 40,000 × (2 + 1) = **120,000** |
| **Company** |    |           |        |                 | **170,000**    | **510,000** |

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
`error` message (for example for a success probability of 0). `GET /api/health` returns `{"status": "ok"}`.
