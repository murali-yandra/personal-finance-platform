# Sprints 11 to 13 — Historical Import, AI Foundation, Learning Engine

## Purpose

This note documents bulk import, model-backed suggestions, and learning from
user corrections.

## Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/ingest/sms/batch` | Import up to 1000 historical messages. |
| POST | `/api/v1/ingest/reprocess` | Re-run stored messages that produced no transaction. |
| GET | `/api/v1/ai/status` | Whether AI is enabled and the provider answers. |
| GET | `/api/v1/ai/suggestions` | List stored suggestions. |
| POST | `/api/v1/ai/suggestions/{id}/review` | Accept or reject a suggestion. |
| GET | `/api/v1/ai/feedback` | List recorded corrections. |
| POST | `/api/v1/ai/feedback/merchant` | Correct a merchant and learn a rule. |

## Sprint 11 — Historical Import

Each message in a batch is stored and processed independently, and the response
reports per-outcome counts (`accepted`, `duplicates`, `failed`, `ignored`)
rather than failing the request. One unreadable message in a year of history
must not discard the rest of the import, so the endpoint returns 202 with the
tally.

Re-importing an overlapping window is safe: the existing two-layer
deduplication catches replays, so `duplicates` rises and no money is
double-counted.

**Reprocessing** re-runs raw events that never produced a transaction. This is
how a parser improvement is applied to history — raw events are retained
permanently precisely so they can be re-read later. Only `FAILED`,
`UNKNOWN_FORMAT` and `RECEIVED` events are eligible: an `IGNORED` message is an
OTP rather than a parser gap, and a `PROCESSED` one would only produce a
duplicate.

## Sprint 12 — AI Foundation

```text
app/ai/
├── adapters/     BaseAIProvider, OllamaProvider, FakeAIProvider
├── prompts/      versioned templates
├── services/     the only code allowed to call a model
├── validators/   response parsing and rejection
└── schemas/      suggestions and confidence bands
```

**Failure is a value, not an exception.** `AIResponse.failure(...)` means callers
cannot forget to handle an outage and accidentally take the pipeline down with
it. `AISuggestionService` additionally catches anything a provider raises. AI
failure must never block SMS processing, transaction creation, balance updates
or reporting (`13-ai_integration_standards.md` section 22).

**Every response is validated** (section 19). A model can return prose, wrap
JSON in a code fence, answer `85` when asked for `0.85`, or invent a category
that does not exist. The validator extracts embedded JSON, normalizes a
percentage confidence, and rejects any category outside the allowed set.
Anything untrustworthy yields no suggestion: an absent suggestion is harmless,
a fabricated one silently corrupts financial history.

**Suggestions are stored, not applied.** Only a `HIGH` band suggestion
(confidence at or above 0.90) may be auto-applied; everything else waits for the
user (section 9). A wrong category quietly corrupts every report grouped by
category.

**Prompts carry only the merchant string and amount.** Account numbers,
balances and raw message text never reach a model (section 26). A test asserts
this.

Prompts are versioned (`PROMPT_VERSION`), and the version and model name are
stored on every suggestion so it can be traced to what produced it.

## Sprint 13 — Learning Engine

The roadmap example:

```text
KA51AJ*
↓
Transport
```

A merchant correction records `UserFeedback` and creates a **user-owned**
merchant pattern. Rules learned this way are never global: one person's
preference must not reclassify everyone else's history. Because user patterns
outrank global ones, a correction also overrides a shared rule that got it
wrong.

### Deriving the pattern

Bank merchant strings carry a stable part and a varying tail — `KA51AJ1234` and
`KA51AJ5678` are the same bus operator with different vehicles. The trailing
digit run is dropped so the rule generalizes, and the result is wrapped as
`%...%` so it matches anywhere in a future string.

The pattern is derived from the **original** text, not a punctuation-stripped
version. Stripping first produced `UPISWIGGYICICI%`, which never matches
`UPISWIGGY@ICICI` — a rule that failed to match the very string it was learned
from. A test now asserts that invariant across several shapes.

Literal `%` and `_` characters are removed from the derived core: a `%` in a
bank string is not a wildcard, and leaving it in would silently widen the rule
to match everything.

## Configuration

| Variable | Purpose |
| --- | --- |
| `ENABLE_AI` | Master switch. Default `false`. |
| `OLLAMA_BASE_URL` | Ollama server. Default `http://localhost:11434`. |
| `OLLAMA_MODEL` | Model name. Default `qwen3`. |

With AI disabled the factory returns a provider that reports itself
unavailable, so callers need no special case for the disabled path.

## Test Commands

```powershell
uv run pytest tests\test_historical_import.py tests\test_ai_engine.py
uv run pytest
```
