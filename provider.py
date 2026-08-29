"""Hermes web-search backend for Codex standalone search."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from agent.web_search_provider import WebSearchProvider

DEFAULT_MODEL = "gpt-5.4-mini"
MAX_LIMIT = 100


def _env(name: str) -> str:
    try:
        from agent.web_search_provider import get_provider_env
    except ImportError:
        return os.getenv(name, "")
    return get_provider_env(name)


def _endpoint(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    return base_url if base_url.endswith("/alpha/search") else f"{base_url}/alpha/search"


def _result_row(item: dict[str, Any], position: int) -> dict[str, Any]:
    row = {
        "title": str(item.get("title") or item.get("name") or ""),
        "url": str(item.get("url") or item.get("link") or ""),
        "description": str(
            item.get("description")
            or item.get("snippet")
            or item.get("text")
            or ""
        ),
        "position": position,
    }
    for key in ("ref_id", "domain"):
        if item.get(key):
            row[key] = str(item[key])
    return row


class CodexWebSearchProvider(WebSearchProvider):
    """Search-only provider backed by a Codex-compatible alpha/search endpoint."""

    @property
    def name(self) -> str:
        return "codex"

    @property
    def display_name(self) -> str:
        return "Codex Web Search"

    def is_available(self) -> bool:
        return bool(_env("CODEX_SEARCH_BASE_URL") and _env("CODEX_SEARCH_API_KEY"))

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        query = str(query or "").strip()
        if not query:
            return {"success": False, "error": "Search query is required"}

        try:
            limit = max(1, min(int(limit), MAX_LIMIT))
        except (TypeError, ValueError):
            limit = 5

        base_url = _env("CODEX_SEARCH_BASE_URL")
        api_key = _env("CODEX_SEARCH_API_KEY")
        if not base_url:
            return {"success": False, "error": "CODEX_SEARCH_BASE_URL is not set"}
        if not api_key:
            return {"success": False, "error": "CODEX_SEARCH_API_KEY is not set"}

        model = _env("CODEX_SEARCH_MODEL") or DEFAULT_MODEL
        payload = {
            "id": str(uuid.uuid4()),
            "model": model,
            "input": [{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": query}],
            }],
            "commands": {"search_query": [{"q": query}]},
            "settings": {
                "allowed_callers": ["direct"],
                "external_web_access": True,
            },
        }
        request = urllib.request.Request(
            _endpoint(base_url),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return {"success": False, "error": f"Codex Search returned HTTP {exc.code}"}
        except (urllib.error.URLError, TimeoutError):
            return {"success": False, "error": "Could not reach Codex Search"}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"success": False, "error": "Codex Search returned invalid JSON"}

        if not isinstance(data, dict):
            return {"success": False, "error": "Codex Search returned invalid JSON"}
        if data.get("error") is not None:
            return {"success": False, "error": "Codex Search returned an error"}

        raw_results = data.get("results")
        output = data.get("output")
        if not isinstance(raw_results, list) and not (isinstance(output, str) and output):
            return {"success": False, "error": "Codex Search returned no results"}

        rows = []
        for item in raw_results or []:
            if not isinstance(item, dict):
                continue
            rows.append(_result_row(item, len(rows) + 1))
            if len(rows) >= limit:
                break
        result: dict[str, Any] = {"success": True, "data": {"web": rows}}
        if isinstance(output, str) and output:
            result["output"] = output
        return result

    def get_setup_schema(self) -> dict[str, Any]:
        return {
            "name": self.display_name,
            "badge": "standalone",
            "tag": "Codex-compatible standalone search; search only.",
            "env_vars": [
                {
                    "key": "CODEX_SEARCH_BASE_URL",
                    "prompt": "Codex Search base URL (must include /v1)",
                },
                {
                    "key": "CODEX_SEARCH_API_KEY",
                    "prompt": "Codex Search API key",
                    "password": True,
                },
            ],
        }
