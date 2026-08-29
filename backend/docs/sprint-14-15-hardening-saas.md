# Sprints 14 and 15 — Production Hardening And SaaS Preparation

## Purpose

This note documents structured logging, rate limiting, per-user API keys, roles,
session tracking, admin APIs, backups, and the security review.

## Sprint 14 — Production Hardening

### Structured logging

Every log line is JSON carrying the fields `10-security_standards.md` section 11
requires: timestamp, request id, correlation id, user id, module and level.

Ids live in context variables, so any module logs them without threading them
through every call signature. Context variables are per-task, so concurrent
requests never see each other's ids.

### Redaction

Masking happens in the **formatter**, not at call sites. A new log line cannot
leak a secret by forgetting to mask it.

Two paths are covered:

- **Message text** — `password=`, `Bearer <token>`, bare JWTs, and 12-to-19 digit
  card or account numbers are redacted wherever they appear.
- **Structured fields** — a value passed as `extra={"token": ...}` has its name
  as a dict key rather than in the text, so field names are checked separately.
  Without this a secret passed structurally was logged verbatim.

Account numbers are masked to the form the standard requires: `1234567890`
becomes `******7890`.

### Request correlation

`RequestContextMiddleware` binds a request id and correlation id for each
request and echoes both on the response, so a client-visible error joins to the
log lines and audit rows it produced. A caller-supplied correlation id is
honoured, which is what lets one id span the ingestion request, the transaction
it creates and the notification it sends.

**Client-supplied ids are validated as UUIDs, not trusted.** They flow into logs
and audit rows, so an arbitrary string would let a caller inject content into
the log stream. `audit_log.request_id` was already a UUID column and silently
dropped non-UUIDs; the error envelope was echoing them. Both are now consistent.

The middleware is registered last so it runs first: every other layer, including
authentication failures, is logged with a request id.

### Backups

`scripts/backup.sh` takes a custom-format `pg_dump`, then:

- fails if the dump is empty or implausibly small,
- verifies the archive is readable with `pg_restore --list`,
- prunes old backups **only after** a verified backup succeeds.

Financial records are retained forever (`04-database_schema.md` section 9), so a
backup that silently produced nothing is worse than none at all: the failure
would not be noticed until a restore was needed.

### Security review

Run over the whole branch. Findings: none outstanding.

| Check | Result |
| --- | --- |
| Secrets committed to git | None. No `.env` tracked, no hardcoded secrets. |
| Plaintext credentials stored | None. Passwords and API keys are Argon2 hashed. |
| SQL injection surface | None. No f-string or formatted SQL anywhere in `app/`. |
| Routes bypassing authentication | None. All 49 `/api/v1` routes are authenticated or explicitly listed as public with a different scheme. |
| Cross-user data access | Every repository filters by `user_id`. |
| Internal detail in error responses | None. Exception text is logged, never returned. |
| Credentials in log calls | None. |

## Sprint 15 — SaaS Preparation

### Roles

`users.role` holds `USER` or `ADMIN`. `require_role(...)` builds a dependency
that admits only the listed roles.

**The role is read from the user record, not the JWT claim.** A token outlives a
role change, so trusting the claim would let a demoted admin keep access until
their token expired. A test asserts a demotion takes effect immediately on an
already-issued token.

### Rate limiting

100 requests per minute per caller (`10-security_standards.md` section 7),
configurable via `RATE_LIMIT_PER_MINUTE`. Keyed by authenticated user where
known, otherwise by API key digest or client address, so one user's burst cannot
exhaust another's allowance.

Health endpoints are never throttled: a throttled probe would make a busy
platform look unhealthy and trigger a restart.

This is an in-process fixed-window counter, correct for the single-container
MVP. A multi-container deployment needs a shared store such as Redis; the
limiter is written so that is a change of backend rather than of call sites.

### Per-user API keys

Replaces the single `INGEST_API_KEY`. Keys are `pfp_`-prefixed random tokens,
returned exactly once and stored only as a hash.

Authentication is two-step: a deterministic SHA-256 **lookup hash** finds the
candidate row, then Argon2 verifies the secret. Pure Argon2 would need one
expensive verification per stored key on every request; pure SHA-256 would leave
keys exposed if the table leaked. This gets a single indexed lookup plus a slow,
salted verification.

The environment key still works, so an existing deployment keeps running across
the upgrade. Remove it once every device holds its own key.

### Sessions

`user_sessions` records issued sessions with only a hash of the refresh token,
for the same reason passwords are hashed. This is what makes "sign out
everywhere" and suspicious-login review possible.

### Admin APIs

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/v1/admin/users` | Paginated user list. |
| PATCH | `/api/v1/admin/users/{id}/role` | Change a user's role. |
| PATCH | `/api/v1/admin/users/{id}/status` | Enable or disable a user. |
| GET | `/api/v1/admin/stats` | Aggregate platform counts. |

Responses deliberately carry no financial detail: an administrator manages
accounts and access, and does not need to read anyone's transactions to do it.

An admin cannot disable their own account — a sole admin doing so would lock the
platform out of administration entirely.

### Multi-factor authentication

Not implemented. It is the one Sprint 15 item left open: TOTP enrolment needs a
user-facing enrolment and recovery-code flow, and shipping half of it would give
the appearance of a second factor without the recovery path that makes it safe.
The `user_sessions` table it builds on is in place.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `RATE_LIMIT_ENABLED` | `true` | Master switch for throttling. |
| `RATE_LIMIT_PER_MINUTE` | `100` | Requests per caller per minute. |

## Test Commands

```powershell
uv run pytest tests\test_hardening.py
uv run pytest
```
