from __future__ import annotations

import json

from owo import BaseProvider, parse


# ── English ────────────────────────────────────────────────────────────────

def test_heuristic_send_k() -> None:
    r = parse("Send 20k to Mama")
    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    assert r.recipient == "Mama"
    assert r.currency == "NGN"
    assert r.language_detected == "en"
    assert r.flags == []


def test_heuristic_missing_amount() -> None:
    r = parse("Send money to Tunde")
    assert r.intent == "transfer"
    assert r.amount is None
    assert r.recipient == "Tunde"
    assert "missing_amount" in r.flags


def test_heuristic_balance_en() -> None:
    r = parse("How much do I have?")
    assert r.intent == "balance_check"
    assert r.language_detected == "en"
    assert r.flags == []


def test_heuristic_whats_my_balance() -> None:
    r = parse("What's my balance?")
    assert r.intent == "balance_check"
    assert r.language_detected == "en"


def test_heuristic_fallback() -> None:
    r = parse("Buy 2GB data for 08012345678 on MTN")
    assert r.intent == "unknown"
    assert "needs_llm_provider" in r.flags


def test_heuristic_transfer_keyword() -> None:
    r = parse("Transfer 10k to  Ada ")
    assert r.intent == "transfer"
    assert r.amount == 10_000.0
    assert r.recipient == "Ada"
    assert r.language_detected == "en"


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


def test_heuristic_normalize_whitespace() -> None:
    r = parse("  Send   2k  to  Ben  ")
    assert r.amount == 2000.0
    assert r.recipient == "Ben"


# ── Naija numerics ─────────────────────────────────────────────────────────

def test_heuristic_half_milli() -> None:
    r = parse("Send half a milli to Kemi")
    assert r.intent == "transfer"
    assert r.amount == 500_000.0
    assert r.recipient == "Kemi"
    assert r.language_detected == "en"


def test_heuristic_milli() -> None:
    r = parse("Send 2 milli to Emeka")
    assert r.intent == "transfer"
    assert r.amount == 2_000_000.0
    assert r.language_detected == "en"


# ── Bank extraction ────────────────────────────────────────────────────────

def test_heuristic_bank_extraction_en() -> None:
    r = parse("Send 10k to Zara, Zenith Bank")
    assert r.recipient == "Zara"
    assert r.bank == "Zenith Bank"


def test_heuristic_bank_extraction_pcm() -> None:
    r = parse("Abeg send 5k to Chidi, GTBank")
    assert r.recipient == "Chidi"
    assert r.bank == "GTBank"
    assert r.language_detected == "pcm"


def test_heuristic_unknown_bank_kept_in_recipient() -> None:
    # Unrecognised bank name stays part of the recipient string.
    r = parse("Send 5k to Ada, RandomBank99")
    assert "RandomBank99" in (r.recipient or "")
    assert r.bank is None


# ── Pidgin (pcm) ───────────────────────────────────────────────────────────

def test_heuristic_pcm_abeg_k() -> None:
    r = parse("Abeg send 5k to Chidi")
    assert r.intent == "transfer"
    assert r.amount == 5_000.0
    assert r.recipient == "Chidi"
    assert r.language_detected == "pcm"


def test_heuristic_pcm_give_k() -> None:
    r = parse("Send 20k give Mama")
    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    assert r.language_detected == "pcm"


def test_heuristic_pcm_send_am() -> None:
    r = parse("Send am 5k to Leo")
    assert r.intent == "transfer"
    assert r.amount == 5_000.0
    assert r.language_detected == "pcm"


def test_heuristic_pcm_missing_amount() -> None:
    r = parse("Abeg transfer money give Tunde")
    assert r.intent == "transfer"
    assert r.amount is None
    assert "missing_amount" in r.flags
    assert r.language_detected == "pcm"


def test_heuristic_pcm_balance() -> None:
    r = parse("How much I get?")
    assert r.intent == "balance_check"
    assert r.language_detected == "pcm"
    assert r.flags == []


def test_heuristic_pcm_wetin_balance() -> None:
    r = parse("Wetin be my balance?")
    assert r.intent == "balance_check"
    assert r.language_detected == "pcm"


# ── Hausa (ha) ─────────────────────────────────────────────────────────────

def test_heuristic_ha_dubu_word() -> None:
    r = parse("Aika dubu goma zuwa ga Ahmad")
    assert r.intent == "transfer"
    assert r.amount == 10_000.0
    assert r.recipient == "Ahmad"
    assert r.language_detected == "ha"


def test_heuristic_ha_k_notation() -> None:
    r = parse("Mika 5k zuwa ga Fatima")
    assert r.intent == "transfer"
    assert r.amount == 5_000.0
    assert r.language_detected == "ha"


def test_heuristic_ha_balance() -> None:
    r = parse("Duba asusuna")
    assert r.intent == "balance_check"
    assert r.language_detected == "ha"


# ── Yoruba (yo) ────────────────────────────────────────────────────────────

def test_heuristic_yo_ran_k() -> None:
    r = parse("Ran 20k si Mama")
    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    assert r.recipient == "Mama"
    assert r.language_detected == "yo"


def test_heuristic_yo_fi_ransẹ() -> None:
    r = parse("Fi ₦5000 ranṣẹ si Tunde")
    assert r.intent == "transfer"
    assert r.amount == 5_000.0
    assert r.recipient == "Tunde"
    assert r.language_detected == "yo"


def test_heuristic_yo_balance() -> None:
    r = parse("Melo ni owo mi?")
    assert r.intent == "balance_check"
    assert r.language_detected == "yo"


# ── Igbo (ig) ──────────────────────────────────────────────────────────────

def test_heuristic_ig_zipu_k() -> None:
    r = parse("Zipụ ego 5k nye Emeka")
    assert r.intent == "transfer"
    assert r.amount == 5_000.0
    assert r.recipient == "Emeka"
    assert r.language_detected == "ig"


def test_heuristic_ig_ziga_naira() -> None:
    r = parse("Ziga ego 10000 nye Ada")
    assert r.intent == "transfer"
    assert r.amount == 10_000.0
    assert r.language_detected == "ig"


def test_heuristic_ig_balance() -> None:
    r = parse("Ego m ole dị?")
    assert r.intent == "balance_check"
    assert r.language_detected == "ig"


# ── Provider path ──────────────────────────────────────────────────────────

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
