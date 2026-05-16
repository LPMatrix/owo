from __future__ import annotations

from owo._heuristic import heuristic_parse as _heuristic_parse
from owo._heuristic import result_from_provider_json as _result_from_provider_json
from owo.providers import BaseProvider
from owo.schema import Intent, Language, OwoResult


def parse(text: str, *, provider: BaseProvider | None = None) -> OwoResult:
    """
    Parse a free-form financial instruction into structured fields.

    The heuristic runs first in all cases. When a *provider* is supplied,
    it is called only for inputs the heuristic cannot confidently handle
    (i.e. the result carries a ``needs_llm_provider`` flag).
    """
    result = _heuristic_parse(text)
    if provider is None or "needs_llm_provider" not in result.flags:
        return result
    out = provider.complete_messages(text)
    return _result_from_provider_json(out, text)


__all__ = [
    "BaseProvider",
    "Intent",
    "Language",
    "OwoResult",
    "parse",
]
