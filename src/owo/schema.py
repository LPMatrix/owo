from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Intent(StrEnum):
    TRANSFER = "transfer"
    BILL_PAY = "bill_pay"
    BUY_AIRTIME = "buy_airtime"
    BUY_DATA = "buy_data"
    CRYPTO_SELL = "crypto_sell"
    BALANCE_CHECK = "balance_check"
    UNKNOWN = "unknown"


class Language(StrEnum):
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
    field_confidence: dict[str, float] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def confidence_for(self, field_name: str, default: float = 0.0) -> float:
        """Confidence (0.0–1.0) for a single field, or *default* if unscored."""
        return self.field_confidence.get(field_name, default)

    @property
    def min_confidence(self) -> float:
        """Lowest per-field confidence — the weakest link in the parse.

        ``0.0`` when nothing was scored. Use this for a single go/no-go gate;
        inspect :attr:`field_confidence` to see *which* field is shaky.
        """
        return min(self.field_confidence.values(), default=0.0)
