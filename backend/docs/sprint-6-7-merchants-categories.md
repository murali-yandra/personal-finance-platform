# Sprints 6 and 7 — Merchant Engine And Categories

## Purpose

This note documents merchant normalization, category management, and the SMS
pipeline that joins Sprints 4 through 7 together.

## Implemented Scope

- `merchants`, `merchant_patterns` and `categories` tables.
- Merchant resolution with EXACT, LIKE and REGEX patterns.
- System and user categories, with the 14 approved system categories seeded.
- The end-to-end pipeline: raw event to transaction.
- The remaining deferred foreign keys from migration 0004.

## Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/v1/merchants` | Paginated merchant list with search. |
| POST | `/api/v1/merchants` | Create, or return the existing same-named merchant. |
| GET | `/api/v1/merchants/{merchant_id}` | Return one merchant. |
| GET | `/api/v1/merchants/patterns` | Caller's patterns plus every global pattern. |
| POST | `/api/v1/merchants/patterns` | Create a pattern owned by the caller. |
| GET | `/api/v1/categories` | System categories plus the caller's own. |
| POST | `/api/v1/categories` | Create a category owned by the caller. |
| PATCH | `/api/v1/categories/{category_id}` | Rename or re-parent an owned category. |

`/merchants/patterns` is registered before `/merchants/{merchant_id}` so the
literal path is not parsed as a UUID.

## Merchant Resolution

```text
UPISWIGGY@ICICI
↓
Swiggy
```

Patterns are ranked before matching:

1. **User patterns beat global patterns.** A personal correction is never
   overridden by a shared rule.
2. **EXACT beats LIKE beats REGEX.** A literal match is stronger evidence than a
   wildcard, which is stronger than a regex written to catch a family of strings.
3. **Longer patterns beat shorter ones** within the same type.

`LIKE` follows SQL semantics: `%` is any run, `_` is one character.

An invalid stored regex is skipped with a warning rather than aborting
resolution, because patterns can be user-supplied and one bad expression must
not disable every other rule. Invalid regexes are also rejected at write time,
so the failure surfaces when the pattern is created rather than silently at
every match.

When nothing matches, the merchant is left unresolved rather than guessed.
A wrongly attributed merchant quietly corrupts every report that groups by
merchant; an unresolved one is recoverable.

## Categories

A system category has `user_id IS NULL` and `is_system = TRUE`. It is shared by
every user and cannot be modified or deleted — attempts return
`SYSTEM_CATEGORY_PROTECTED`.

Uniqueness uses two partial indexes rather than one composite unique index. A
plain unique on `(user_id, name)` would not constrain system rows at all,
because `NULL` is never equal to `NULL` in SQL:

```sql
CREATE UNIQUE INDEX uq_system_category_name ON categories(name)
  WHERE user_id IS NULL;
CREATE UNIQUE INDEX uq_user_category_name ON categories(user_id, name)
  WHERE user_id IS NOT NULL;
```

A user may reuse a system category's name, since the two live in separate
uniqueness scopes. Two different users may also use the same name.

## The SMS Pipeline

```text
raw event -> parse -> resolve account -> resolve merchant -> resolve category
          -> create transaction -> TransactionCreated
```

Processing runs synchronously inside the ingestion request. MVP deploys only a
backend and a database container (`11-deployment_standards.md` section 5), so
there is no worker to hand off to, and the five-second SMS-to-transaction budget
(`14-sprint_roadmap.md` section 26) is met comfortably.

The raw event is committed before the pipeline runs, so every outcome is
recorded against a stored message rather than lost.

### Account resolution

An unrecognized account is created as `PENDING` and the message is flagged
`NEEDS_REVIEW`. The transaction is real money and must be recorded; the user
confirms the account details afterwards.

An **archived** account still matches. Archiving says the user stopped using the
account, but a bank message says money moved on it anyway, and the
`uq_user_bank_lastfour_type` constraint would reject a second account with the
same bank and digits. So the transaction is posted to the real account, the
account stays archived so the user's decision is not silently reversed, and the
message is flagged `NEEDS_REVIEW` so they are asked about the conflict. A live
account is always preferred over an archived one.

This is the only path allowed to post to an archived account. The manual
transaction API still rejects it.

### Processing status outcomes

| Status | Meaning |
| --- | --- |
| `PROCESSED` | Transaction created against a known account. |
| `NEEDS_REVIEW` | Created, but the account was new or archived. |
| `DUPLICATE` | The transaction fingerprint already exists. |
| `IGNORED` | Not a transaction: an OTP, reminder or marketing message. |
| `UNKNOWN_FORMAT` | Looks transactional but could not be read. |

`IGNORED` and `UNKNOWN_FORMAT` are deliberately distinct. Burying OTPs and
due-date reminders in the failure queue would hide genuine parser gaps.

## Deferred Foreign Keys

Migration 0004 created `transactions` before `raw_events`, `merchants` and
`categories` existed. Those columns carried the correct types but no
constraints. The constraints are attached by:

| Migration | Foreign key |
| --- | --- |
| 0006 | `transactions.raw_event_id` |
| 0007 | `transactions.merchant_id` |
| 0008 | `transactions.category_id`, `merchants.default_category_id` |

An integration test asserts all three transaction foreign keys exist after
`alembic upgrade head`.

## Test Commands

```powershell
uv run pytest tests\test_merchant_engine.py tests\test_categories.py tests\test_sms_pipeline.py
uv run pytest
```
