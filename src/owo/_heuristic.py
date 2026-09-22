from __future__ import annotations

import difflib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from owo.schema import Intent, Language, OwoResult

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _normalize_heuristic_input(text: str) -> str:
    t = text.strip()
    t = (
        t.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )
    t = re.sub(r"[ \t\n\r ]+", " ", t)
    return t


# Common texting/SMS-speak abbreviations, folded to a canonical spelling
# before anything else runs. Kept small and conservative — each entry maps a
# single unambiguous token, not general SMS-speak decoding — per the finding
# (see "Modeling Orthographic Variation Improves NLP Performance for
# Nigerian Pidgin", arXiv:2404.18264) that canonicalizing spelling variation
# before matching, rather than open-endedly, measurably helps.
_VARIANT_MAP: dict[str, str] = {
    "pls": "please",
    "plz": "please",
    "plse": "please",
    "abg": "abeg",
    "nw": "now",
}
_VARIANT_RE = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k) for k in _VARIANT_MAP) + r")\b"
)


def _canonicalize_variants(text: str) -> str:
    return _VARIANT_RE.sub(lambda m: _VARIANT_MAP[m.group(1).lower()], text)


# Greetings and politeness phrases that precede the actual command in natural
# chat/voice input ("hey abeg send 20k to mama", "can you send 20k to mama").
# None of these are meaningful tokens in any of the five languages' grammar
# matched below, so stripping them generically before dispatch is safe.
_LEADING_FILLER_RE = re.compile(
    r"(?i)^(?:"
    r"hey|hi|hello|"
    r"please|kindly|"
    r"can\s+you(?:\s+please)?|"
    r"could\s+you(?:\s+please)?|"
    r"i\s+(?:want|wan|would\s+like)\s+to|"
    r"i\s+wan"
    r")[,]?\s+"
)


def _strip_leading_filler(text: str) -> str:
    """Repeatedly strip a leading greeting/politeness phrase.

    Applied before dispatch so a verb-first pattern still matches once the
    filler is gone, e.g. 'hey abeg send 20k to mama' -> 'abeg send 20k to
    mama' (the pcm 'abeg' marker survives -- it isn't in the filler list).
    """
    prev = None
    t = text
    while prev != t:
        prev = t
        t = _LEADING_FILLER_RE.sub("", t, count=1)
    # "Abeg, send ..." -- tolerate a comma right after the pcm marker so
    # grammars that require abeg at the very start still fire.
    t = re.sub(r"(?i)^abeg\s*,\s*", "abeg ", t)
    return t.strip()


# The closed vocabulary of leading verb/marker tokens across all five
# languages' grammars, plus balance-query openers. Used only to fuzzy-correct
# the FIRST token of the (already filler-stripped) input against a likely
# typo -- narrow blast radius, high similarity cutoff, so an unrelated short
# word is unlikely to get "corrected" into the wrong command.
_KNOWN_LEAD_TOKENS: frozenset[str] = frozenset({
    "send", "transfer", "abeg",
    "aika", "mika",
    "ran", "fi",
    "zipu", "zipụ", "ziga",
    "how", "what", "wetin", "nawa", "duba", "check", "show", "account",
    "melo", "mélò", "iye", "gwa",
})


def _fuzzy_correct_leading_token(text: str) -> str:
    """Typo-correct the leading token against the known verb/marker
    vocabulary (stdlib difflib, no model). Scoped to one token so a
    correction can't silently rewrite the rest of the sentence."""
    m = re.match(r"^(\S+)(\s*.*)$", text, re.DOTALL)
    if not m:
        return text
    first, rest = m.group(1), m.group(2)
    lowered = first.lower()
    if lowered in _KNOWN_LEAD_TOKENS:
        return text
    # A token like "what's" or "checking" already contains/extends a known
    # word — that's not a typo, leave it alone rather than truncating it.
    if any(lowered.startswith(v) or v.startswith(lowered) for v in _KNOWN_LEAD_TOKENS):
        return text
    matches = difflib.get_close_matches(lowered, _KNOWN_LEAD_TOKENS, n=1, cutoff=0.8)
    if not matches:
        return text
    return matches[0] + rest


# Trailing particles/politeness words common in Nigerian speech that have no
# place in a recipient name ("send 20k to mama now", "send 20k to mama pls").
_TRAILING_FILLERS = ("please", "pls", "plz", "abeg", "now", "jare", "sha", "biko")
_TRAILING_FILLER_RE = re.compile(
    r"(?i)(?:[\s,]+(?:" + "|".join(_TRAILING_FILLERS) + r")\b)+\s*[.,!]*$"
)


def _trim_recipient_tail(raw: str) -> tuple[str, bool]:
    """Strip trailing filler words from a greedily-captured recipient tail.

    A pattern's `(.+)$` capture takes everything to the end of the string, so
    without this, "send 20k to mama pls" silently becomes recipient='mama
    pls'. Returns (name, was_trimmed); if the whole tail was filler, the
    untrimmed text is kept rather than emptying the recipient.
    """
    base = raw.strip().rstrip(",.").strip()
    trimmed = _TRAILING_FILLER_RE.sub("", raw).strip().rstrip(",.").strip()
    return (trimmed or base), bool(trimmed) and trimmed != base


def _parse_plain_amount(digits: str) -> float:
    return float(digits.replace(",", ""))


def _clean_recipient(name: str) -> str:
    return name.strip().rstrip(",.").strip()


# ---------------------------------------------------------------------------
# Per-field confidence
# ---------------------------------------------------------------------------
# Baseline reliability per language before looking at evidence in a specific
# utterance — pidgin/regional verbs are unambiguous markers on their own;
# English verbs ("send", "transfer") double as loan words and connectors in
# code-switched text, so English starts lower. See _language_confidence for
# how this is adjusted per-utterance.
_LANG_BASE_CONF: dict[Language, float] = {
    Language.ENGLISH: 0.78,
    Language.PIDGIN: 0.88,
    Language.HAUSA: 0.86,
    Language.YORUBA: 0.86,
    Language.IGBO: 0.86,
}

# Every heuristic transfer/balance match fires on an explicit, unambiguous verb.
_INTENT_CONF = 0.95
# A looser grammar (e.g. the object-first "send mama 20k" fallback, with no
# connector word to anchor on) — same idea, less rigid, so scored lower.
_INTENT_CONF_LOOSE = 0.85
# Recipient is captured verbatim from the pattern tail — high, but free text.
_RECIPIENT_CONF = 0.90
_RECIPIENT_CONF_LOOSE = 0.75
# Bank is only set when it matched the known-institutions list.
_BANK_CONF = 0.95
# Amount confidence by how the figure was derived.
_AMOUNT_CONF_EXPLICIT = 0.97  # "20k", "₦5,000", "dubu 10"
_AMOUNT_CONF_WORD = 0.90  # "half a milli", "dubu goma"
# A field the pattern expected but could not fill.
_AMOUNT_CONF_MISSING = 0.20
_RECIPIENT_CONF_MISSING = 0.20
# At or below this score a field is treated as absent and gets a missing_* flag.
_MISSING_THRESHOLD = 0.50


def _transfer_result(
    *,
    amount: float | None,
    recipient: str,
    language: Language,
    amount_conf: float,
    lang_conf: float,
    pattern: str,
    intent_conf: float = _INTENT_CONF,
    recipient_conf: float = _RECIPIENT_CONF,
) -> OwoResult:
    trimmed_recipient, was_trimmed = _trim_recipient_tail(recipient)
    name, bank = _extract_bank(trimmed_recipient)
    clean_name = _clean_recipient(name)

    # A trimmed tail is still a clean extraction, just a slightly less
    # certain one than a capture with no trailing junk at all.
    recipient_score = recipient_conf - 0.05 if was_trimmed else recipient_conf

    field_confidence = {
        "intent": intent_conf,
        "recipient": recipient_score if clean_name else _RECIPIENT_CONF_MISSING,
        "language_detected": lang_conf,
        "amount": amount_conf if amount is not None else _AMOUNT_CONF_MISSING,
    }
    if bank is not None:
        field_confidence["bank"] = _BANK_CONF

    # Flags are derived from the same scores, so a flag and its field's
    # confidence can never disagree.
    flags = [
        f"missing_{fld}"
        for fld in ("amount", "recipient")
        if field_confidence[fld] <= _MISSING_THRESHOLD
    ]

    return OwoResult(
        intent=Intent.TRANSFER,
        amount=amount,
        currency="NGN",
        recipient=clean_name or None,
        account_number=None,
        bank=bank,
        service=None,
        language_detected=language,
        field_confidence=field_confidence,
        flags=flags,
        raw={"parser": "heuristic", "pattern": pattern},
    )


def _balance_result(language: Language, lang_conf: float, pattern: str) -> OwoResult:
    return OwoResult(
        intent=Intent.BALANCE_CHECK,
        amount=None,
        currency="NGN",
        recipient=None,
        account_number=None,
        bank=None,
        service=None,
        language_detected=language,
        field_confidence={
            "intent": _INTENT_CONF,
            "language_detected": lang_conf,
        },
        flags=[],
        raw={"parser": "heuristic", "pattern": pattern},
    )


# ---------------------------------------------------------------------------
# Shared amount-shape library
# ---------------------------------------------------------------------------
# Each shape takes the text remaining after the verb (and any pre-amount
# token) and either returns (amount, confidence, remainder-after-amount) or
# None. Per-language grammars below compose these instead of each hand-coding
# its own amount regex — the "20k [naira]" shape, for instance, used to be
# written out six times with the same bug-fix needing to land six times.

_AmountShape = Callable[[str], "tuple[float, float, str] | None"]


def _extract_amount_k(rest: str) -> tuple[float, float, str] | None:
    m = re.match(r"(?i)^(\d+)\s*k\s*(?:naira)?\s*", rest)
    if not m:
        return None
    return float(m.group(1)) * 1000, _AMOUNT_CONF_EXPLICIT, rest[m.end():]


def _extract_amount_plain(rest: str) -> tuple[float, float, str] | None:
    # `+` (not `*`) on the comma-group repetition: this regex is matched in
    # isolation (no surrounding pattern to backtrack into), so a plain
    # digit run without commas must fall through to the `\d+` alternative
    # rather than the comma-form under-matching its first 1-3 digits.
    m = re.match(r"(?i)^(?:₦|ngn\s*|#)?(\d{1,3}(?:,\d{3})+|\d+)\s*(?:naira|₦)?\s*", rest)
    if not m:
        return None
    return _parse_plain_amount(m.group(1)), _AMOUNT_CONF_EXPLICIT, rest[m.end():]


def _extract_amount_half_milli(rest: str) -> tuple[float, float, str] | None:
    m = re.match(r"(?i)^half\s+a\s+milli(?:on)?\s*", rest)
    if not m:
        return None
    return 500_000.0, _AMOUNT_CONF_WORD, rest[m.end():]


def _extract_amount_milli(rest: str) -> tuple[float, float, str] | None:
    m = re.match(r"(?i)^(\d*\.?\d+)\s*milli(?:on)?\s*", rest)
    if not m:
        return None
    return float(m.group(1)) * 1_000_000, _AMOUNT_CONF_WORD, rest[m.end():]


# Number words used after Hausa "dubu" (thousand) to form common amounts.
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


def _extract_amount_dubu_word(rest: str) -> tuple[float, float, str] | None:
    m = re.match(r"(?i)^dubu\s+(\w+)\s*", rest)
    if not m:
        return None
    multiplier = _HA_NUM_WORDS.get(m.group(1).lower())
    if multiplier is None:
        return None
    return float(multiplier * 1000), _AMOUNT_CONF_WORD, rest[m.end():]


def _extract_amount_dubu_n(rest: str) -> tuple[float, float, str] | None:
    m = re.match(r"(?i)^dubu\s+(\d+)\s*", rest)
    if not m:
        return None
    return float(m.group(1)) * 1000, _AMOUNT_CONF_EXPLICIT, rest[m.end():]


_EN_AMOUNT_SHAPES: tuple[_AmountShape, ...] = (
    _extract_amount_k,
    _extract_amount_plain,
    _extract_amount_half_milli,
    _extract_amount_milli,
)
_HA_AMOUNT_SHAPES: tuple[_AmountShape, ...] = (
    _extract_amount_k,
    _extract_amount_dubu_word,
    _extract_amount_dubu_n,
)
_IG_AMOUNT_SHAPES: tuple[_AmountShape, ...] = (
    _extract_amount_k,
    _extract_amount_plain,
)


# ---------------------------------------------------------------------------
# Generic transfer grammar: verb [pre-amount] amount connector recipient
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _TransferMatch:
    verb_text: str
    connector_text: str
    amount: float | None
    amount_conf: float
    recipient_raw: str


def _match_transfer(
    text: str,
    *,
    verb_re: str,
    connector_re: str,
    amount_shapes: tuple[_AmountShape, ...],
    pre_amount_re: str | None = None,
    money_words: tuple[str, ...] = (),
) -> _TransferMatch | None:
    m = re.match(rf"(?i)^(?:{verb_re})\s+", text)
    if not m:
        return None
    verb_text = m.group(0).strip()
    rest = text[m.end():]

    if pre_amount_re is not None:
        pm = re.match(rf"(?i)^{pre_amount_re}\s+", rest)
        if not pm:
            return None
        rest = rest[pm.end():]

    # "send money to X" shape — recognised, but no amount value to extract.
    for word in money_words:
        wm = re.match(rf"(?i)^{word}\s+(?:({connector_re}))\s+(.+)$", rest)
        if wm:
            return _TransferMatch(verb_text, wm.group(1), None, _AMOUNT_CONF_MISSING, wm.group(2))

    for shape in amount_shapes:
        result = shape(rest)
        if result is None:
            continue
        amount, amount_conf, remainder = result
        cm = re.match(rf"(?i)^(?:({connector_re}))\s+(.+)$", remainder)
        if cm:
            return _TransferMatch(verb_text, cm.group(1), amount, amount_conf, cm.group(2))
    return None


def _match_en_transfer(text: str) -> _TransferMatch | None:
    return _match_transfer(
        text, verb_re=r"send|transfer", connector_re=r"to",
        amount_shapes=_EN_AMOUNT_SHAPES, money_words=("money",),
    )


def _match_pcm_transfer(text: str) -> _TransferMatch | None:
    """Pidgin shares English verbs/amount grammar, so it needs an explicit
    unambiguous marker to disambiguate from plain English: a leading 'abeg',
    a 'give' connector, or the object pronoun 'am' after the verb."""
    has_abeg = bool(re.match(r"(?i)^abeg\s+", text))
    core = re.sub(r"(?i)^abeg\s+", "", text) if has_abeg else text
    tm = _match_transfer(
        core, verb_re=r"send(?:\s+am\b)?|transfer(?:\s+am\b)?", connector_re=r"to|give",
        amount_shapes=_EN_AMOUNT_SHAPES, money_words=("money",),
    )
    if tm is None:
        return None
    is_am = tm.verb_text.lower().endswith("am")
    is_give = tm.connector_text.lower() == "give"
    if not (has_abeg or is_am or is_give):
        return None  # plain English "send X to Y" — not pidgin
    return tm


def _match_ha_transfer(text: str) -> _TransferMatch | None:
    return _match_transfer(
        text, verb_re=r"aika|mika", connector_re=r"zuwa(?:\s+ga)?",
        amount_shapes=_HA_AMOUNT_SHAPES,
    )


def _match_ig_transfer(text: str) -> _TransferMatch | None:
    return _match_transfer(
        text, verb_re=r"zip[uụ]|ziga", connector_re=r"nye",
        amount_shapes=_IG_AMOUNT_SHAPES, pre_amount_re=r"ego\b",
    )


def _match_yo_transfer(text: str) -> _TransferMatch | None:
    # Two distinct sentence templates: "ran <N>k si <recipient>" and the
    # "fi <amount> [naira] ranṣe si <recipient>" wrapper.
    tm = _match_transfer(text, verb_re=r"ran", connector_re=r"si", amount_shapes=(_extract_amount_k,))
    if tm is not None:
        return tm
    return _match_transfer(
        text, verb_re=r"fi", connector_re=r"ran[sṣ][eẹ]\s+si",
        amount_shapes=(_extract_amount_plain,),
    )


# Object-first fallback ("send mama 20k") — no connector word at all.
# Recipient is bounded to 1-4 word-tokens so it can't swallow the trailing
# amount. English-only for now; tried after every connector-based grammar.
_EN_TRANSFER_OBJECT_K = re.compile(
    r"(?i)^(?:send|transfer)\s+((?!money\b)[a-z][\w'.-]*(?:\s+[a-z][\w'.-]*){0,3})\s+(\d+)\s*k\s*$",
)


# ---------------------------------------------------------------------------
# Balance-check phrase sets
# ---------------------------------------------------------------------------

_EN_BALANCE = re.compile(
    r"(?i)^(?:"
    r"how\s+much\s+do\s+i\s+(?:have|get)(?:\s+in\s+my\s+account)?\??"
    r"|how\s+much\s+is\s+in\s+my\s+account\??"
    r"|what(?:'s|\s+is)\s+my\s+balance\??"
    r"|what(?:'s|\s+is)\s+in\s+my\s+account\??"
    r"|check\s+my\s+balance"
    r"|show\s+my\s+balance"
    r"|account\s+balance(?:\s+please)?"
    r")\s*$",
)
_PCM_BALANCE = re.compile(
    r"(?i)^(?:"
    r"how\s+much\s+(?:i\s+)?get\??"
    r"|how\s+much\s+dey\s+my\s+account\??"
    r"|wetin\s+be\s+my\s+balance\??"
    r")\s*$",
)
_HA_BALANCE = re.compile(
    r"(?i)^(?:"
    r"nawa\s+ne\s+kudi(?:n\s+(?:da\s+ke\s+)?asusun?a?)?\??"
    r"|duba\s+asusun?[ai]?"
    r")\s*$",
)
_YO_BALANCE = re.compile(
    r"(?i)^(?:"
    r"m[eẹ]lo\s+ni\s+owo\s+mi\??"
    r"|iy[eẹ]\s+owo\s+mi\s+to\s+m[eẹ]lo\??"
    r")\s*$",
)
_IG_BALANCE = re.compile(
    r"(?i)^(?:"
    r"ego\s+m\s+ole\s+d[iị]\??"
    r"|gwa\s+m\s+ego\s+m\s+nwere"
    r")\s*$",
)

_TRANSFER_MATCHERS: dict[Language, Callable[[str], _TransferMatch | None]] = {
    Language.PIDGIN: _match_pcm_transfer,
    Language.HAUSA: _match_ha_transfer,
    Language.YORUBA: _match_yo_transfer,
    Language.IGBO: _match_ig_transfer,
    Language.ENGLISH: _match_en_transfer,
}
_BALANCE_MATCHERS: dict[Language, re.Pattern[str]] = {
    Language.PIDGIN: _PCM_BALANCE,
    Language.HAUSA: _HA_BALANCE,
    Language.YORUBA: _YO_BALANCE,
    Language.IGBO: _IG_BALANCE,
    Language.ENGLISH: _EN_BALANCE,
}


# ---------------------------------------------------------------------------
# Marker-scored language detection
# ---------------------------------------------------------------------------
# Weighted evidence per language, instead of a hardcoded try-pcm-then-ha-
# then-yo-then-ig-then-en cascade. Weight reflects how uniquely a token marks
# its language: verbs distinct to one language score high; English verbs
# ("send", "transfer") also appear inside pidgin sentences, so they score low
# — pidgin's own markers (abeg, give, wetin, ...) are what should tip it.
_LANGUAGE_MARKERS: dict[Language, tuple[tuple[str, float], ...]] = {
    Language.PIDGIN: (
        ("abeg", 3.0), ("give", 1.5), ("wetin", 3.0), ("dey", 2.0),
        ("sha", 1.0), ("jare", 1.0), ("abi", 1.0),
    ),
    Language.HAUSA: (
        ("aika", 3.0), ("mika", 3.0), ("zuwa", 2.0), ("dubu", 2.0),
        ("nawa", 2.5), ("asusu", 2.0), ("asusuna", 2.0), ("kudi", 1.5), ("duba", 1.5),
    ),
    Language.YORUBA: (
        ("ran", 1.5), ("ranse", 2.0), ("ranṣe", 2.0), ("fi", 1.0),
        ("owo", 2.0), ("melo", 2.5), ("mélò", 2.5), ("si", 0.3),
    ),
    Language.IGBO: (
        ("zipu", 3.0), ("zipụ", 3.0), ("ziga", 3.0), ("nye", 1.5),
        ("ego", 2.0), ("ole", 2.0), ("gwa", 1.5), ("nwere", 1.0),
    ),
    Language.ENGLISH: (
        ("send", 0.5), ("transfer", 0.5), ("balance", 1.0),
        ("account", 0.5), ("money", 0.5),
    ),
}
# Tie-break order for zero-evidence inputs — matches the old cascade's
# precedence so ambiguous/empty-evidence cases resolve the same way.
_LANGUAGE_PRIORITY: tuple[Language, ...] = (
    Language.PIDGIN, Language.HAUSA, Language.YORUBA, Language.IGBO, Language.ENGLISH,
)


def _score_languages(text: str) -> dict[Language, float]:
    lower = text.lower()
    scores: dict[Language, float] = {}
    for language, markers in _LANGUAGE_MARKERS.items():
        scores[language] = sum(
            weight for marker, weight in markers
            if re.search(rf"\b{re.escape(marker)}\b", lower)
        )
    return scores


def _ranked_languages(scores: dict[Language, float]) -> list[Language]:
    return sorted(_LANGUAGE_PRIORITY, key=lambda lang: (-scores[lang], _LANGUAGE_PRIORITY.index(lang)))


def _language_confidence(scores: dict[Language, float], language: Language) -> float:
    """Blend the language's baseline reliability with how dominant its
    marker evidence was in *this* utterance relative to competing languages
    — a computed number instead of one static per-language constant."""
    total = sum(scores.values())
    base = _LANG_BASE_CONF[language]
    if total <= 0:
        return base
    dominance = scores[language] / total  # 0..1
    return round(min(0.97, base + (dominance - 0.5) * 0.2), 2)


# ---------------------------------------------------------------------------
# Main heuristic dispatcher
# ---------------------------------------------------------------------------

def heuristic_parse(text: str) -> OwoResult:
    """Rule-based parse covering common patterns across all five languages."""
    t = _normalize_heuristic_input(text)
    t = _canonicalize_variants(t)
    t = _strip_leading_filler(t)
    t = _fuzzy_correct_leading_token(t)

    scores = _score_languages(t)
    ranked = _ranked_languages(scores)

    for language in ranked:
        tm = _TRANSFER_MATCHERS[language](t)
        if tm is not None:
            return _transfer_result(
                amount=tm.amount,
                recipient=tm.recipient_raw,
                language=language,
                amount_conf=tm.amount_conf,
                lang_conf=_language_confidence(scores, language),
                pattern=f"{language.value}_transfer",
            )

    m = _EN_TRANSFER_OBJECT_K.match(t)
    if m:
        return _transfer_result(
            amount=float(m.group(2)) * 1000,
            recipient=m.group(1),
            language=Language.ENGLISH,
            amount_conf=_AMOUNT_CONF_EXPLICIT,
            lang_conf=_language_confidence(scores, Language.ENGLISH),
            intent_conf=_INTENT_CONF_LOOSE,
            recipient_conf=_RECIPIENT_CONF_LOOSE,
            pattern="en_transfer_object_first",
        )

    for language in ranked:
        if _BALANCE_MATCHERS[language].match(t):
            return _balance_result(
                language, _language_confidence(scores, language), pattern=f"{language.value}_balance",
            )

    return OwoResult(
        intent=Intent.UNKNOWN,
        amount=None,
        currency="NGN",
        recipient=None,
        account_number=None,
        bank=None,
        service=None,
        language_detected=Language.ENGLISH,
        field_confidence={"intent": 0.20, "language_detected": 0.30},
        flags=["needs_llm_provider"],
        raw={"parser": "heuristic", "pattern": "fallback"},
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
# Provider path
# ---------------------------------------------------------------------------

_PROVIDER_SCORED_FIELDS = (
    "intent",
    "amount",
    "currency",
    "recipient",
    "account_number",
    "bank",
    "service",
    "language_detected",
)


def _clamp01(value: float) -> float:
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


def _coerce_field_confidence(data: dict[str, Any]) -> dict[str, float]:
    """Pull ``field_confidence`` out of provider JSON, tolerant of shape.

    Accepts the current ``{"amount": 0.9, ...}`` object. Falls back to
    spreading a legacy scalar ``confidence`` across the populated fields so
    older prompts keep producing usable per-field numbers.
    """
    raw = data.get("field_confidence")
    scored: dict[str, float] = {}
    if isinstance(raw, dict):
        for key, val in raw.items():
            try:
                scored[str(key)] = _clamp01(float(val))
            except (TypeError, ValueError):
                continue
        if scored:
            return scored

    legacy = data.get("confidence")
    if legacy is not None:
        try:
            flat = _clamp01(float(legacy))
        except (TypeError, ValueError):
            return scored
        for key in _PROVIDER_SCORED_FIELDS:
            if data.get(key) is not None:
                scored[key] = flat
    return scored


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

    try:
        data: dict[str, Any] = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return OwoResult(
            intent=Intent.UNKNOWN,
            amount=None,
            currency="NGN",
            recipient=None,
            account_number=None,
            bank=None,
            service=None,
            language_detected=Language.ENGLISH,
            field_confidence={},
            flags=["bad_provider_output"],
            raw={"parser": "provider", "source_text": source_text, "raw_output": payload},
        )
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
        field_confidence=_coerce_field_confidence(data),
        flags=list(flags),
        raw={"parser": "provider", "source_text": source_text, "llm": data},
    )
