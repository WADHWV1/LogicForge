import json
import os
import unittest
from unittest.mock import patch

import compiler


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"JUDGE0_BASE_URL": "http://judge0.test", "JUDGE0_API_KEY": "test-key"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_supported_language_resolution(self):
        languages = [{"id": 71, "name": "Python (3.8.1)"}, {"id": 63, "name": "JavaScript (Node.js 12.14.0)"}]
        self.assertEqual(compiler._language_id("Python", languages), 71)
        self.assertEqual(compiler._language_id("JavaScript", languages), 63)

    def test_rejects_unconfigured_language(self):
        with self.assertRaises(compiler.CompilerError):
            compiler._language_id("SQL", [])

    def test_connection_status_reports_available_compilers(self):
        languages = [
            {"id": 71, "name": "Python (3.8.1)"},
            {"id": 63, "name": "JavaScript (Node.js 12.14.0)"},
            {"id": 51, "name": "C# (Mono 6.6.0.161)"},
        ]
        with patch("compiler.get_languages", return_value=languages):
            status = compiler.connection_status()
        self.assertTrue(status["configured"])
        self.assertEqual(status["supported_targets"], ["python", "javascript", "c#", "c# / .net"])

    def test_connection_status_surfaces_provider_unavailable(self):
        with patch("compiler.get_languages", side_effect=compiler.CompilerError("provider unavailable")):
            status = compiler.connection_status()
        self.assertFalse(status["configured"])
        self.assertEqual(status["error"], "provider unavailable")

    def test_execute_posts_code_then_polls_result(self):
        def fake_urlopen(req, timeout=0):
            url = req.full_url
            if url.endswith("/languages"):
                return FakeResponse([{"id": 71, "name": "Python (3.8.1)"}])
            if "/submissions/?" in url:
                payload = json.loads(req.data.decode("utf-8"))
                self.assertEqual(payload["source_code"], "print('hi')")
                self.assertEqual(payload["stdin"], "")
                self.assertLessEqual(payload["cpu_time_limit"], 2)
                return FakeResponse({"token": "abc-123"})
            if "/submissions/abc-123?" in url:
                return FakeResponse({"status": {"id": 3, "description": "Accepted"}, "stdout": "hi\n", "time": "0.01", "memory": 3000})
            raise AssertionError("Unexpected Judge0 request: " + url)

        with patch("compiler.urllib.request.urlopen", side_effect=fake_urlopen):
            result = compiler.execute("print('hi')", "Python")
        self.assertEqual(result["status"], "Accepted")
        self.assertEqual(result["stdout"], "hi\n")

    def test_size_guard_rejects_before_network(self):
        with self.assertRaises(compiler.CompilerError):
            compiler.execute("x" * 50_000, "Python")


if __name__ == "__main__":
    unittest.main()
