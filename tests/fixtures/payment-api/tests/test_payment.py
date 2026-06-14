"""Tests for the existing PaymentService (the pattern new work follows)."""

from __future__ import annotations

import pytest

from payment_service import PaymentService


def test_charge_succeeds() -> None:
    svc = PaymentService()
    charge = svc.charge(100, "usd")
    assert charge.status == "succeeded"
    assert charge.amount == 100
    assert charge.currency == "usd"
    assert svc.charges() == [charge]


def test_charge_rejects_non_positive() -> None:
    svc = PaymentService()
    with pytest.raises(ValueError):
        svc.charge(0)
