from __future__ import annotations

import json
import re
from typing import Any

from owo.schema import Intent, Language, OwoResult

_SEND_K = re.compile(
    r"(?i)^\s*send\s+(\d+)\s*k\s+to\s+(.+?)\s*$",
)
_SEND_MONEY = re.compile(
    r"(?i)^\s*send\s+money\s+to\s+(.+?)\s*$",
)
_BALANCE = re.compile(
    r"(?i)^\s*how\s+much\s+(?:do\s+)?i\s+(?:have|get)\??\s*$",
)


def _clean_recipient(name: str) -> str:
    return name.strip().rstrip(",.").strip()


def heuristic_parse(text: str) -> OwoResult:
    """Rule-based parse for common patterns; extend with LLM providers for full coverage."""
    t = text.strip()
    m = _SEND_K.match(t)
    if m:
        amount = float(m.group(1)) * 1000.0
        recipient = _clean_recipient(m.group(2))
        return OwoResult(
            intent=Intent.TRANSFER,
            amount=amount,
            currency="NGN",
            recipient=recipient,
            account_number=None,
            bank=None,
            service=None,
            language_detected=Language.ENGLISH,
            confidence=0.85,
            flags=[],
            raw={"parser": "heuristic", "pattern": "send_Nk_to"},
        )

    m = _SEND_MONEY.match(t)
    if m:
        recipient = _clean_recipient(m.group(1))
        return OwoResult(
            intent=Intent.TRANSFER,
            amount=None,
            currency="NGN",
            recipient=recipient,
            account_number=None,
            bank=None,
            service=None,
            language_detected=Language.ENGLISH,
            confidence=0.61,
            flags=["missing_amount"],
            raw={"parser": "heuristic", "pattern": "send_money_to"},
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
        intent=Intent.BALANCE_CHECK,
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
    return OwoResult(
        intent=Intent(data.get("intent") or Intent.BALANCE_CHECK),
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
        "language_detected, confidence, flags (array of strings).\n\n"
        f"User said:\n{user_text!r}\n"
    )
