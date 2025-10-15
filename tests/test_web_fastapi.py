import os
import sys
import types
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

for path in (PROJECT_ROOT, SRC_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

if "jinja2" not in sys.modules:
    jinja2_stub = types.ModuleType("jinja2")

    class _StubEnvironment:  # pragma: no cover - simple stub for tests
        def __init__(self, *args, **kwargs):
            self.globals = {}

        def get_template(self, name):
            raise RuntimeError("Templates not available in tests")

    class _StubLoader:  # pragma: no cover - simple stub for tests
        def __init__(self, *args, **kwargs):
            pass

    jinja2_stub.Environment = _StubEnvironment
    jinja2_stub.FileSystemLoader = _StubLoader
    jinja2_stub.TemplateNotFound = RuntimeError
    jinja2_stub.pass_context = lambda fn: fn
    jinja2_stub.contextfunction = lambda fn: fn
    sys.modules["jinja2"] = jinja2_stub

from src.web_fastapi import _build_webhook_url


class BuildWebhookUrlTests(unittest.TestCase):
    def test_combines_base_and_relative_path(self):
        self.assertEqual(
            _build_webhook_url("https://example.com", "/webhook/text-input"),
            "https://example.com/webhook/text-input",
        )

    def test_adds_leading_slash_when_missing(self):
        self.assertEqual(
            _build_webhook_url("https://example.com/", "webhook/text-input"),
            "https://example.com/webhook/text-input",
        )

    def test_returns_base_when_it_already_contains_path(self):
        self.assertEqual(
            _build_webhook_url(
                "https://example.com/webhook/text-input", "/webhook/text-input"
            ),
            "https://example.com/webhook/text-input",
        )

    def test_respects_full_url_in_path_field(self):
        self.assertEqual(
            _build_webhook_url(
                "https://example.com", "https://other.com/webhook/text-input"
            ),
            "https://other.com/webhook/text-input",
        )

    def test_returns_base_when_path_blank(self):
        self.assertEqual(
            _build_webhook_url("https://example.com/", ""),
            "https://example.com",
        )


if __name__ == "__main__":
    unittest.main()
