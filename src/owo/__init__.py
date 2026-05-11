from __future__ import annotations

from owo._heuristic import (
    build_parse_prompt,
    heuristic_parse,
    result_from_provider_json,
)
from owo.providers import BaseProvider
from owo.schema import Intent, Language, OwoResult


def parse(text: str, *, provider: BaseProvider | None = None) -> OwoResult:
    """
    Parse a free-form financial instruction into structured fields.

    Without a *provider*, a small built-in heuristic handles a few English
    patterns so local tests and evals can run offline. Pass a ``BaseProvider``
    subclass to integrate an LLM backend.
    """
    if provider is None:
        return heuristic_parse(text)
    out = provider.complete(build_parse_prompt(text))
    return result_from_provider_json(out, text)


__all__ = [
    "BaseProvider",
    "Intent",
    "Language",
    "OwoResult",
    "parse",
]
