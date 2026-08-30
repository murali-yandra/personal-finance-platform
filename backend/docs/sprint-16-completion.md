# Completion — Contract Endpoints, Sessions, MFA, Scheduler

## Purpose

This note documents the work that closed the remaining gaps after Sprint 15:
the API contract endpoints with no implementation, the two tables that existed
but were never written to, MFA, and the scheduler.

## What Was Missing

An audit of `08-api_contracts.md` against the running app, plus a check for
declared-but-unwired features, found six gaps:

| Gap | Status |
| --- | --- |
| `PATCH /users/me` | Implemented |
| `GET` and `PATCH /settings` | Implemented |
| `POST /telegram/test` | Implemented |
| `user_sessions` table written by nothing | Wired to login, refresh and logout |
| `capture_snapshot` called by nothing | Wired to a scheduled job |
| `DAILY_SUMMARY` / `WEEKLY_SUMMARY` modes did nothing | Wired to digest jobs |

MFA, previously deferred, is also complete.

## Profile And Settings

`PATCH /users/me` covers display name, timezone, default currency and Telegram
chat id. Email is deliberately **not** editable: it is the login identity and
the address an ingestion key resolves against, so changing it needs a
verification flow rather than a PATCH.

Timezones are validated against the real tz database. An unknown zone would
make every date-bounded report silently wrong for that user.

`GET /users/me` now also returns `telegram_chat_id` and `role`. Both are
additive, so v1 consumers are unaffected.

## Session Tracking

A session row is created for every issued refresh token and checked when that
token is exchanged.

This is what makes revocation possible at all. A JWT is self-validating, so
before this a stolen refresh token stayed usable for its full 30-day life and
"sign out everywhere" could not work. Only a SHA-256 digest of the token is
stored, so a leaked sessions table hands over nothing usable.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/auth/logout` | End this session, or every session. |
| GET | `/api/v1/sessions` | List active sessions with address and user agent. |
| DELETE | `/api/v1/sessions/{id}` | Revoke one session. |
| DELETE | `/api/v1/sessions` | Sign out everywhere. |

Logout takes the **refresh token**, not an access token, because the refresh
token is what has a long life and therefore what needs revoking — and because
the moment you most need to log out is when your access token has already
expired. It is public for the same reason `/auth/refresh` is.

Logging out twice reports zero revocations rather than an error. Reporting
otherwise would tell an attacker which tokens are real.

**What revocation does not do:** access tokens live 15 minutes and are
validated without a database lookup, which is what keeps every request cheap.
Revoking a session therefore bounds a stolen login to that window rather than
ending it instantly.

## Multi-Factor Authentication

**Enrolment is two-step.** Generating a secret does not enable MFA; the user
must first produce a code from it. Enabling on generation alone would lock out
anyone whose authenticator failed to scan the QR code, with no way back in. An
abandoned enrolment can simply be restarted.

**Recovery codes cover the other lockout path.** Ten single-use codes are issued
at enrolment, stored Argon2 hashed, and marked used rather than deleted so a
replay is refused. They work anywhere a TOTP code does, including at login, so
a lost phone does not mean a lost account.

Disabling MFA and regenerating recovery codes both require a valid code.
Otherwise anyone holding a stolen access token could strip the protection MFA
exists to provide.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/v1/mfa` | Status and remaining recovery codes. |
| POST | `/api/v1/mfa/enrol` | Generate a secret and recovery codes. Returned once. |
| POST | `/api/v1/mfa/confirm` | Enable MFA with a valid code. |
| POST | `/api/v1/mfa/disable` | Turn MFA off. Requires a code. |
| POST | `/api/v1/mfa/recovery-codes` | Replace the codes. Requires a code. |

At login the second factor is checked after the password and before any token
is issued, so a correct password alone yields nothing usable. A missing code
returns `MFA_REQUIRED`; a wrong one returns `INVALID_CREDENTIALS`, so a client
can tell "prompt for a code" from "that code was wrong".

Verification allows one time step either side of now for clock drift. Wider
would meaningfully extend the window in which a shoulder-surfed code works.

## Scheduler

Jobs are plain functions over a `Session`. Nothing owns a timer, so they are
testable without waiting on wall-clock time and the MVP needs no extra
container.

```bash
python -m app.scheduler.cli balance-snapshots
python -m app.scheduler.cli daily-digest
python -m app.scheduler.cli weekly-digest --date 2026-06-15
```

The CLI exits non-zero when a job reports failures, so a scheduler surfaces the
problem instead of a nightly job failing unnoticed for weeks.

**Balance snapshots** record every non-archived account's balance for the day.
The write is an upsert keyed on account and date, so a scheduler that retries,
fires late or overlaps updates rather than duplicating.

**Digests** send a summary to users on `DAILY_SUMMARY` or `WEEKLY_SUMMARY`.
Design points:

- A day with no transactions sends nothing. A digest saying nothing happened is
  how users end up muting the bot entirely.
- Transfers are excluded, consistent with every other report.
- One delivery failure does not abort the run for everyone else.

`render.yaml` declares both as cron services. They need a paid plan; on the
free tier, run them from any external scheduler against the same image.

## Test Commands

```powershell
uv run pytest tests\test_profile_and_sessions.py tests\test_mfa.py tests\test_scheduler.py
uv run pytest
```
