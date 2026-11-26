"""A payment parser must hand over what it can't read cleanly, never guess."""
from __future__ import annotations

import json
import time
import unicodedata

import pytest

from owo import BaseProvider, parse

# ── Offline: the recipient must be separable from the rest of the sentence ──


@pytest.mark.parametrize(
    "text",
    [
        "send 5k to Chidi tomorrow",
        "send 5k to Chidi Tomorrow",
        "SEND 5K TO CHIDI TOMORROW",
        "send 5k to Chidi quickly",
        "send 5k to Chidi Monday Morning",
        "send 5k to Chidi School Fees",
        "send 5k to Chidi-not-today",
        "send 5k to mama tomorrow",
        "send 5k to my mum quickly",
        "send 5k to Chidi and 3k to Ada",
        "send 5k to Chidi and Ada",
        "send 5k to Chidi or Ada",
        "send 5k to Chidi if he calls",
        "send 5k to Chidi? no, don't",
        "send 5k to Chidi?",
        "send 5k to Chidi for rent",
        "send 5k to Chidi. Actually make it 10k",
        "send 5k to Chidi, tomorrow",
        "send 5k to Chidi, GTBank tomorrow",
        "send 5k to Chidi, RandomBank99",
        "send 5k to Chidi GTBank",
        "send 5k to Chidi on Opay",
        "send 5k to Chidi Sterling Bank",
        "send 5k to 0123456789",
        "send 5k to 0123456789 GTBank",
        "send 5k to Chidi, 08012345678",
        "send 5k to Ada Obi Eze Okafor Bello",
        "send 5k to nobody",
        "send 5k to him",
        "send 5k to please",
        "send money to Tunde tomorrow",
        "send mama tomorrow 20k",
        "Aika dubu goma zuwa ga Ahmad gobe",
        "Aika dubu goma zuwa ga Ahmad da Musa",
        "Zipụ ego 5k nye Emeka echi",
        "Ran 20k si Mama lọla",
        "Abeg send 5k give Chidi make e quick",
    ],
)
def test_unclear_recipient_is_handed_over(text: str) -> None:
    r = parse(text)
    assert r.intent == "unknown"
    assert r.amount is None
    assert r.recipient is None
    assert r.flags == ["needs_llm_provider", "ambiguous_recipient"]
    assert r.raw["unparsed_recipient"]


@pytest.mark.parametrize(
    ("text", "recipient"),
    [
        ("send 5k to Chidi.", "Chidi"),
        ("send 5k to Chidi!", "Chidi"),
        ("send 5k to Ada Obi", "Ada Obi"),
        ("send 5k to Uncle Emeka", "Uncle Emeka"),
        ("send 5k to uncle emeka", "uncle emeka"),
        ("send 5k to Mama Nkechi", "Mama Nkechi"),
        ("send 5k to Mr. John Obi", "Mr. John Obi"),
        ("send 5k to Emeka O.", "Emeka O"),
        ("send 5k to my mum", "my mum"),
        ("send 5k to my landlord", "my landlord"),
        ("send 5k to my brother Emeka", "my brother Emeka"),
        ("transfer 5k to mama's account", "mama's account"),
        ("transfer 5k to my mama's account", "my mama's account"),
        ("send 5k to Abdul-Rahman", "Abdul-Rahman"),
        ("send 5k to O’Brien", "O'Brien"),
        ("send 5k to Adébáyọ̀", "Adébáyọ̀"),
        ("send 5k to Chidi, abeg", "Chidi"),
        ("send 5k to mama pls!!", "mama"),
    ],
)
def test_ordinary_recipients_still_parse(text: str, recipient: str) -> None:
    r = parse(text)
    assert r.intent == "transfer"
    assert r.recipient == unicodedata.normalize("NFC", recipient)
    assert r.flags == []


@pytest.mark.parametrize("amount", ["0", "0k", "9" * 400])
def test_unusable_amount_is_handed_over(amount: str) -> None:
    r = parse(f"send {amount} to Chidi")
    assert r.intent == "unknown"
    assert r.amount is None
    assert "needs_llm_provider" in r.flags


def test_unclear_recipient_reaches_the_provider() -> None:
    seen = []

    class Provider(BaseProvider):
        def complete(self, prompt: str) -> str:
            seen.append(prompt)
            return json.dumps({"intent": "unknown", "flags": ["ambiguous_intent"]})

    parse("send 5k to Chidi? no, don't", provider=Provider())
    assert len(seen) == 1


# ── Input handling ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "send 5k to a" + " ," * 100_000 + "x",
        "send 5k to a" + " pls" * 100_000 + " x",
        "hey " * 100_000 + "send",
        "e" + "̣́" * 100_000,
    ],
)
def test_oversized_input_returns_quickly(text: str) -> None:
    start = time.perf_counter()
    r = parse(text)
    assert time.perf_counter() - start < 0.5
    assert r.intent == "unknown"
    assert r.flags == ["needs_llm_provider", "input_too_long"]


@pytest.mark.parametrize("filler", [" ,", " pls"])
def test_long_input_under_the_limit_is_quick(filler: str) -> None:
    text = "send 5k to a" + filler * ((480 - 12) // len(filler)) + " x"
    start = time.perf_counter()
    parse(text)
    assert time.perf_counter() - start < 0.1


@pytest.mark.parametrize(
    "text",
    [
        "Zipụ ego 5k nye Emeka",
        "Zipụ ego nde abụọ nye Emeka",
        "Fi ₦5000 ranṣẹ si Tunde",
        "Ego m ole dị?",
    ],
)
def test_decomposed_accents_parse_like_composed(text: str) -> None:
    composed = parse(unicodedata.normalize("NFC", text))
    decomposed = parse(unicodedata.normalize("NFD", text))
    assert composed.intent != "unknown"
    assert decomposed == composed


# ── Provider replies ────────────────────────────────────────────────────────


def _reply(payload: object) -> object:
    class Provider(BaseProvider):
        def complete(self, prompt: str) -> str:
            return payload if not isinstance(payload, dict) else json.dumps(payload)

    return parse("something the offline rules cannot read", provider=Provider())


@pytest.mark.parametrize(
    "payload",
    ["[1, 2]", '"hello"', "42", "null", "", "[" * 100_000, None, 7],
)
def test_reply_that_is_not_an_object_is_rejected(payload: object) -> None:
    r = _reply(payload)
    assert r.intent == "unknown"
    assert r.amount is None
    assert r.flags == ["bad_provider_output"]


@pytest.mark.parametrize("payload", [{}, {"amount": 500}, {"intent": "nonsense"}, {"intent": ["transfer"]}])
def test_reply_without_a_valid_intent_is_unknown(payload: dict) -> None:
    r = _reply(payload)
    assert r.intent == "unknown"
    assert "bad_provider_output" in r.flags


@pytest.mark.parametrize(
    "amount",
    [-5000, 0, "five thousand", "5k", "-5000", "1,00", True, [5000], {"value": 1}, float("nan"), float("inf"), 10**400],
)
def test_reply_with_unusable_amount_drops_it(amount: object) -> None:
    r = _reply({"intent": "transfer", "amount": amount, "recipient": "Ada",
                "field_confidence": {"amount": 0.99, "recipient": 0.9}})
    assert r.amount is None
    assert "invalid_amount" in r.flags
    assert r.confidence_for("amount") == 0.0
    assert r.recipient == "Ada"


@pytest.mark.parametrize(("amount", "expected"), [(5000, 5000.0), (0.05, 0.05), ("5000", 5000.0), ("5,000.50", 5000.5)])
def test_reply_with_numeric_amount_is_a_float(amount: object, expected: float) -> None:
    r = _reply({"intent": "transfer", "amount": amount, "recipient": "Ada"})
    assert r.amount == expected
    assert isinstance(r.amount, float)
    assert r.flags == []


@pytest.mark.parametrize("name", ["recipient", "account_number", "bank", "service"])
@pytest.mark.parametrize("value", [["a", "b"], {"a": 1}, 123456789, True])
def test_reply_with_non_text_field_drops_it(name: str, value: object) -> None:
    r = _reply({"intent": "transfer", name: value, "field_confidence": {name: 0.99}})
    assert getattr(r, name) is None
    assert f"invalid_{name}" in r.flags
    assert r.confidence_for(name) == 0.0


def test_reply_blank_text_is_none() -> None:
    r = _reply({"intent": "transfer", "recipient": "  "})
    assert r.recipient is None


@pytest.mark.parametrize("currency", [5, ["NGN"], {}])
def test_reply_with_bad_currency_is_flagged(currency: object) -> None:
    r = _reply({"intent": "transfer", "currency": currency})
    assert r.currency == "NGN"
    assert "invalid_currency" in r.flags


@pytest.mark.parametrize("flags", [5, {"a": 1}, [1, None]])
def test_reply_with_bad_flags_does_not_crash(flags: object) -> None:
    r = _reply({"intent": "transfer", "flags": flags})
    assert r.flags == ["bad_provider_output"]


def test_reply_with_bad_language_and_confidence_does_not_crash() -> None:
    r = _reply('{"intent": "transfer", "language_detected": ["en"], '
               '"field_confidence": {"intent": NaN, "recipient": 0.5, "amount": 1e999}}')
    assert r.language_detected == "en"
    assert r.field_confidence == {"recipient": 0.5}
