#!/usr/bin/env python3
"""Local web server for the deferred-salary calculator.

Uses only the Python standard library, so there is nothing to install. It serves
the static frontend from ``static/`` and exposes a small JSON API that runs the
model in :mod:`app.calculator`.

Run it with::

    python3 server.py                 # http://127.0.0.1:8000
    python3 server.py --port 9000
    python3 server.py --host 0.0.0.0  # reachable from your network

Then open the printed URL in your browser.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app.calculator import EmployeeInput, YearInput, calculate

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MAX_BODY_BYTES = 1_000_000


def _number(value: Any, label: str) -> float:
    """Convert a JSON value to a float or raise a readable ValueError."""

    if value is None or value == "":
        raise ValueError(f"{label} is required.")
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a number.")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.") from None


def parse_payload(data: Any) -> tuple[list[YearInput], list[EmployeeInput]]:
    """Turn the decoded JSON request body into model inputs.

    Expected shape::

        {
          "years":     [{"success_probability_pct": 10}, ...],
          "employees": [{"name": "Ada", "start_year": 1,
                         "fictional_gross": 90000, "actual_gross": 60000}, ...]
        }
    """

    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")

    raw_years = data.get("years")
    raw_employees = data.get("employees", [])
    if not isinstance(raw_years, list):
        raise ValueError("'years' must be a list.")
    if not isinstance(raw_employees, list):
        raise ValueError("'employees' must be a list.")

    years = [
        YearInput(
            success_probability_pct=_number(
                (item or {}).get("success_probability_pct"),
                f"Year {index}: success probability",
            )
        )
        for index, item in enumerate(raw_years, start=1)
    ]

    employees: list[EmployeeInput] = []
    for index, item in enumerate(raw_employees, start=1):
        item = item or {}
        name = str(item.get("name") or "").strip() or f"Employee {index}"
        employees.append(
            EmployeeInput(
                name=name,
                start_year=_number(item.get("start_year"), f"{name}: start year"),
                fictional_gross=_number(
                    item.get("fictional_gross"), f"{name}: fictional salary"
                ),
                actual_gross=_number(item.get("actual_gross"), f"{name}: actual salary"),
            )
        )

    return years, employees


class RequestHandler(BaseHTTPRequestHandler):
    """Serves static assets and the ``/api/calculate`` JSON endpoint."""

    server_version = "DeferredSalaryApp/2.0"

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json({"error": "Not found"}, status=404)
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _resolve_static(url_path: str) -> Path | None:
        """Map a URL path to a file inside STATIC_DIR, preventing traversal."""

        candidate = (STATIC_DIR / (url_path.lstrip("/") or "index.html")).resolve()
        try:
            candidate.relative_to(STATIC_DIR)
        except ValueError:
            return None
        return candidate

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            self._send_json({"status": "ok"})
            return
        target = self._resolve_static(path)
        if target is None:
            self._send_json({"error": "Forbidden"}, status=403)
            return
        self._send_file(target)

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path.split("?", 1)[0] != "/api/calculate":
            self._send_json({"error": "Not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_BODY_BYTES:
                self._send_json({"error": "Request body too large."}, status=413)
                return
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._send_json({"error": "Invalid JSON body."}, status=400)
            return

        try:
            years, employees = parse_payload(data)
            result = calculate(years, employees)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        self._send_json(result)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[server] {self.address_string()} - {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deferred-salary calculator")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), RequestHandler)
    print("Deferred-salary calculator")
    print(f"Serving on http://{args.host}:{args.port}  (press Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
