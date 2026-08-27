# Sprint 4 SMS Ingestion

## Purpose

This note documents the implemented Sprint 4 SMS ingestion scope.

## Implemented Scope

- `raw_events` table.
- `POST /api/v1/ingest/sms`.
- API key authentication.
- Exact-message deduplication.
- Foreign key from `transactions.raw_event_id` to `raw_events.id`.

## Endpoint

```http
POST /api/v1/ingest/sms
X-API-KEY: <INGEST_API_KEY>
Content-Type: application/json
```

Request:

```json
{
  "sender": "VK-HDFCBK",
  "message_text": "Rs.70 debited from A/C XXXX0452 at SmartQ",
  "received_at": "2026-06-02T10:00:00Z"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "raw_event_id": "uuid",
    "status": "RECEIVED"
  }
}
```

## Authentication

MacroDroid cannot hold a JWT, so this endpoint authenticates with a shared key
sent as `X-API-KEY` (`10-security_standards.md` section 7). The comparison is
constant-time, so the key cannot be recovered by timing responses.

The path is listed in `PUBLIC_PATHS` in the authentication middleware. Without
that, the bearer-token middleware would reject the request before the API key
was ever checked. The endpoint is not public: it is authenticated by a different
scheme.

## Message Owner

The endpoint carries no JWT, so the owning user comes from the
`INGEST_USER_EMAIL` setting. If it is unset, or names a missing, disabled or
soft-deleted user, ingestion returns `SERVICE_UNAVAILABLE`.

This is an MVP mechanism for the single-user deployment.
`10-security_standards.md` section 7 requires hashed, per-user API keys; those
arrive in Sprint 15 and replace this setting.

## Deduplication

This is the first of the two layers in `04-database_schema.md` section 7.

`message_hash` is the SHA-256 of the sender, the message text and the receipt
timestamp. The timestamp is included on purpose:

- A retry from the sending device replays the identical payload and is caught
  here.
- Two genuinely separate but identically worded purchases arrive with different
  timestamps, so both are stored. If they turn out to be the same transaction,
  the transaction fingerprint from Sprint 3 catches it downstream.

A replay returns HTTP 201 with `status: "DUPLICATE"` rather than an error, so a
retrying sender does not treat it as a failure and keep retrying.

The unique index `uq_raw_events_user_message_hash` is the backstop against a
race between two concurrent deliveries of the same message.

## Immutability

Raw events are the source of truth for every transaction derived from them and
are retained permanently (`04-database_schema.md` sections 2.4 and 9).
`RawEventRepository` exposes no delete method. Only `processing_status` and
`processing_error` change after insert.

The raw event is committed **before** any downstream processing runs, so a
parser failure can never lose the original message. A failure is recorded as
`FAILED` against the stored event.

## Processing Status

```text
RECEIVED
PARSED
PROCESSED
DUPLICATE
IGNORED
FAILED
UNKNOWN_FORMAT
NEEDS_REVIEW
```

Sprint 4 stops at `RECEIVED`. Sprint 5 attaches the parser to the service's
`processor` hook and moves the status on.

## Error Codes

| Code | Status | Meaning |
| --- | --- | --- |
| `INVALID_TOKEN` | 401 | API key missing or wrong. |
| `SERVICE_UNAVAILABLE` | 503 | No ingestion owner configured. |
| `VALIDATION_ERROR` | 400 | Empty or oversized message text. |

## Test Commands

```powershell
uv run pytest tests\test_ingestion.py
uv run pytest
```
