"""Minimal in-memory payment service.

Fixture for the agent-team S10 payment-api E2E. The team extends this following
the existing one-method-per-operation pattern (e.g. adding refunds).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Charge:
    amount: int
    currency: str
    status: str


class PaymentService:
    """A tiny payment service: one method per operation, validated inputs."""

    def __init__(self) -> None:
        self._charges: list[Charge] = []

    def charge(self, amount: int, currency: str = "usd") -> Charge:
        """Charge ``amount`` (minor units). Raises ValueError if not positive."""
        if amount <= 0:
            raise ValueError("amount must be positive")
        charge = Charge(amount=amount, currency=currency, status="succeeded")
        self._charges.append(charge)
        return charge

    def charges(self) -> list[Charge]:
        """Return all recorded charges (newest last)."""
        return list(self._charges)
