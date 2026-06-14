# payment-api — team guide

A minimal payment service. New work follows the existing `PaymentService`
pattern: one method per operation, validated inputs, a passing test per method.

## Conventions

- Source lives in `src/`, tests in `tests/`.
- Run tests from the project root: `pytest tests/ -q`
- Public methods get type hints and a short docstring.
- A new operation (e.g. refunds) mirrors the existing service-method + test
  pattern; keep modules small and focused.

## Current surface

- `src/payment_service.py` — `PaymentService.charge(amount, currency)` returns a
  `Charge`. Raises `ValueError` on non-positive amounts.
- `tests/test_payment.py` — covers `charge` (success + rejection).

## Definition of done

- `pytest tests/ -q` is green.
- New code reviewed; lead summarizes before exit.
