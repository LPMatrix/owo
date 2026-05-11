from __future__ import annotations

import os

try:
    from openai import OpenAI as _OpenAI
except ImportError as exc:
    raise ImportError(
        "Install the OpenAI SDK: pip install 'owo-parse[openrouter]'"
    ) from exc

from owo.providers import BaseProvider

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "openai/gpt-4o-mini"


class OpenRouterProvider(BaseProvider):
    """BaseProvider backed by OpenRouter (OpenAI-compatible API).

    Model and API key are read from environment variables when not passed
    explicitly:

    - ``OWO_OPENROUTER_MODEL``  — default: ``openai/gpt-4o-mini``
    - ``OPENROUTER_API_KEY``    — required

    Any model available on OpenRouter can be used, e.g. ``"google/gemini-flash-1.5"``.

    Usage::

        from owo import parse
        from owo.providers.openrouter import OpenRouterProvider

        result = parse("Aika dubu goma zuwa ga Ahmad", provider=OpenRouterProvider())
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        max_tokens: int = 512,
    ) -> None:
        self._client = _OpenAI(
            base_url=_OPENROUTER_BASE_URL,
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY"),
        )
        self._model = model or os.environ.get("OWO_OPENROUTER_MODEL", _DEFAULT_MODEL)
        self._max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
