# Sprint 5 Parsing Engine

## Purpose

This note documents the implemented Sprint 5 SMS parsing engine.

## Implemented Scope

- `BaseParser` contract and `ParseResult` value objects.
- ICICI, HDFC, SBI and generic fallback parsers.
- Amount, direction, account, merchant, reference and timestamp extraction.
- Parser registry with sender-based selection.
- Confidence scoring.

## Module Layout

```text
app/parser/
├── base.py          BaseParser, ParsedTransaction, ParseResult
├── registry.py      parser selection
├── banks/           icici.py, hdfc.py, sbi.py, generic.py
└── extractors/      amount, direction, account, merchant, timestamp
```

## Parsers Are Pure

Parsers take text and return a value object. They never touch the database,
which is what makes the whole engine testable against a corpus of real message
shapes. Resolving an account, merchant or category from a parse result is the
pipeline's job, not the parser's.

## Parser Selection

Bank parsers are tried in registration order, and the generic parser runs last,
so adding a bank never changes how existing messages parse.

Selection matches a bank token against the **sender ID** only. Indian bank SMS
senders look like `VK-HDFCBK` or `AD-ICICIB`: a circle prefix, a hyphen, then the
bank token. Matching the token alone survives the prefix changing between circles
and operators.

The message body is deliberately not searched when a sender is present. Bodies
routinely name other banks: in `Rs.150 debited from A/c XX0452 to VPA
swiggy@icici`, the `icici` is the *counterparty's* payment provider, not the
sender's bank. Matching on the body would hand an HDFC message to the ICICI
parser and attribute the transaction to the wrong bank. The body is used only
when no sender was supplied at all.

`SBI` is matched with a token boundary, so `SBIWALA STORE` in a message body
does not claim it.

## Extraction Rules

**Amount.** Balance clauses are removed before the amount is read. Most messages
state both the amount and the resulting balance, and the balance is frequently
the larger and later number, so a naive scan picks the wrong one. Indian digit
grouping (`1,02,345.00`) is handled.

**Direction.** Whichever of the debit or credit keywords appears first wins.
Banks lead with the action, and a later mention usually belongs to an advisory
clause such as "will be credited back if disputed".

**Account.** Banks disclose only a masked tail (`XXXX0452`, `xx9012`, `****5566`),
so the last four digits plus the bank name are what identify the account
downstream. A `Credit Card` mention yields a `CREDIT_CARD` account-type hint.

**Merchant.** Returned exactly as the bank wrote it. Mapping `UPISWIGGY@ICICI`
to `Swiggy` is the merchant engine's job in Sprint 6. Patterns are ordered most
specific first, so the VPA form wins over the generic "to X" form rather than
capturing the literal `VPA ` prefix.

**Timestamp.** Day-first, matching Indian bank convention: `06-07-2026` is 6 July,
not 7 June.

## Non-Transactional Messages

OTPs, due-date reminders, scheduled-debit notices, collect requests and
marketing all quote amounts but are not transactions. They are classified as
`is_transactional = False` rather than reported as parse failures, so genuine
failures are not buried in noise. The pipeline ignores them.

A message that looks transactional but cannot be read fails explicitly with a
reason rather than being guessed at. A wrong transaction is far more expensive
to undo than a missing one.

## Confidence Scoring

Confidence reflects field coverage, not certainty about the amount. It starts at
0.50 and rises with the merchant, account digits, reference number and
timestamp, capped at 1.00. Downstream consumers use it to decide whether to ask
the user to confirm.

## Test Commands

```powershell
uv run pytest tests\test_parser_engine.py
uv run pytest
```

Message samples live in `tests/fixtures/sms_samples.py`. Adding a new bank
format means adding a sample there first.
