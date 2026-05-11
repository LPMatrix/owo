from __future__ import annotations

import json
import re
from typing import Any

from owo.schema import Intent, Language, OwoResult

# ---------------------------------------------------------------------------
# English (en)
# ---------------------------------------------------------------------------
_EN_TRANSFER_K = re.compile(
    r"(?i)^(?:send|transfer)\s+(\d+)\s*k\s+to\s+(.+)$",
)
_EN_TRANSFER_NAIRA = re.compile(
    r"(?i)^(?:send|transfer)\s+(?:₦|ngn\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira)?\s+to\s+(.+)$",
)
_EN_TRANSFER_MONEY = re.compile(
    r"(?i)^(?:send|transfer)\s+money\s+to\s+(.+)$",
)
_EN_TRANSFER_HALF_MILLI = re.compile(
    r"(?i)^(?:send|transfer)\s+half\s+a\s+milli(?:on)?\s+to\s+(.+)$",
)
_EN_TRANSFER_MILLI = re.compile(
    r"(?i)^(?:send|transfer)\s+(\d*\.?\d+)\s*milli(?:on)?\s+to\s+(.+)$",
)
_EN_BALANCE = re.compile(
    r"(?i)^(?:"
    r"how\s+much\s+do\s+i\s+(?:have|get)\??"
    r"|what(?:'s|\s+is)\s+my\s+balance\??"
    r"|check\s+my\s+balance"
    r"|show\s+my\s+balance"
    r"|account\s+balance(?:\s+please)?"
    r")\s*$",
)

# ---------------------------------------------------------------------------
# Nigerian Pidgin (pcm)
# Each pattern requires at least one unambiguous pcm marker:
#   abeg (prefix), give (instead of "to"), or send am (object pronoun).
# ---------------------------------------------------------------------------
_PCM_ABEG_K = re.compile(
    r"(?i)^abeg\s+(?:send|transfer)(?:\s+am)?\s+(\d+)\s*k\s+(?:to|give)\s+(.+)$",
)
_PCM_ABEG_NAIRA = re.compile(
    r"(?i)^abeg\s+(?:send|transfer)\s+(?:₦|ngn\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira)?\s+(?:to|give)\s+(.+)$",
)
_PCM_ABEG_HALF_MILLI = re.compile(
    r"(?i)^abeg\s+(?:send|transfer)\s+half\s+a\s+milli(?:on)?\s+(?:to|give)\s+(.+)$",
)
_PCM_ABEG_MILLI = re.compile(
    r"(?i)^abeg\s+(?:send|transfer)\s+(\d*\.?\d+)\s*milli(?:on)?\s+(?:to|give)\s+(.+)$",
)
_PCM_GIVE_K = re.compile(
    r"(?i)^(?:send|transfer)(?:\s+am)?\s+(\d+)\s*k\s+give\s+(.+)$",
)
_PCM_GIVE_NAIRA = re.compile(
    r"(?i)^(?:send|transfer)(?:\s+am)?\s+(?:₦|ngn\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira)?\s+give\s+(.+)$",
)
_PCM_GIVE_HALF_MILLI = re.compile(
    r"(?i)^(?:send|transfer)\s+half\s+a\s+milli(?:on)?\s+give\s+(.+)$",
)
_PCM_GIVE_MILLI = re.compile(
    r"(?i)^(?:send|transfer)\s+(\d*\.?\d+)\s*milli(?:on)?\s+give\s+(.+)$",
)
_PCM_AM_K = re.compile(
    r"(?i)^send\s+am\s+(\d+)\s*k\s+to\s+(.+)$",
)
_PCM_AM_NAIRA = re.compile(
    r"(?i)^send\s+am\s+(?:₦|ngn\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira)?\s+to\s+(.+)$",
)
_PCM_ABEG_MONEY = re.compile(
    r"(?i)^abeg\s+(?:send|transfer)\s+money\s+(?:to|give)\s+(.+)$",
)
_PCM_GIVE_MONEY = re.compile(
    r"(?i)^(?:send|transfer)\s+money\s+give\s+(.+)$",
)
_PCM_BALANCE = re.compile(
    r"(?i)^(?:"
    r"how\s+much\s+(?:i\s+)?get\??"
    r"|how\s+much\s+dey\s+my\s+account\??"
    r"|wetin\s+be\s+my\s+balance\??"
    r")\s*$",
)

# ---------------------------------------------------------------------------
# Hausa (ha)
# ---------------------------------------------------------------------------
# Number words used after "dubu" (thousand) to form common amounts.
_HA_NUM_WORDS: dict[str, int] = {
    "ɗaya": 1, "daya": 1,
    "biyu": 2,
    "uku": 3,
    "huɗu": 4, "hudu": 4,
    "biyar": 5,
    "shida": 6,
    "bakwai": 7,
    "takwas": 8,
    "tara": 9,
    "goma": 10,
    "ashirin": 20,
    "talatin": 30,
}
_HA_TRANSFER_K = re.compile(
    r"(?i)^(?:aika|mika)\s+(\d+)\s*k\s+zuwa\s+(?:ga\s+)?(.+)$",
)
_HA_TRANSFER_DUBU_WORD = re.compile(
    r"(?i)^(?:aika|mika)\s+dubu\s+(\w+)\s+zuwa\s+(?:ga\s+)?(.+)$",
)
_HA_TRANSFER_DUBU_N = re.compile(
    r"(?i)^(?:aika|mika)\s+dubu\s+(\d+)\s+zuwa\s+(?:ga\s+)?(.+)$",
)
_HA_BALANCE = re.compile(
    r"(?i)^(?:"
    r"nawa\s+ne\s+kudi(?:n\s+(?:da\s+ke\s+)?asusun?a?)?\??"
    r"|duba\s+asusun?[ai]?"
    r")\s*$",
)

# ---------------------------------------------------------------------------
# Yoruba (yo)
# ---------------------------------------------------------------------------
_YO_TRANSFER_K = re.compile(
    r"(?i)^ran\s+(\d+)\s*k\s+si\s+(.+)$",
)
_YO_TRANSFER_NAIRA = re.compile(
    r"^fi\s+[₦#]?(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira|₦)?\s+ran[sṣ][eẹ]\s+si\s+(.+)$",
    re.IGNORECASE,
)
_YO_BALANCE = re.compile(
    r"(?i)^(?:"
    r"m[eẹ]lo\s+ni\s+owo\s+mi\??"
    r"|iy[eẹ]\s+owo\s+mi\s+to\s+m[eẹ]lo\??"
    r")\s*$",
)

# ---------------------------------------------------------------------------
# Igbo (ig)
# ---------------------------------------------------------------------------
_IG_TRANSFER_K = re.compile(
    r"(?i)^(?:zip[uụ]|ziga)\s+ego\s+(\d+)\s*k\s+nye\s+(.+)$",
)
_IG_TRANSFER_NAIRA = re.compile(
    r"(?i)^(?:zip[uụ]|ziga)\s+ego\s+(?:₦|ngn\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira)?\s+nye\s+(.+)$",
)
_IG_BALANCE = re.compile(
    r"(?i)^(?:"
    r"ego\s+m\s+ole\s+d[iị]\??"
    r"|gwa\s+m\s+ego\s+m\s+nwere"
    r")\s*$",
)

# ---------------------------------------------------------------------------
# Bank name extraction
# ---------------------------------------------------------------------------
_BANK_NAMES: frozenset[str] = frozenset({
    "gtbank", "gtb", "access bank", "access", "first bank", "firstbank",
    "zenith bank", "zenith", "uba", "opay", "kuda", "moniepoint",
    "palmpay", "fcmb", "stanbic ibtc", "stanbic", "fidelity bank",
    "fidelity", "union bank", "sterling bank", "sterling",
    "wema bank", "wema", "alat", "polaris bank", "polaris",
    "ecobank", "eco bank",
})


def _extract_bank(raw: str) -> tuple[str, str | None]:
    """Split 'Chidi, GTBank' → ('Chidi', 'GTBank') when bank name is recognised."""
    if "," not in raw:
        return raw, None
    name_part, candidate = raw.rsplit(",", 1)
    if candidate.strip().rstrip(".").lower() in _BANK_NAMES:
        return name_part.strip(), candidate.strip().rstrip(".")
    return raw, None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_heuristic_input(text: str) -> str:
    t = text.strip()
    t = (
        t.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )
    t = re.sub(r"[ \t\n\r ]+", " ", t)
    return t


def _parse_plain_amount(digits: str) -> float:
    return float(digits.replace(",", ""))


def _clean_recipient(name: str) -> str:
    return name.strip().rstrip(",.").strip()


def _transfer_result(
    *,
    amount: float | None,
    recipient: str,
    language: Language,
    confidence: float,
    flags: list[str],
    pattern: str,
) -> OwoResult:
    name, bank = _extract_bank(recipient)
    return OwoResult(
        intent=Intent.TRANSFER,
        amount=amount,
        currency="NGN",
        recipient=_clean_recipient(name),
        account_number=None,
        bank=bank,
        service=None,
        language_detected=language,
        confidence=confidence,
        flags=list(flags),
        raw={"parser": "heuristic", "pattern": pattern},
    )


def _balance_result(language: Language, pattern: str) -> OwoResult:
    return OwoResult(
        intent=Intent.BALANCE_CHECK,
        amount=None,
        currency="NGN",
        recipient=None,
        account_number=None,
        bank=None,
        service=None,
        language_detected=language,
        confidence=0.72,
        flags=[],
        raw={"parser": "heuristic", "pattern": pattern},
    )


# ---------------------------------------------------------------------------
# Main heuristic dispatcher
# ---------------------------------------------------------------------------

def heuristic_parse(text: str) -> OwoResult:
    """Rule-based parse covering common patterns across all five languages."""
    t = _normalize_heuristic_input(text)

    # --- Nigerian Pidgin (pcm) ---
    m = _PCM_ABEG_K.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1000, recipient=m.group(2), language=Language.PIDGIN, confidence=0.85, flags=[], pattern="pcm_abeg_Nk")

    m = _PCM_ABEG_NAIRA.match(t)
    if m:
        return _transfer_result(amount=_parse_plain_amount(m.group(1)), recipient=m.group(2), language=Language.PIDGIN, confidence=0.83, flags=[], pattern="pcm_abeg_naira")

    m = _PCM_ABEG_HALF_MILLI.match(t)
    if m:
        return _transfer_result(amount=500_000.0, recipient=m.group(1), language=Language.PIDGIN, confidence=0.83, flags=[], pattern="pcm_abeg_half_milli")

    m = _PCM_ABEG_MILLI.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1_000_000, recipient=m.group(2), language=Language.PIDGIN, confidence=0.83, flags=[], pattern="pcm_abeg_milli")

    m = _PCM_GIVE_K.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1000, recipient=m.group(2), language=Language.PIDGIN, confidence=0.85, flags=[], pattern="pcm_give_Nk")

    m = _PCM_GIVE_NAIRA.match(t)
    if m:
        return _transfer_result(amount=_parse_plain_amount(m.group(1)), recipient=m.group(2), language=Language.PIDGIN, confidence=0.83, flags=[], pattern="pcm_give_naira")

    m = _PCM_GIVE_HALF_MILLI.match(t)
    if m:
        return _transfer_result(amount=500_000.0, recipient=m.group(1), language=Language.PIDGIN, confidence=0.83, flags=[], pattern="pcm_give_half_milli")

    m = _PCM_GIVE_MILLI.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1_000_000, recipient=m.group(2), language=Language.PIDGIN, confidence=0.83, flags=[], pattern="pcm_give_milli")

    m = _PCM_AM_K.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1000, recipient=m.group(2), language=Language.PIDGIN, confidence=0.85, flags=[], pattern="pcm_am_Nk")

    m = _PCM_AM_NAIRA.match(t)
    if m:
        return _transfer_result(amount=_parse_plain_amount(m.group(1)), recipient=m.group(2), language=Language.PIDGIN, confidence=0.83, flags=[], pattern="pcm_am_naira")

    m = _PCM_ABEG_MONEY.match(t)
    if m:
        return _transfer_result(amount=None, recipient=m.group(1), language=Language.PIDGIN, confidence=0.61, flags=["missing_amount"], pattern="pcm_abeg_money")

    m = _PCM_GIVE_MONEY.match(t)
    if m:
        return _transfer_result(amount=None, recipient=m.group(1), language=Language.PIDGIN, confidence=0.61, flags=["missing_amount"], pattern="pcm_give_money")

    if _PCM_BALANCE.match(t):
        return _balance_result(Language.PIDGIN, "pcm_balance")

    # --- Hausa (ha) ---
    m = _HA_TRANSFER_K.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1000, recipient=m.group(2), language=Language.HAUSA, confidence=0.83, flags=[], pattern="ha_aika_Nk")

    m = _HA_TRANSFER_DUBU_WORD.match(t)
    if m:
        multiplier = _HA_NUM_WORDS.get(m.group(1).lower())
        if multiplier is not None:
            return _transfer_result(amount=float(multiplier * 1000), recipient=m.group(2), language=Language.HAUSA, confidence=0.80, flags=[], pattern="ha_aika_dubu_word")

    m = _HA_TRANSFER_DUBU_N.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1000, recipient=m.group(2), language=Language.HAUSA, confidence=0.80, flags=[], pattern="ha_aika_dubu_N")

    if _HA_BALANCE.match(t):
        return _balance_result(Language.HAUSA, "ha_balance")

    # --- Yoruba (yo) ---
    m = _YO_TRANSFER_K.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1000, recipient=m.group(2), language=Language.YORUBA, confidence=0.83, flags=[], pattern="yo_ran_Nk_si")

    m = _YO_TRANSFER_NAIRA.match(t)
    if m:
        return _transfer_result(amount=_parse_plain_amount(m.group(1)), recipient=m.group(2), language=Language.YORUBA, confidence=0.81, flags=[], pattern="yo_fi_naira_ransẹ_si")

    if _YO_BALANCE.match(t):
        return _balance_result(Language.YORUBA, "yo_balance")

    # --- Igbo (ig) ---
    m = _IG_TRANSFER_K.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1000, recipient=m.group(2), language=Language.IGBO, confidence=0.83, flags=[], pattern="ig_zipu_ego_Nk_nye")

    m = _IG_TRANSFER_NAIRA.match(t)
    if m:
        return _transfer_result(amount=_parse_plain_amount(m.group(1)), recipient=m.group(2), language=Language.IGBO, confidence=0.81, flags=[], pattern="ig_zipu_ego_naira_nye")

    if _IG_BALANCE.match(t):
        return _balance_result(Language.IGBO, "ig_balance")

    # --- English (en) ---
    m = _EN_TRANSFER_K.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1000, recipient=m.group(2), language=Language.ENGLISH, confidence=0.85, flags=[], pattern="en_send_Nk_to")

    m = _EN_TRANSFER_NAIRA.match(t)
    if m:
        return _transfer_result(amount=_parse_plain_amount(m.group(1)), recipient=m.group(2), language=Language.ENGLISH, confidence=0.83, flags=[], pattern="en_send_naira_to")

    m = _EN_TRANSFER_HALF_MILLI.match(t)
    if m:
        return _transfer_result(amount=500_000.0, recipient=m.group(1), language=Language.ENGLISH, confidence=0.83, flags=[], pattern="en_send_half_milli_to")

    m = _EN_TRANSFER_MILLI.match(t)
    if m:
        return _transfer_result(amount=float(m.group(1)) * 1_000_000, recipient=m.group(2), language=Language.ENGLISH, confidence=0.83, flags=[], pattern="en_send_milli_to")

    m = _EN_TRANSFER_MONEY.match(t)
    if m:
        return _transfer_result(amount=None, recipient=m.group(1), language=Language.ENGLISH, confidence=0.61, flags=["missing_amount"], pattern="en_send_money_to")

    if _EN_BALANCE.match(t):
        return _balance_result(Language.ENGLISH, "en_balance")

    return OwoResult(
        intent=Intent.UNKNOWN,
        amount=None,
        currency="NGN",
        recipient=None,
        account_number=None,
        bank=None,
        service=None,
        language_detected=Language.ENGLISH,
        confidence=0.35,
        flags=["needs_llm_provider"],
        raw={"parser": "heuristic", "pattern": "fallback"},
    )


# ---------------------------------------------------------------------------
# Provider path
# ---------------------------------------------------------------------------

def result_from_provider_json(payload: str, source_text: str) -> OwoResult:
    """Parse JSON from an LLM provider into :class:`OwoResult`."""
    text = payload.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    data: dict[str, Any] = json.loads(text)
    flags = data.get("flags") or []
    if isinstance(flags, str):
        flags = [flags]
    raw_intent = data.get("intent")
    try:
        intent = Intent(raw_intent) if raw_intent is not None else Intent.BALANCE_CHECK
    except ValueError:
        intent = Intent.UNKNOWN
    try:
        language = Language(data.get("language_detected") or Language.ENGLISH)
    except ValueError:
        language = Language.ENGLISH
    return OwoResult(
        intent=intent,
        amount=data.get("amount"),
        currency=str(data.get("currency") or "NGN"),
        recipient=data.get("recipient"),
        account_number=data.get("account_number"),
        bank=data.get("bank"),
        service=data.get("service"),
        language_detected=language,
        confidence=float(data.get("confidence") or 0.5),
        flags=list(flags),
        raw={"parser": "provider", "source_text": source_text, "llm": data},
    )


def build_parse_prompt(user_text: str) -> str:
    return (
        "You are a strict JSON emitter for Nigerian financial intents. "
        "Reply with a single JSON object only (no markdown), keys: "
        "intent, amount, currency, recipient, account_number, bank, service, "
        "language_detected, confidence, flags (array of strings).\n"
        "intent must be one of: transfer, bill_pay, buy_airtime, buy_data, "
        "crypto_sell, balance_check, unknown (use unknown when unclear).\n"
        "language_detected must be one of: en, pcm, yo, ha, ig.\n\n"
        f"User said:\n{user_text!r}\n"
    )
