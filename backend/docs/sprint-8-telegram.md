# Sprint 8 Telegram Bot

## Purpose

This note documents the Telegram feedback loop.

## Implemented Scope

- Transaction notifications driven by domain events.
- Webhook endpoint with secret-token authentication.
- `/start`, `/help`, `/accounts` and `/settings` commands.
- Notification-mode preferences.
- Off by default behind `ENABLE_TELEGRAM`.

## Configuration

| Variable | Purpose |
| --- | --- |
| `ENABLE_TELEGRAM` | Master switch. Default `false`. |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather. |
| `TELEGRAM_WEBHOOK_SECRET` | Secret token Telegram sends on every webhook call. |

A user receives notifications only once `users.telegram_chat_id` is set.

## Transport Abstraction

Every client satisfies the `TelegramClient` protocol:

| Client | Use |
| --- | --- |
| `HttpTelegramClient` | Calls the Bot API over HTTPS. |
| `NullTelegramClient` | Used when disabled or unconfigured. Drops messages. |
| `FakeTelegramClient` | Records what would have been sent. Used in tests. |

`NullTelegramClient.send_message` returns `False` rather than raising, so a
disabled integration behaves exactly like an unreachable one and every caller
stays on one code path. A deployment with `ENABLE_TELEGRAM=true` but no token
degrades to silence rather than erroring on every transaction.

This is what lets the whole feature be built and tested without a bot token.

## Notifications Are Event-Driven

`TelegramNotifier` implements the `EventPublisher` protocol, so no service ever
calls Telegram directly — `12-coding_standards.md` section 23 forbids
`transaction_service.send_telegram()`.

Two publisher combinators make this work:

- `CompositeEventPublisher` fans one event out to the audit service and the
  notifier. A failing publisher is logged and skipped, so a notification problem
  can never cost an audit row.
- `BufferedEventPublisher` holds events until the caller commits. Sending inside
  the transaction would announce a transaction that then rolled back, and would
  put network latency on the critical path.

The pipeline flushes the buffer only after the transaction is durably committed,
and discards it when the transaction turns out to be a duplicate — so a replayed
SMS never re-notifies the user about money they already saw.

## Failure Isolation

A Telegram outage never propagates. `HttpTelegramClient` reports transport
failures rather than raising, and `TelegramNotifier.publish` swallows anything
that escapes. Telegram being down must not affect SMS processing or transaction
creation (`09-error_handling_standards.md` section 13).

## Notification Modes

| Mode | Behavior |
| --- | --- |
| `ALWAYS` | Notify on every transaction. |
| `LOW_CONFIDENCE_ONLY` | Notify only when parser confidence is 0.80 or lower. Default. |
| `DISABLED` | Never notify. |
| `DAILY_SUMMARY`, `WEEKLY_SUMMARY` | Reserved for a scheduled digest job. |

A transaction with no confidence score was entered by hand rather than parsed,
so `LOW_CONFIDENCE_ONLY` does not flag it: there is nothing uncertain to review.

## Webhook Security

```http
POST /api/v1/telegram/webhook
X-Telegram-Bot-Api-Secret-Token: <TELEGRAM_WEBHOOK_SECRET>
```

The path is listed in `PUBLIC_PATHS` because it is authenticated by the secret
token rather than a JWT. It is not public: an unauthenticated caller is
rejected, and the comparison is constant-time.

If no secret is configured the webhook **refuses everything**, so a
misconfiguration cannot silently expose it.

The endpoint always returns 200. A non-2xx response makes Telegram retry the
same update indefinitely, so handler errors are logged and reported as
`handled: false` instead.

## Command Safety

Commands are read-only. A Telegram chat is identified only by its chat ID, which
is not a credential, so the bot cannot modify financial records
(`10-security_standards.md` section 6). `/start` and `/help` work for anyone;
`/accounts` and `/settings` require a linked user and otherwise explain how to
link.

Merchant text from bank SMS is HTML-escaped before it is sent, since messages
are rendered with `parse_mode: HTML`.

## Test Commands

```powershell
uv run pytest tests\test_telegram.py
uv run pytest
```
