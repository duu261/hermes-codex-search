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

    def read(self):
        return json.dumps(self.payload).encode()


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
        }, clear=False), patch.object(provider.urllib.request, "urlopen", return_value=response) as open_url:
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
        }, clear=False), patch.object(provider.urllib.request, "urlopen", side_effect=error):
            result = provider.CodexWebSearchProvider().search("test")
        self.assertEqual(result, {"success": False, "error": "Codex Search returned HTTP 502"})

    def test_provider_is_search_only_and_exposes_setup(self):
        search = provider.CodexWebSearchProvider()
        self.assertTrue(search.supports_search())
        self.assertFalse(search.supports_extract())
        keys = {item["key"] for item in search.get_setup_schema()["env_vars"]}
        self.assertEqual(keys, {"CODEX_SEARCH_BASE_URL", "CODEX_SEARCH_API_KEY"})


if __name__ == "__main__":
    unittest.main()
