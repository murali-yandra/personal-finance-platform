# Sprints 9 and 10 — Reporting, Balance Engine And Transfers

## Purpose

This note documents financial reporting, estimated balances, reconciliation and
transfers. These sprints complete the MVP.

## Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/v1/reports/monthly-summary` | Income, expenses and savings for a month. |
| GET | `/api/v1/reports/category-breakdown` | Spend per category, largest first. |
| GET | `/api/v1/reports/income-vs-expense` | Income and expenses per month. |
| GET | `/api/v1/reports/account-summary` | Balance and activity per account. |
| GET | `/api/v1/reports/net-worth` | Assets, liabilities and net worth. |
| POST | `/api/v1/accounts/{account_id}/reconcile` | Correct a balance against the bank. |
| GET | `/api/v1/transfers` | List transfers. |
| POST | `/api/v1/transfers` | Link two transactions as one transfer. |
| POST | `/api/v1/transfers/{transfer_id}/confirm` | Confirm a detected transfer. |

## Balance Rules

Balances are **estimates** derived from the messages the platform happened to
receive, not an authoritative statement.

| Account kind | Debit | Credit |
| --- | --- | --- |
| Asset (`BANK`, `CASH`, `INVESTMENT`) | Balance falls | Balance rises |
| Liability (`CREDIT_CARD`, `LOAN`) | Owed rises | Owed falls |

Liability balances are stored as a positive amount **owed**, so spending on a
credit card increases the number. Net worth therefore sums liabilities
separately and subtracts them rather than adding a negative
(`04-database_schema.md` section 8).

The balance update is an `EventPublisher` on `TransactionCreated` that shares
the transaction's session and commit. A balance that had drifted from the
transactions that produced it would be worse than no balance at all.

A **transfer still moves balances.** It is excluded from income and expense
reporting, not from the balance: the money really did leave one account and
arrive in another.

## Reconciliation

```http
POST /api/v1/accounts/{account_id}/reconcile
{"actual_balance": 25000}
```

Returns the estimate held before the correction, the actual figure, and the
difference absorbed. The correction writes a `BALANCE_RECONCILIATION` audit row,
so drift is visible after the fact rather than silently erased.

## Reporting Rules

Every query is scoped by `user_id` and restricted to `ACTIVE` transactions.

**Transfers are excluded from income and expense.** Money moved between the
user's own accounts is not spending; counting it would overstate both sides of
every report.

Date windows are inclusive of the last day: a transaction at `23:59:59` on the
30th falls inside that month. Getting this wrong silently drops month-end
activity, which is when a lot of it happens.

Transactions with no category are reported as `Uncategorized` rather than
dropped, so the breakdown always totals the real spend.

## Transfers

A transfer links two transactions that represent one movement of money.
`destination_transaction_id` is nullable because the matching side often arrives
in a later SMS, or never arrives.

Validation refuses a transfer that:

- names the same transaction on both sides,
- has both sides on one account,
- or spans two users. Linking across users would let one account's balance be
  moved by another user's activity.

## Balance Snapshots

`balance_snapshots` holds one row per account per day so a trend can be drawn
without replaying every transaction. Writes are an upsert keyed on
`(account_id, snapshot_date)`, so re-running the snapshot job is idempotent
rather than duplicating rows.

## Migration Note

Alembic's `alembic_version.version_num` column is `VARCHAR(32)`. A longer
revision id inserts fine on SQLite but fails on PostgreSQL with
`StringDataRightTruncation` part-way through the upgrade — during a deploy.
`tests/test_migration_conventions.py` now asserts every revision id fits, that
every migration has a real `downgrade`, and that the migrations form a single
unbranched chain.

## Test Commands

```powershell
uv run pytest tests\test_balances_and_reporting.py tests\test_mvp_end_to_end.py
uv run pytest
```

`tests/test_mvp_end_to_end.py` is the single test that proves the whole product:
register, ingest an SMS, and assert the transaction appears in the ledger, the
balance, the reports and the audit trail.
