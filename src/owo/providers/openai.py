from __future__ import annotations

import os

try:
    from openai import OpenAI as _OpenAI
except ImportError as exc:
    raise ImportError(
        "Install the OpenAI SDK: pip install 'owo-parse[openai]'"
    ) from exc

from owo._prompt import SYSTEM_PROMPT, build_user_message
from owo.providers import BaseProvider

_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(BaseProvider):
    """BaseProvider backed by the OpenAI Chat Completions API.

    Model and API key are read from environment variables when not passed
    explicitly:

    - ``OWO_OPENAI_MODEL``  — default: ``gpt-4o-mini``
    - ``OPENAI_API_KEY``    — required (read by the SDK automatically)

    Usage::

        from owo import parse
        from owo.providers.openai import OpenAIProvider

        result = parse("Buy 2GB data for 08012345678 on MTN", provider=OpenAIProvider())
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> None:
        self._client = _OpenAI(api_key=api_key)
        self._model = model or os.environ.get("OWO_OPENAI_MODEL", _DEFAULT_MODEL)
        self._max_tokens = max_tokens
        self._temperature = temperature

    def complete(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    def complete_messages(self, user_text: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(user_text)},
            ],
        )
        return response.choices[0].message.content or ""
