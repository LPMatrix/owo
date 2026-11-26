from __future__ import annotations

import json

import pytest

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


# ── Natural / messy phrasing ────────────────────────────────────────────────
# A full-line-anchored regex only ever matches the exact template it was
# written for. These cover the gap: leading filler before the verb, trailing
# filler after the recipient, and one connector-less object-first shape.

def test_heuristic_leading_filler_hey_abeg() -> None:
    r = parse("hey abeg send 20k to mama")
    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    assert r.recipient == "mama"
    assert r.language_detected == "pcm"


def test_heuristic_leading_filler_pls() -> None:
    r = parse("pls send 20k to mama")
    assert r.intent == "transfer"
    assert r.recipient == "mama"
    assert r.language_detected == "en"


def test_heuristic_leading_filler_can_you() -> None:
    r = parse("can you send 20k to my mum")
    assert r.intent == "transfer"
    assert r.recipient == "my mum"


def test_heuristic_leading_filler_i_want_to() -> None:
    r = parse("i want to send 20k to mama")
    assert r.intent == "transfer"
    assert r.recipient == "mama"


def test_heuristic_abeg_with_comma() -> None:
    r = parse("Abeg, send 5k give Chidi")
    assert r.intent == "transfer"
    assert r.amount == 5_000.0
    assert r.recipient == "Chidi"
    assert r.language_detected == "pcm"


def test_heuristic_trailing_filler_not_swallowed_into_recipient() -> None:
    """Regression: a pattern's greedy (.+)$ capture used to fold trailing
    filler words into the recipient with no warning — 'mama pls', 'mama
    now' — silently corrupting the field instead of failing loudly."""
    r = parse("send 20k to mama pls")
    assert r.recipient == "mama"
    assert r.flags == []

    r = parse("send 20,000 naira to mama now")
    assert r.recipient == "mama"


def test_heuristic_trailing_filler_lowers_recipient_confidence() -> None:
    clean = parse("send 20k to mama")
    trimmed = parse("send 20k to mama pls")
    assert trimmed.field_confidence["recipient"] < clean.field_confidence["recipient"]


def test_heuristic_k_with_trailing_naira_word() -> None:
    r = parse("transfer 20k naira to mama's account")
    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    assert r.recipient == "mama's account"


def test_heuristic_object_first_send_recipient_amount() -> None:
    r = parse("send mama 20k")
    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    assert r.recipient == "mama"
    # Looser grammar (no connector word) scores lower than a connector match.
    assert r.field_confidence["intent"] < 0.95
    assert r.field_confidence["recipient"] < 0.90


def test_heuristic_balance_how_much_is_in_my_account() -> None:
    r = parse("how much is in my account")
    assert r.intent == "balance_check"
    assert r.language_detected == "en"


def test_heuristic_no_verb_still_unknown() -> None:
    """Verb-less input stays a deliberate miss — too ambiguous to guess."""
    r = parse("20k to mama")
    assert r.intent == "unknown"
    assert "needs_llm_provider" in r.flags


def test_heuristic_naira_amount_without_comma_grouping() -> None:
    """Regression: the shared plain-naira amount extractor used to
    under-match a comma-less digit run (e.g. '20000' -> just '200') once it
    was pulled out of a single backtracking regex into its own isolated
    match — because nothing downstream forced the regex to retry."""
    r = parse("transfer ₦20000 to Zara")
    assert r.amount == 20_000.0
    assert r.recipient == "Zara"


# ── Typo tolerance / spelling variants ──────────────────────────────────────

def test_heuristic_typo_tolerant_verb() -> None:
    r = parse("trasfer 20k to mama")
    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    assert r.recipient == "mama"


def test_heuristic_variant_canonicalization() -> None:
    r = parse("abg send 5k give Chidi")
    assert r.intent == "transfer"
    assert r.language_detected == "pcm"
    assert r.recipient == "Chidi"


def test_heuristic_fuzzy_correction_does_not_mangle_apostrophe_word() -> None:
    """Regression: fuzzy-correcting the leading token used to truncate
    "What's" (close to "what" under difflib's cutoff) into "what", which no
    longer matched the "what's my balance" phrase."""
    r = parse("What's my balance?")
    assert r.intent == "balance_check"


@pytest.mark.parametrize(
    "text",
    [
        "abg trasfer 20k to mama pls",
        "abeg trasfer 20k give mama",
        "Abeg, trasfer 20k to mama",
    ],
)
def test_heuristic_typo_tolerant_verb_after_abeg(text: str) -> None:
    """Regression: only the first token was typo-corrected, so a leading
    'abeg' hid a misspelled verb from the corrector."""
    r = parse(text)
    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    assert r.recipient == "mama"
    assert r.language_detected == "pcm"


@pytest.mark.parametrize("word", ["spend", "second", "ascend", "end", "transform"])
def test_heuristic_real_word_after_abeg_not_corrected_to_a_verb(word: str) -> None:
    """These are close enough to 'send'/'transfer' to clear the similarity
    cutoff, but they are real words and must not start a transfer."""
    r = parse(f"abeg {word} 20k give mama")
    assert r.intent == "unknown"


@pytest.mark.parametrize(
    "text",
    [
        "spend 20k to mama",
        "Spend 20k to mama",
        "spends 20k to mama",
        "spend, 20k to mama",
        "i want to spend 20k to mama",
        "ascend 20k to mama",
        "end 20k to mama",
        "second 20k to mama",
        "transform 20k to mama",
        "rain 20k si Mama",
        "zigzag ego 5k nye Emeka",
    ],
)
def test_heuristic_real_word_not_corrected_to_a_transfer_verb(text: str) -> None:
    """Regression: "spend 20k to mama" was typo-corrected to "send" and
    returned as a high-confidence transfer."""
    r = parse(text)
    assert r.intent == "unknown"
    assert "needs_llm_provider" in r.flags


@pytest.mark.parametrize("verb", ["trasfer", "trnsfer", "snd", "sennd"])
def test_heuristic_genuine_verb_typos_still_corrected(verb: str) -> None:
    r = parse(f"{verb} 20k to mama")
    assert r.intent == "transfer"
    assert r.amount == 20_000.0


# ── Marker-scored language ranking ──────────────────────────────────────────
# Language is decided by weighted marker evidence in the utterance, not a
# fixed try-order, so a plain English sentence with no pidgin/regional
# markers must resolve to English even though pidgin is checked first when
# scores tie.

def test_heuristic_language_ranking_prefers_evidence_over_fixed_order() -> None:
    r = parse("Send 20k to Mama")
    assert r.language_detected == "en"


def test_heuristic_language_ranking_pidgin_markers_win() -> None:
    r = parse("Abeg send 5k give Chidi")
    assert r.language_detected == "pcm"


def test_heuristic_language_confidence_reflects_evidence_dominance() -> None:
    """A sentence with zero competing-language evidence should score at
    least as confident as one sharing its verb with another language's
    grammar (English 'send' also appears in pidgin sentences)."""
    clean_en = parse("Send 20k to Mama")
    pidgin = parse("Abeg send 5k give Chidi")
    assert clean_en.field_confidence["language_detected"] > 0.0
    assert pidgin.field_confidence["language_detected"] > 0.0


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


def test_heuristic_unknown_bank_is_handed_over() -> None:
    # An unrecognised bank is not folded into the recipient name.
    r = parse("Send 5k to Ada, RandomBank99")
    assert r.recipient is None
    assert r.bank is None
    assert "ambiguous_recipient" in r.flags
    assert r.raw["unparsed_recipient"] == "Ada, RandomBank99"


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


@pytest.mark.parametrize(
    ("words", "amount"),
    [
        ("nde ise", 5_000_000.0),
        ("nde abụọ", 2_000_000.0),
        ("puku ise", 5_000.0),
        ("puku abuo", 2_000.0),
        ("puku iri", 10_000.0),
    ],
)
def test_heuristic_ig_number_words(words: str, amount: float) -> None:
    r = parse(f"Zipụ ego {words} nye Emeka")
    assert r.intent == "transfer"
    assert r.amount == amount
    assert r.recipient == "Emeka"
    assert r.language_detected == "ig"
    assert r.field_confidence["amount"] == 0.90
    assert r.flags == []


@pytest.mark.parametrize(
    "words",
    ["puku iri abụọ", "puku iri na ise", "nde ise puku iri", "puku nde"],
)
def test_heuristic_ig_compound_number_is_not_partially_read(words: str) -> None:
    """Compound amounts aren't supported. They must fall through to a
    provider rather than return only the first part of the figure."""
    r = parse(f"Zipụ ego {words} nye Emeka")
    assert r.intent == "unknown"
    assert r.amount is None


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
                    "field_confidence": {
                        "intent": 0.95,
                        "amount": 0.9,
                        "service": 0.96,
                        "language_detected": 0.94,
                    },
                    "flags": [],
                }
            )

    r = parse("fixture prompt", provider=FakeProvider())
    assert r.intent == "buy_data"
    assert r.service == "MTN"
    assert r.amount == 500.0
    assert r.field_confidence["service"] == 0.96
    assert r.confidence_for("amount") == 0.9
    assert r.min_confidence == 0.9


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
                    "field_confidence": {"intent": 0.8, "recipient": 0.75},
                    "flags": [],
                }
            )
            return "```json\n" + body + "\n```"

    r = parse("x", provider=FenceProvider())
    assert r.recipient == "Ada"
    assert r.field_confidence == {"intent": 0.8, "recipient": 0.75}


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
                    "field_confidence": {"intent": 0.1},
                    "flags": ["bad_model_output"],
                }
            )

    r = parse("x", provider=BadIntentProvider())
    assert r.intent == "unknown"


def test_provider_legacy_scalar_confidence_is_spread() -> None:
    """A provider still emitting a bare `confidence` scalar is mapped to
    per-field scores across the fields it populated."""

    class LegacyProvider(BaseProvider):
        def complete(self, prompt: str) -> str:
            return json.dumps(
                {
                    "intent": "transfer",
                    "amount": 1000.0,
                    "currency": "NGN",
                    "recipient": "Ada",
                    "account_number": None,
                    "bank": None,
                    "service": None,
                    "language_detected": "en",
                    "confidence": 0.67,
                    "flags": [],
                }
            )

    r = parse("x", provider=LegacyProvider())
    assert r.field_confidence["intent"] == 0.67
    assert r.field_confidence["amount"] == 0.67
    assert r.field_confidence["recipient"] == 0.67
    assert "bank" not in r.field_confidence


def test_heuristic_field_confidence_pinpoints_missing_amount() -> None:
    r = parse("Send money to Tunde")
    assert r.field_confidence["recipient"] >= 0.8
    assert r.field_confidence["amount"] <= 0.3
    assert r.min_confidence == r.field_confidence["amount"]


def test_heuristic_field_confidence_scored_for_clean_transfer() -> None:
    r = parse("Send 20k to Zara, Zenith Bank")
    assert set(r.field_confidence) == {
        "intent",
        "amount",
        "recipient",
        "bank",
        "language_detected",
    }
    assert all(0.0 <= v <= 1.0 for v in r.field_confidence.values())
