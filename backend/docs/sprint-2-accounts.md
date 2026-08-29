# Sprint 2 Accounts

## Purpose

This note documents the implemented Sprint 2 account management scope.

## Implemented Scope

- Create, read, update, archive and list accounts.
- Ownership validation at the service boundary.
- Account status transition rules.
- Duplicate prevention per user.
- Internal event hooks for `AccountCreated`, `AccountUpdated` and
  `AccountArchived`.

## Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/accounts` | Create an account. Returns 201. |
| GET | `/api/v1/accounts` | List non-archived accounts. |
| GET | `/api/v1/accounts/{account_id}` | Return one owned account. |
| PATCH | `/api/v1/accounts/{account_id}` | Update submitted fields only. |
| DELETE | `/api/v1/accounts/{account_id}` | Archive. Never deletes. |

All endpoints require `Authorization: Bearer <access_token>`.

## Account Types

The approved source of truth is `04-database_schema.md` section 3.1:

```text
BANK
CREDIT_CARD
CASH
INVESTMENT
LOAN
```

`WALLET` is not an account type. Cash wallets must use `CASH`.

## Status Model

```text
PENDING
ACTIVE
ARCHIVED
DISABLED
```

Manual account creation defaults to `ACTIVE`. Automatically detected accounts are
created as `PENDING` until the user confirms the details.

Allowed transitions:

| From | To |
| --- | --- |
| `PENDING` | `ACTIVE`, `DISABLED`, `ARCHIVED` |
| `ACTIVE` | `DISABLED`, `ARCHIVED` |
| `DISABLED` | `ACTIVE`, `ARCHIVED` |
| `ARCHIVED` | none |

`ARCHIVED` is terminal. An archived account cannot be modified, and archiving is
idempotent: re-archiving changes nothing and raises no event.

## List Behavior

`GET /api/v1/accounts` returns `PENDING`, `ACTIVE` and `DISABLED` accounts.
`ARCHIVED` accounts are returned only with `?include_archived=true`.

## Duplicate Prevention

An account is unique per user on:

```text
(user_id, bank_name, last_four_digits, account_type)
```

This mirrors the `uq_user_bank_lastfour_type` database constraint. The service
checks for a duplicate before writing so callers receive
`ACCOUNT_ALREADY_EXISTS` rather than a database error, and the constraint remains
the backstop against a race.

Two different users may hold the same bank, last four digits and account type.

## Ownership And Cross-User Access

Every read and write is scoped by `user_id`. A request for an account owned by
another user returns `ACCOUNT_NOT_FOUND`, identical to a genuinely missing
record, so the API cannot be used to probe for other users' account IDs
(`10-security_standards.md` section 6).

## Audit Behavior

Sprint 2 raises the approved ADR-007 events through the `EventPublisher`
protocol in `app/events/publisher.py`. The default implementation records
nothing.

`audit_log` persistence starts in Sprint 3, as the roadmap requires. Sprint 3
supplies an implementation of the same protocol, so no service logic changes.
An implementation that persists must use the service's own `Session`, so an
audit row can never survive a rolled-back change.

## Error Codes

| Code | Status | Meaning |
| --- | --- | --- |
| `ACCOUNT_NOT_FOUND` | 404 | Missing, or owned by another user. |
| `ACCOUNT_ALREADY_EXISTS` | 409 | Duplicate identity tuple for this user. |
| `VALIDATION_ERROR` | 400 | Invalid field, status transition, or archived-account edit. |

## Test Commands

```powershell
uv run pytest tests\test_account_service.py tests\test_accounts_endpoints.py
uv run pytest
```
