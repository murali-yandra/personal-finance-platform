# Sprint 3 Transactions And Audit

## Purpose

This note documents the implemented Sprint 3 transaction engine and audit trail.

## Implemented Scope

- `transactions` and `audit_log` tables.
- Create, read, update and list transactions.
- Transaction fingerprint engine and duplicate detection.
- Append-only audit persistence for account and transaction changes.
- Centralized Decimal money arithmetic.

## Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/transactions` | Create a transaction. Returns 201. |
| GET | `/api/v1/transactions` | Paginated list with filters. |
| GET | `/api/v1/transactions/{transaction_id}` | Return one owned transaction. |
| PATCH | `/api/v1/transactions/{transaction_id}` | Update user-editable fields. |
| GET | `/api/v1/audit` | Paginated, read-only audit trail. |

List filters: `account_id`, `category_id`, `merchant_id`, `business_type`,
`direction`, `start_date`, `end_date`, plus `page` and `page_size`.

## Duplicate Detection

Deduplication has two layers (`04-database_schema.md` section 7).

Raw messages are deduplicated by `message_hash`, which arrives in Sprint 4.
Transactions are deduplicated by `transaction_fingerprint`, a SHA-256 digest of:

```text
user_id
account_id
amount
direction
transaction_timestamp
merchant_raw
reference_number
```

Raw SMS text is never used for transaction-level deduplication: two different
transactions can produce byte-identical text, and one transaction can arrive
worded two different ways.

Normalization before hashing:

- Amounts are quantized to two decimal places, so `70` and `70.00` match.
- Text is upper-cased with non-alphanumeric characters removed, so `smart-q` and
  `SMART Q` match.
- Timestamps are truncated to whole minutes, because banks routinely report the
  same transaction with a few seconds of drift between SMS and statement.

Enforcement is two-layer as well. The service pre-checks so callers receive a
clean `DUPLICATE_TRANSACTION` conflict, and the partial unique index
`uq_transaction_fingerprint_user` is what actually holds under concurrent
ingestion of the same message. The index is partial on
`transaction_fingerprint IS NOT NULL` so rows without a fingerprint never
collide.

## Immutable Fingerprint Inputs

`PATCH /api/v1/transactions/{id}` can change `description`, `category_id`,
`merchant_id`, `business_type` and `is_reviewed`.

Amount, direction, account and timestamp are deliberately not editable. They are
the fingerprint inputs, so changing them would silently break duplicate
detection for messages already ingested.

## Audit Behavior

`AuditService` implements the `EventPublisher` protocol introduced in Sprint 2,
so the account service began writing audit rows with no change to its own logic.

Audit records share the caller's `Session`. An audit row therefore cannot survive
a rolled-back change, and a committed change cannot lose its audit row.

An update carrying a `changes` map produces one row per changed field, so a
reviewer sees exactly what moved without diffing snapshots.

Audit rows are append-only. `AuditRepository` exposes no update or delete method,
and `/api/v1/audit` is read-only.

## Money Arithmetic

`FinancialCalculator` is the single place money is computed. All amounts are
`NUMERIC(18,2)`, quantized with `ROUND_HALF_UP`. Floats are routed through `str`
so binary rounding error never enters the ledger.

`balance_delta` returns the signed effect of a transaction on an account balance.
Asset accounts fall on a debit and rise on a credit; liability accounts invert,
because spending on a credit card increases what is owed
(`04-database_schema.md` section 8).

## Error Codes

| Code | Status | Meaning |
| --- | --- | --- |
| `TRANSACTION_NOT_FOUND` | 404 | Missing, or owned by another user. |
| `DUPLICATE_TRANSACTION` | 409 | Fingerprint already exists for this user. |
| `ACCOUNT_NOT_FOUND` | 404 | Referenced account is missing or not owned. |
| `INVALID_AMOUNT` | 400 | Amount is negative or not a number. |
| `VALIDATION_ERROR` | 400 | Invalid direction, business type or currency. |

## Test Commands

```powershell
uv run pytest tests\test_transaction_service.py tests\test_transaction_fingerprint.py tests\test_audit_service.py tests\test_transactions_endpoints.py tests\test_financial_calculator.py
uv run pytest
```
