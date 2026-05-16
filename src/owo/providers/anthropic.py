from __future__ import annotations

import os

try:
    import anthropic as _anthropic
except ImportError as exc:
    raise ImportError(
        "Install the Anthropic SDK: pip install 'owo-parse[anthropic]'"
    ) from exc

from owo._prompt import SYSTEM_PROMPT, build_user_message
from owo.providers import BaseProvider

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class AnthropicProvider(BaseProvider):
    """BaseProvider backed by the Anthropic Messages API.

    Model and API key are read from environment variables when not passed
    explicitly:

    - ``OWO_ANTHROPIC_MODEL``  — default: ``claude-haiku-4-5-20251001``
    - ``ANTHROPIC_API_KEY``    — required (read by the SDK automatically)

    Usage::

        from owo import parse
        from owo.providers.anthropic import AnthropicProvider

        result = parse("Jẹ kí n san ₦5,000 fún DSTV mi", provider=AnthropicProvider())
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> None:
        self._client = _anthropic.Anthropic(api_key=api_key)
        self._model = model or os.environ.get("OWO_ANTHROPIC_MODEL", _DEFAULT_MODEL)
        self._max_tokens = max_tokens
        self._temperature = temperature

    def complete(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def complete_messages(self, user_text: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(user_text)}],
        )
        return response.content[0].text
