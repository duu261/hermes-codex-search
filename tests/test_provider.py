import http.client
import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    agent = types.ModuleType("agent")
    base = types.ModuleType("agent.web_search_provider")

    class WebSearchProvider:
        pass

    base.WebSearchProvider = WebSearchProvider
    sys.modules.setdefault("agent", agent)
    sys.modules["agent.web_search_provider"] = base
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


provider = load_module("codex_search_provider", ROOT / "provider.py")


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=None):
        body = json.dumps(self.payload).encode()
        return body if limit is None else body[:limit]


class ProviderTests(unittest.TestCase):
    def test_search_sends_fixed_model_and_normalizes_results(self):
        response = FakeResponse({
            "output": "search context",
            "results": [{
                "type": "text_result",
                "title": "Python 3.13",
                "snippet": "Release notes",
                "url": "https://python.org/3.13",
                "ref_id": "turn0search0",
            }],
            "encrypted_output": "must-not-be-returned",
        })
        with patch.dict("os.environ", {
            "CODEX_SEARCH_BASE_URL": "https://gateway.example/v1",
            "CODEX_SEARCH_API_KEY": "secret",
        }, clear=False), patch.object(provider, "_open_request", return_value=response) as open_url:
            result = provider.CodexWebSearchProvider().search("Python 3.13", 3)

        request = open_url.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://gateway.example/v1/alpha/search")
        self.assertEqual(body["model"], "gpt-5.4-mini")
        self.assertEqual(body["commands"]["search_query"], [{"q": "Python 3.13"}])
        self.assertEqual(result["data"]["web"][0]["title"], "Python 3.13")
        self.assertEqual(result["data"]["web"][0]["description"], "Release notes")
        self.assertEqual(result["data"]["web"][0]["position"], 1)
        self.assertNotIn("encrypted_output", result)
        self.assertEqual(result["output"], "search context")

    def test_invalid_configuration_is_rejected_without_exposing_values(self):
        cases = [
            ("CODEX_SEARCH_API_KEY", "fixture\nAUDIT_MARKER"),
            ("CODEX_SEARCH_API_KEY", "fixture\rAUDIT_MARKER"),
            ("CODEX_SEARCH_API_KEY", "fixture\x7fAUDIT_MARKER"),
            ("CODEX_SEARCH_BASE_URL", "https://user:AUDIT_MARKER@gateway.example/v1"),
            ("CODEX_SEARCH_BASE_URL", "https://gateway.example:AUDIT_MARKER/v1"),
            ("CODEX_SEARCH_BASE_URL", "https://[AUDIT_MARKER/v1"),
            ("CODEX_SEARCH_BASE_URL", "https://gateway.example/bad path/AUDIT_MARKER"),
            ("CODEX_SEARCH_BASE_URL", "https://gateway.example/\nAUDIT_MARKER"),
        ]
        for field, value in cases:
            with self.subTest(field=field, case=cases.index((field, value))):
                env = {"CODEX_SEARCH_BASE_URL": "https://gateway.example/v1", "CODEX_SEARCH_API_KEY": "fixture"}
                env[field] = value
                with patch.dict("os.environ", env, clear=True), patch.object(provider, "_open_request", return_value=FakeResponse({"results": [{"url": "https://example.com"}]})) as transport:
                    try:
                        result = provider.CodexWebSearchProvider().search("test")
                    except (ValueError, http.client.InvalidURL) as exc:
                        self.fail(f"configuration escaped as {type(exc).__name__}")
                self.assertFalse(result["success"])
                self.assertNotIn("AUDIT_MARKER", json.dumps(result))
                transport.assert_not_called()

    def test_request_errors_do_not_expose_configuration_values(self):
        errors = [ValueError("AUDIT_MARKER"), http.client.InvalidURL("AUDIT_MARKER"),
                  UnicodeEncodeError("latin-1", "AUDIT_MARKER", 0, 1, "fixture")]
        for stage in ("Request", "_open_request"):
            owner = provider.urllib.request if stage == "Request" else provider
            for error in errors:
                with self.subTest(stage=stage, error=type(error).__name__):
                    env = {"CODEX_SEARCH_BASE_URL": "https://gateway.example/v1", "CODEX_SEARCH_API_KEY": "fixture"}
                    with patch.dict("os.environ", env, clear=True), patch.object(owner, stage, side_effect=error) as fault:
                        try:
                            result = provider.CodexWebSearchProvider().search("test")
                        except (ValueError, http.client.InvalidURL) as exc:
                            self.fail(f"request error escaped as {type(exc).__name__}")
                    self.assertEqual(result, {"success": False, "error": "Codex Search request configuration is invalid"})
                    self.assertNotIn("AUDIT_MARKER", json.dumps(result))
                    fault.assert_called_once()

    def test_search_requires_configuration(self):
        with patch.dict("os.environ", {}, clear=True):
            result = provider.CodexWebSearchProvider().search("test")
        self.assertFalse(result["success"])
        self.assertIn("CODEX_SEARCH_BASE_URL", result["error"])

    def test_search_returns_safe_http_error(self):
        error = provider.urllib.error.HTTPError(
            "https://gateway.example/v1/alpha/search", 502, "bad gateway", {}, io.BytesIO(b"secret")
        )
        with patch.dict("os.environ", {
            "CODEX_SEARCH_BASE_URL": "https://gateway.example/v1",
            "CODEX_SEARCH_API_KEY": "secret",
        }, clear=False), patch.object(provider, "_open_request", side_effect=error):
            result = provider.CodexWebSearchProvider().search("test")
        self.assertEqual(result, {"success": False, "error": "Codex Search returned HTTP 502"})

    def test_search_rejects_error_or_empty_success_envelopes(self):
        with patch.dict("os.environ", {
            "CODEX_SEARCH_BASE_URL": "https://gateway.example/v1",
            "CODEX_SEARCH_API_KEY": "secret",
        }, clear=False):
            with patch.object(
                provider,
                "_open_request",
                return_value=FakeResponse({"error": "upstream failed"}),
            ):
                error_result = provider.CodexWebSearchProvider().search("test")
            with patch.object(
                provider,
                "_open_request",
                return_value=FakeResponse({}),
            ):
                empty_result = provider.CodexWebSearchProvider().search("test")

        self.assertEqual(error_result, {"success": False, "error": "Codex Search returned an error"})
        self.assertEqual(empty_result, {"success": False, "error": "Codex Search returned no results"})

    def test_search_compacts_positions_after_malformed_entries(self):
        response = FakeResponse({
            "results": [None, {"title": "A", "url": "https://a.example"}, "bad", {"title": "B"}],
        })
        with patch.dict("os.environ", {
            "CODEX_SEARCH_BASE_URL": "https://gateway.example/v1",
            "CODEX_SEARCH_API_KEY": "secret",
        }, clear=False), patch.object(provider, "_open_request", return_value=response):
            rows = provider.CodexWebSearchProvider().search("test", 5)["data"]["web"]
        self.assertEqual([row["position"] for row in rows], [1])

    def test_transport_requires_https_and_does_not_follow_redirects(self):
        with patch.dict("os.environ", {
            "CODEX_SEARCH_BASE_URL": "http://gateway.example/v1",
            "CODEX_SEARCH_API_KEY": "secret",
        }, clear=False):
            result = provider.CodexWebSearchProvider().search("test")
        self.assertFalse(result["success"])
        self.assertIn("must use HTTPS", result["error"])
        handler = provider._NoRedirectHandler()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://other.example"))

    def test_local_http_endpoint_is_allowed_for_development(self):
        response = FakeResponse({"results": [{"title": "Local", "url": "http://localhost:8000/result"}]})
        with patch.dict("os.environ", {
            "CODEX_SEARCH_BASE_URL": "http://localhost:8000/v1",
            "CODEX_SEARCH_API_KEY": "secret",
        }, clear=False), patch.object(provider, "_open_request", return_value=response):
            result = provider.CodexWebSearchProvider().search("test")
        self.assertTrue(result["success"])

    def test_response_size_is_bounded(self):
        response = FakeResponse({"results": []})
        response.read = lambda limit=None: b"x" * (provider.MAX_RESPONSE_BYTES + 1)
        with patch.dict("os.environ", {
            "CODEX_SEARCH_BASE_URL": "https://gateway.example/v1",
            "CODEX_SEARCH_API_KEY": "secret",
        }, clear=False), patch.object(provider, "_open_request", return_value=response):
            result = provider.CodexWebSearchProvider().search("test")
        self.assertEqual(result, {"success": False, "error": "Codex Search response is too large"})

    def test_provider_is_search_only_and_exposes_setup(self):
        search = provider.CodexWebSearchProvider()
        self.assertTrue(search.supports_search())
        self.assertFalse(search.supports_extract())
        keys = {item["key"] for item in search.get_setup_schema()["env_vars"]}
        self.assertEqual(keys, {"CODEX_SEARCH_BASE_URL", "CODEX_SEARCH_API_KEY"})


if __name__ == "__main__":
    unittest.main()
