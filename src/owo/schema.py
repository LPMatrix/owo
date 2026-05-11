from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    TRANSFER = "transfer"
    BILL_PAY = "bill_pay"
    BUY_AIRTIME = "buy_airtime"
    BUY_DATA = "buy_data"
    CRYPTO_SELL = "crypto_sell"
    BALANCE_CHECK = "balance_check"
    UNKNOWN = "unknown"


class Language(str, Enum):
    ENGLISH = "en"
    PIDGIN = "pcm"
    YORUBA = "yo"
    HAUSA = "ha"
    IGBO = "ig"


@dataclass
class OwoResult:
    """Structured parse result aligned with the public README contract."""

    intent: Intent
    amount: float | None
    currency: str
    recipient: str | None
    account_number: str | None
    bank: str | None
    service: str | None
    language_detected: Language
    confidence: float
    flags: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)
