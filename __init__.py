"""Hermes plugin entry point."""

from .provider import CodexWebSearchProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(CodexWebSearchProvider())
