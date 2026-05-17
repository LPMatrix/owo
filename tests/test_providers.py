from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from owo import parse
from owo._prompt import SYSTEM_PROMPT
from owo.providers import BaseProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_json(**kwargs) -> str:
    base = {
        "intent": "buy_data",
        "amount": None,
        "currency": "NGN",
        "recipient": None,
        "account_number": "08012345678",
        "bank": None,
        "service": "MTN",
        "language_detected": "en",
        "confidence": 0.92,
        "flags": [],
    }
    base.update(kwargs)
    return json.dumps(base)


def _fenced(payload: str) -> str:
    return f"```json\n{payload}\n```"


def _anthropic_response(text: str):
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


def _openai_response(text: str):
    msg = SimpleNamespace(content=text)
    choice = SimpleNamespace(message=msg)
    return SimpleNamespace(choices=[choice])


# ---------------------------------------------------------------------------
# BaseProvider default complete_messages falls back to complete()
# ---------------------------------------------------------------------------

class _MinimalProvider(BaseProvider):
    """Implements only complete(); complete_messages() uses the inherited default."""

    def __init__(self, response: str) -> None:
        self._response = response
        self._last_prompt = ""

    def complete(self, prompt: str) -> str:
        self._last_prompt = prompt
        return self._response


def test_base_provider_complete_messages_default_joins_system_and_user() -> None:
    provider = _MinimalProvider(_make_json())
    parse("Buy 1GB data for 08012345678 on MTN", provider=provider)
    assert SYSTEM_PROMPT in provider._last_prompt
    assert "08012345678" in provider._last_prompt


def test_base_provider_complete_messages_default_returns_parsed_result() -> None:
    provider = _MinimalProvider(_make_json(intent="buy_data", service="MTN"))
    r = parse("Buy 1GB data for 08012345678", provider=provider)
    assert r.intent == "buy_data"
    assert r.service == "MTN"


# ---------------------------------------------------------------------------
# Heuristic-first routing
# ---------------------------------------------------------------------------

class _SpyProvider(BaseProvider):
    called = False

    def complete(self, prompt: str) -> str:
        _SpyProvider.called = True
        return _make_json()

    def complete_messages(self, user_text: str) -> str:
        _SpyProvider.called = True
        return _make_json()


def test_provider_not_called_when_heuristic_succeeds() -> None:
    _SpyProvider.called = False
    r = parse("Send 10k to Ada", provider=_SpyProvider())
    assert not _SpyProvider.called
    assert r.intent == "transfer"
    assert r.amount == 10_000.0


def test_provider_called_for_unknown_intent() -> None:
    _SpyProvider.called = False
    parse("Buy 2GB data for 08012345678 on MTN", provider=_SpyProvider())
    assert _SpyProvider.called


# ---------------------------------------------------------------------------
# AnthropicProvider — mock the `anthropic` package in sys.modules
# ---------------------------------------------------------------------------

def _make_anthropic_sdk(response_text: str) -> tuple[ModuleType, MagicMock]:
    """Return (fake_module, mock_client) with messages.create wired up."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _anthropic_response(response_text)
    fake_sdk = ModuleType("anthropic")
    fake_sdk.Anthropic = MagicMock(return_value=mock_client)
    return fake_sdk, mock_client


def test_anthropic_provider_happy_path() -> None:
    fake_sdk, mock_client = _make_anthropic_sdk(_make_json(intent="buy_airtime"))
    with patch.dict(sys.modules, {"anthropic": fake_sdk}):
        # remove cached module so provider re-imports cleanly
        sys.modules.pop("owo.providers.anthropic", None)
        from owo.providers.anthropic import AnthropicProvider

        r = parse("Recharge 500 for 08012345678", provider=AnthropicProvider(api_key="k"))

    assert r.intent == "buy_airtime"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == SYSTEM_PROMPT
    assert call_kwargs["temperature"] == 0.0
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


def test_anthropic_provider_fenced_response() -> None:
    fake_sdk, _ = _make_anthropic_sdk(_fenced(_make_json(intent="bill_pay")))
    with patch.dict(sys.modules, {"anthropic": fake_sdk}):
        sys.modules.pop("owo.providers.anthropic", None)
        from owo.providers.anthropic import AnthropicProvider

        r = parse("Pay my DSTV", provider=AnthropicProvider(api_key="k"))

    assert r.intent == "bill_pay"


def test_anthropic_provider_bad_json_returns_unknown() -> None:
    fake_sdk, _ = _make_anthropic_sdk("not valid json at all")
    with patch.dict(sys.modules, {"anthropic": fake_sdk}):
        sys.modules.pop("owo.providers.anthropic", None)
        from owo.providers.anthropic import AnthropicProvider

        r = parse("Something weird that the heuristic won't match XYZ123", provider=AnthropicProvider(api_key="k"))

    assert r.intent == "unknown"
    assert "bad_provider_output" in r.flags


def test_anthropic_provider_custom_temperature() -> None:
    fake_sdk, mock_client = _make_anthropic_sdk(_make_json())
    with patch.dict(sys.modules, {"anthropic": fake_sdk}):
        sys.modules.pop("owo.providers.anthropic", None)
        from owo.providers.anthropic import AnthropicProvider

        parse("Buy data for 08012345678 on MTN", provider=AnthropicProvider(api_key="k", temperature=0.3))

    assert mock_client.messages.create.call_args.kwargs["temperature"] == 0.3


def test_anthropic_provider_max_tokens_forwarded() -> None:
    fake_sdk, mock_client = _make_anthropic_sdk(_make_json())
    with patch.dict(sys.modules, {"anthropic": fake_sdk}):
        sys.modules.pop("owo.providers.anthropic", None)
        from owo.providers.anthropic import AnthropicProvider

        parse("Buy data for 08012345678 on MTN", provider=AnthropicProvider(api_key="k", max_tokens=256))

    assert mock_client.messages.create.call_args.kwargs["max_tokens"] == 256


# ---------------------------------------------------------------------------
# OpenAIProvider — mock the `openai` package in sys.modules
# ---------------------------------------------------------------------------

def _make_openai_sdk(response_text: str) -> tuple[ModuleType, MagicMock]:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _openai_response(response_text)
    fake_sdk = ModuleType("openai")
    fake_sdk.OpenAI = MagicMock(return_value=mock_client)
    return fake_sdk, mock_client


def test_openai_provider_happy_path() -> None:
    fake_sdk, mock_client = _make_openai_sdk(_make_json(intent="buy_data", service="Airtel"))
    with patch.dict(sys.modules, {"openai": fake_sdk}):
        sys.modules.pop("owo.providers.openai", None)
        from owo.providers.openai import OpenAIProvider

        r = parse("Get 2GB Airtel data for 09031112222", provider=OpenAIProvider(api_key="k"))

    assert r.intent == "buy_data"
    assert r.service == "Airtel"
    messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SYSTEM_PROMPT
    assert messages[1]["role"] == "user"


def test_openai_provider_temperature_zero() -> None:
    fake_sdk, mock_client = _make_openai_sdk(_make_json())
    with patch.dict(sys.modules, {"openai": fake_sdk}):
        sys.modules.pop("owo.providers.openai", None)
        from owo.providers.openai import OpenAIProvider

        parse("Buy data for 08012345678 on MTN", provider=OpenAIProvider(api_key="k"))

    assert mock_client.chat.completions.create.call_args.kwargs["temperature"] == 0.0


def test_openai_provider_bad_json() -> None:
    fake_sdk, _ = _make_openai_sdk("oops")
    with patch.dict(sys.modules, {"openai": fake_sdk}):
        sys.modules.pop("owo.providers.openai", None)
        from owo.providers.openai import OpenAIProvider

        r = parse("Something weird XYZ123 blah blah", provider=OpenAIProvider(api_key="k"))

    assert r.intent == "unknown"
    assert "bad_provider_output" in r.flags


# ---------------------------------------------------------------------------
# OpenRouterProvider — same openai SDK, different base_url
# ---------------------------------------------------------------------------

def test_openrouter_provider_happy_path() -> None:
    fake_sdk, mock_client = _make_openai_sdk(_make_json(intent="crypto_sell", currency="BTC"))
    with patch.dict(sys.modules, {"openai": fake_sdk}):
        sys.modules.pop("owo.providers.openrouter", None)
        from owo.providers.openrouter import OpenRouterProvider

        r = parse("Sell 0.05 BTC please", provider=OpenRouterProvider(api_key="k"))

    assert r.intent == "crypto_sell"
    assert r.currency == "BTC"
    messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_openrouter_provider_temperature_zero() -> None:
    fake_sdk, mock_client = _make_openai_sdk(_make_json())
    with patch.dict(sys.modules, {"openai": fake_sdk}):
        sys.modules.pop("owo.providers.openrouter", None)
        from owo.providers.openrouter import OpenRouterProvider

        parse("Buy data for 08012345678 on MTN", provider=OpenRouterProvider(api_key="k"))

    assert mock_client.chat.completions.create.call_args.kwargs["temperature"] == 0.0
