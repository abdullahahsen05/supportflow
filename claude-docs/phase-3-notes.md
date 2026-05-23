# Phase 3 — Notes & Decisions

## Seed data design

- `get_or_create(db, model, filter_by, defaults)` helper used throughout for idempotency.
- Unique keys used per table: `email` (users), `order_number` (orders), `user_id+plan_name` (subscriptions), `transaction_reference` (payments), `file_path` (knowledge_documents).
- `db.flush()` called after each insert so the new row's `id` is available for FK references before the transaction commits.
- Full transaction: all-or-nothing. If any step fails, `db.rollback()` is called and no partial data is left.

## Duplicate charge demo (Ayesha)

- TXN-AYE-001: 2026-05-01, $79.99, success
- TXN-AYE-002: 2026-05-03, $79.99, success (same amount, same subscription, 2 days later)
- When Phase 7 agent sees "I was charged twice", it calls `check_payment_history(user_id)` and finds both rows → triggers ticket + escalation.

## User IDs start at 6

The first seed run failed mid-way (Unicode encode error) and rolled back. However, Postgres sequences do NOT roll back — so the next run used IDs 6–10 instead of 1–5. This is harmless; all FK relationships are consistent. Do not assume specific ID values in code — always look up by email/order_number.

## Windows cp1252 Unicode fix

The `←`, `✓`, `✗` characters couldn't be printed in the Windows cp1252 console. Replaced with `<--`, `[OK]`, `[FAIL]`. The `—` em-dash in string literals caused the initial title garble (shows as `?`) — cosmetic only, doesn't affect data.

## KB file paths

Paths in `knowledge_documents.file_path` are relative to the repo root (e.g., `data/knowledge_base/refund_policy.md`). The ingest script (Phase 4) should resolve these relative to the repo root, not `backend/`.
