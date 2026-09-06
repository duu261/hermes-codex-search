# Hermes Codex Search

A search-only Hermes Agent backend for a Codex-compatible standalone web-search endpoint.

## This is the `web_search` backend plugin

This repository does **not** add a `codex_web` tool. It registers a provider named
`codex` for Hermes' existing `web_search` tool:

```text
Hermes web_search -> provider: codex -> /v1/alpha/search
```

Use this plugin when you want ordinary Hermes `web_search` calls to route through
the Codex-compatible search endpoint while keeping Hermes' normal search tool
shape. It does not provide `open`, `find`, `click`, PDF screenshots, or page
extraction.

For those Codex-style advanced commands, use
[Hermes Codex Web](https://github.com/duu261/hermes-codex-web) instead. That is a
separate standalone tool plugin and registers `codex_web`; it is not a search
backend.

## What it does

Hermes keeps the main model and calls its normal `web_search` tool. This plugin sends the query to `/v1/alpha/search`, then returns structured search results to the same Hermes model. It does not generate an answer and does not provide page extraction.

The endpoint requires a `model` field. The default is `gpt-5.6-luna`; override it with `CODEX_SEARCH_MODEL` when the gateway uses another compatible model. This field identifies the search request for routing and billing. It does not start a second model-completion turn.

## Install

Install the repository as a Hermes plugin, enable it, and restart the Hermes surface that will use it:

```bash
hermes plugins install <repository-url> --enable
```

Set the endpoint and credential in Hermes' private environment file:

```text
CODEX_SEARCH_BASE_URL=https://gateway.example/v1
CODEX_SEARCH_API_KEY=replace-me
# Optional:
CODEX_SEARCH_MODEL=gpt-5.6-luna
```

The base URL must include `/v1`; the plugin appends `/alpha/search`. Never commit credentials.

Remote endpoints must use HTTPS. Plain HTTP is accepted only for local
development on `localhost`, `127.0.0.1`, or `::1`. The adapter rejects embedded
credentials, refuses redirects, caps response bodies, and drops result rows
without a valid HTTP(S) URL.

## Select search without changing extraction

Set the capability-specific backend:

```yaml
web:
  search_backend: codex
  extract_backend: firecrawl
```

Or use Hermes' Web Search settings and choose **Use for Search** for this provider. Choose **Use for Extract** separately for an extraction provider.

## Development

The tests use only the Python standard library and mocked HTTP responses:

```bash
python -m unittest discover -s tests -v
```

This plugin follows Hermes' public `WebSearchProvider` extension point. It does not patch Hermes core or replace the built-in `web_search` tool.
