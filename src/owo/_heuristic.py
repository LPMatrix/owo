from __future__ import annotations

import json
import re
from typing import Any

from owo.schema import Intent, Language, OwoResult

# Heuristic matchers run on :func:`_normalize_heuristic_input` output (trimmed,
# whitespace collapsed, common smart quotes normalized).
_TRANSFER_K = re.compile(
    r"(?i)^(?:send|transfer)\s+(\d+)\s*k\s+to\s+(.+)$",
)
_TRANSFER_MONEY = re.compile(
    r"(?i)^(?:send|transfer)\s+money\s+to\s+(.+)$",
)
_TRANSFER_NAIRA = re.compile(
    r"(?i)^(?:send|transfer)\s+(?:₦|ngn\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira)?\s+to\s+(.+)$",
)
_BALANCE = re.compile(
    r"(?i)^(?:"
    r"how\s+much\s+(?:do\s+)?i\s+(?:have|get)\??"
    r"|what(?:'s|\s+is)\s+my\s+balance\??"
    r"|check\s+my\s+balance"
    r"|show\s+my\s+balance"
    r"|account\s+balance(?:\s+please)?"
    r")\s*$",
)


def _normalize_heuristic_input(text: str) -> str:
    """Normalize user text before regex matching (shared single path)."""
    t = text.strip()
    t = (
        t.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    t = re.sub(r"[\u00A0\t\n\r]+", " ", t)
    t = re.sub(r" +", " ", t)
    return t


def _parse_plain_amount(digits: str) -> float:
    return float(digits.replace(",", ""))


def _clean_recipient(name: str) -> str:
    return name.strip().rstrip(",.").strip()


def _transfer_result(
    *,
    amount: float | None,
    recipient: str,
    confidence: float,
    flags: list[str],
    pattern: str,
) -> OwoResult:
    return OwoResult(
        intent=Intent.TRANSFER,
        amount=amount,
        currency="NGN",
        recipient=_clean_recipient(recipient),
        account_number=None,
        bank=None,
        service=None,
        language_detected=Language.ENGLISH,
        confidence=confidence,
        flags=list(flags),
        raw={"parser": "heuristic", "pattern": pattern},
    )


def heuristic_parse(text: str) -> OwoResult:
    """Rule-based parse for common patterns; extend with LLM providers for full coverage."""
    t = _normalize_heuristic_input(text)

    m = _TRANSFER_K.match(t)
    if m:
        amount = float(m.group(1)) * 1000.0
        return _transfer_result(
            amount=amount,
            recipient=m.group(2),
            confidence=0.85,
            flags=[],
            pattern="send_or_transfer_Nk_to",
        )

    m = _TRANSFER_NAIRA.match(t)
    if m:
        amount = _parse_plain_amount(m.group(1))
        return _transfer_result(
            amount=amount,
            recipient=m.group(2),
            confidence=0.83,
            flags=[],
            pattern="send_or_transfer_plain_amount_to",
        )

    m = _TRANSFER_MONEY.match(t)
    if m:
        return _transfer_result(
            amount=None,
            recipient=m.group(1),
            confidence=0.61,
            flags=["missing_amount"],
            pattern="send_or_transfer_money_to",
        )

    if _BALANCE.match(t):
        return OwoResult(
            intent=Intent.BALANCE_CHECK,
            amount=None,
            currency="NGN",
            recipient=None,
            account_number=None,
            bank=None,
            service=None,
            language_detected=Language.ENGLISH,
            confidence=0.72,
            flags=[],
            raw={"parser": "heuristic", "pattern": "balance_check"},
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
        confidence=0.35,
        flags=["needs_llm_provider"],
        raw={"parser": "heuristic", "pattern": "fallback"},
    )


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
    return OwoResult(
        intent=intent,
        amount=data.get("amount"),
        currency=str(data.get("currency") or "NGN"),
        recipient=data.get("recipient"),
        account_number=data.get("account_number"),
        bank=data.get("bank"),
        service=data.get("service"),
        language_detected=Language(data.get("language_detected") or Language.ENGLISH),
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
        "crypto_sell, balance_check, unknown (use unknown when unclear).\n\n"
        f"User said:\n{user_text!r}\n"
    )
