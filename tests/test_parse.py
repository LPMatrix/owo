from __future__ import annotations

import json

from owo import BaseProvider, parse


def test_heuristic_send_k() -> None:
    r = parse("Send 20k to Mama")
    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    assert r.recipient == "Mama"
    assert r.currency == "NGN"
    assert r.flags == []


def test_heuristic_missing_amount() -> None:
    r = parse("Send money to Tunde")
    assert r.intent == "transfer"
    assert r.amount is None
    assert r.recipient == "Tunde"
    assert "missing_amount" in r.flags


def test_heuristic_balance() -> None:
    r = parse("How much I get?")
    assert r.intent == "balance_check"
    assert r.flags == []


def test_heuristic_fallback() -> None:
    r = parse("Buy 2GB data for 08012345678 on MTN")
    assert r.intent == "unknown"
    assert "needs_llm_provider" in r.flags


def test_heuristic_transfer_keyword() -> None:
    r = parse("Transfer 10k to  Ada ")
    assert r.intent == "transfer"
    assert r.amount == 10_000.0
    assert r.recipient == "Ada"


def test_heuristic_plain_naira_amount() -> None:
    r = parse("Send 5,000 to Chidi")
    assert r.intent == "transfer"
    assert r.amount == 5000.0
    assert r.recipient == "Chidi"


def test_heuristic_plain_naira_with_symbol() -> None:
    r = parse("transfer ₦20000 to Zara")
    assert r.amount == 20_000.0
    assert r.recipient == "Zara"


def test_heuristic_transfer_money() -> None:
    r = parse("Transfer money to Emeka")
    assert r.intent == "transfer"
    assert r.amount is None
    assert "missing_amount" in r.flags
    assert r.recipient == "Emeka"


def test_heuristic_balance_whats_my_balance() -> None:
    r = parse("What's my balance?")
    assert r.intent == "balance_check"


def test_heuristic_normalize_whitespace() -> None:
    r = parse("  Send   2k  to  Ben  ")
    assert r.amount == 2000.0
    assert r.recipient == "Ben"


def test_provider_json() -> None:
    class FakeProvider(BaseProvider):
        def complete(self, prompt: str) -> str:
            return json.dumps(
                {
                    "intent": "buy_data",
                    "amount": 500.0,
                    "currency": "NGN",
                    "recipient": None,
                    "account_number": None,
                    "bank": None,
                    "service": "MTN",
                    "language_detected": "en",
                    "confidence": 0.9,
                    "flags": [],
                }
            )

    r = parse("fixture prompt", provider=FakeProvider())
    assert r.intent == "buy_data"
    assert r.service == "MTN"
    assert r.amount == 500.0


def test_provider_json_fenced() -> None:
    class FenceProvider(BaseProvider):
        def complete(self, prompt: str) -> str:
            body = json.dumps(
                {
                    "intent": "transfer",
                    "amount": 1000.0,
                    "currency": "NGN",
                    "recipient": "Ada",
                    "account_number": None,
                    "bank": None,
                    "service": None,
                    "language_detected": "en",
                    "confidence": 0.8,
                    "flags": [],
                }
            )
            return "```json\n" + body + "\n```"

    r = parse("x", provider=FenceProvider())
    assert r.recipient == "Ada"


def test_provider_json_invalid_intent_maps_to_unknown() -> None:
    class BadIntentProvider(BaseProvider):
        def complete(self, prompt: str) -> str:
            return json.dumps(
                {
                    "intent": "totally_fake_intent",
                    "amount": None,
                    "currency": "NGN",
                    "recipient": None,
                    "account_number": None,
                    "bank": None,
                    "service": None,
                    "language_detected": "en",
                    "confidence": 0.1,
                    "flags": ["bad_model_output"],
                }
            )

    r = parse("x", provider=BadIntentProvider())
    assert r.intent == "unknown"
