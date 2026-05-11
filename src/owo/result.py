from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OwoResult:
    """Structured parse result aligned with the public README contract."""

    intent: str
    amount: float | None
    currency: str
    recipient: str | None
    account_number: str | None
    bank: str | None
    service: str | None
    language_detected: str
    confidence: float
    flags: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)
