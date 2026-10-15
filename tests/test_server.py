"""End-to-end tests of the HTTP server (static files + JSON API)."""

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from server import RequestHandler


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), RequestHandler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return response.status, response.headers, response.read()

    def post(self, payload, raw=None):
        body = raw if raw is not None else json.dumps(payload).encode()
        request = urllib.request.Request(
            self.base + "/api/calculate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_static_files_are_served(self):
        for path, content_type in [
            ("/", "text/html"),
            ("/styles.css", "text/css"),
            ("/app.js", "javascript"),
        ]:
            status, headers, _ = self.get(path)
            self.assertEqual(status, 200)
            self.assertIn(content_type, headers["Content-Type"])

    def test_health(self):
        status, _, body = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})

    def test_path_traversal_is_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get("/../server.py")
        self.assertIn(caught.exception.code, (403, 404))

    def test_calculate_multi_year_multi_employee(self):
        status, data = self.post(
            {
                "years": [
                    {"success_probability_pct": 10},
                    {"success_probability_pct": 40},
                ],
                "employees": [
                    {"name": "Ada", "start_year": 1, "fictional_gross": 90000, "actual_gross": 60000},
                    {"name": "Bruno", "start_year": 2, "fictional_gross": 120000, "actual_gross": 80000},
                ],
            }
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["company"]["total_deferred"], 100000.0)
        self.assertEqual(data["company"]["total_risk_adjusted"], 31000.0)
        self.assertEqual([e["name"] for e in data["employees"]], ["Ada", "Bruno"])

    def test_string_numbers_are_accepted(self):
        status, data = self.post(
            {
                "years": [{"success_probability_pct": "20"}],
                "employees": [
                    {"name": "Ada", "start_year": "1", "fictional_gross": "100000", "actual_gross": "50000"}
                ],
            }
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["company"]["total_risk_adjusted"], 10000.0)

    def test_validation_errors_return_400_with_message(self):
        status, data = self.post(
            {
                "years": [{"success_probability_pct": 10}],
                "employees": [
                    {"name": "Ada", "start_year": 1, "fictional_gross": 50000, "actual_gross": 60000}
                ],
            }
        )
        self.assertEqual(status, 400)
        self.assertIn("actual salary", data["error"])

    def test_missing_field_returns_400(self):
        status, data = self.post(
            {
                "years": [{"success_probability_pct": None}],
                "employees": [],
            }
        )
        self.assertEqual(status, 400)
        self.assertIn("Year 1", data["error"])

    def test_invalid_json_returns_400(self):
        status, data = self.post(None, raw=b"{not json")
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_non_object_body_returns_400(self):
        status, _ = self.post([1, 2, 3])
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
