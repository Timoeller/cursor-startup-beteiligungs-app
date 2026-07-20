#!/usr/bin/env python3
"""Local web server for the deferred-salary economic-value calculator.

Uses only the Python standard library, so there is nothing to install. It
serves the static frontend from ``static/`` and exposes a small JSON API that
runs the calculation model in :mod:`app.calculator`.

Run it with::

    python3 server.py            # serves on http://127.0.0.1:8000
    python3 server.py --port 9000
    python3 server.py --host 0.0.0.0 --port 8000

Then open the printed URL in your browser.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.calculator import CalculationInputs, calculate

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class RequestHandler(BaseHTTPRequestHandler):
    """Serves static assets and the ``/api/calculate`` JSON endpoint."""

    server_version = "DeferredSalaryApp/1.0"

    # -- helpers ---------------------------------------------------------
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json({"error": "Not found"}, status=404)
            return
        content_type, _ = mimetypes.guess_type(str(path))
        content_type = content_type or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _resolve_static(self, url_path: str) -> Path | None:
        """Map a URL path to a file inside STATIC_DIR, preventing traversal."""

        relative = url_path.lstrip("/") or "index.html"
        candidate = (STATIC_DIR / relative).resolve()
        try:
            candidate.relative_to(STATIC_DIR)
        except ValueError:
            return None
        return candidate

    # -- routing ---------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send_file(STATIC_DIR / "index.html")
            return
        if path == "/api/health":
            self._send_json({"status": "ok"})
            return

        target = self._resolve_static(path)
        if target is None:
            self._send_json({"error": "Forbidden"}, status=403)
            return
        self._send_file(target)

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        path = self.path.split("?", 1)[0]
        if path != "/api/calculate":
            self._send_json({"error": "Not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, json.JSONDecodeError):
            self._send_json({"error": "Invalid JSON body."}, status=400)
            return

        try:
            inputs = _parse_inputs(data)
            result = calculate(inputs)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json({"error": f"Unexpected error: {exc}"}, status=500)
            return

        self._send_json(result.as_dict())

    def log_message(self, fmt: str, *args) -> None:  # keep output tidy
        print(f"[server] {self.address_string()} - {fmt % args}")


def _num(data: dict, key: str, default: float | None = None) -> float:
    """Extract a numeric field, raising a clear ValueError otherwise."""

    if key not in data or data[key] in (None, ""):
        if default is not None:
            return float(default)
        raise ValueError(f"Missing required field: '{key}'.")
    try:
        return float(data[key])
    except (TypeError, ValueError):
        raise ValueError(f"Field '{key}' must be a number.")


def _parse_inputs(data: dict) -> CalculationInputs:
    """Build CalculationInputs from a decoded JSON body, applying defaults."""

    from app.calculator import (
        DEFAULT_CAPITAL_GAINS_TAX_PCT,
        DEFAULT_WAGE_TAX_PCT,
        DEFAULT_YEARS,
    )

    return CalculationInputs(
        intended_gross=_num(data, "intended_gross"),
        actual_gross=_num(data, "actual_gross"),
        success_probability_pct=_num(data, "success_probability_pct"),
        annual_return_pct=_num(data, "annual_return_pct"),
        wage_tax_pct=_num(data, "wage_tax_pct", DEFAULT_WAGE_TAX_PCT),
        capital_gains_tax_pct=_num(
            data, "capital_gains_tax_pct", DEFAULT_CAPITAL_GAINS_TAX_PCT
        ),
        years=_num(data, "years", DEFAULT_YEARS),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Host/interface to bind.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), RequestHandler)
    url = f"http://{args.host}:{args.port}"
    print("Deferred-salary economic-value calculator")
    print(f"Serving on {url}  (press Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
