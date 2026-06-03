# 09-error_handling_standards.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Error Handling Standards

Architecture Style: Modular Monolith

Framework: FastAPI

Database: PostgreSQL

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines the standardized error handling strategy for the Personal Finance Tracking Platform.

The goals are:

* Prevent silent failures
* Improve debugging
* Improve observability
* Improve user experience
* Support future SaaS operations
* Enable consistent API responses
* Support auditability

This document applies to:

* APIs
* Services
* Repositories
* Telegram Integration
* SMS Ingestion
* Batch Processing
* Authentication
* Future AI Components

---

# 2. Error Handling Principles

## Principle 1

Never fail silently.

Bad:

```python
try:
    process()
except:
    pass
```

Forbidden.

---

## Principle 2

All exceptions must be logged.

Minimum:

```text
Timestamp
User ID
Request ID
Correlation ID
Exception Type
Error Message
Stack Trace
```

---

## Principle 3

Users should receive understandable errors.

Bad:

```json
{
  "error": "IntegrityError"
}
```

Good:

```json
{
  "error": {
    "code": "ACCOUNT_ALREADY_EXISTS",
    "message": "An account with these details already exists."
  }
}
```

---

## Principle 4

Internal details must not leak.

Never expose:

* Stack traces
* SQL queries
* Database credentials
* Internal file paths

to API consumers.

---

## Principle 5

Raw events must survive failures.

If processing fails:

```text
Raw Event
MUST remain stored
```

for reprocessing.

---

## Principle 6

Financial data must not be partially committed.

Use database transactions.

Example:

```text
Transaction Created
Balance Update Failed
```

Must rollback.

---

# 3. Error Classification

Errors are classified into categories.

---

# Category 1

Validation Errors

Cause:

Invalid client input.

Examples:

* Missing fields
* Invalid UUID
* Invalid enum
* Invalid date range

HTTP Status:

```text
400
```

---

# Category 2

Authentication Errors

Cause:

Identity problems.

Examples:

* Invalid JWT
* Expired JWT
* Invalid credentials

HTTP Status:

```text
401
```

---

# Category 3

Authorization Errors

Cause:

Access violation.

Examples:

* User accessing another user's transaction
* User accessing another user's account

HTTP Status:

```text
403
```

---

# Category 4

Resource Not Found

Cause:

Record does not exist.

Examples:

* Account not found
* Transaction not found
* Category not found

HTTP Status:

```text
404
```

---

# Category 5

Conflict Errors

Cause:

Duplicate or conflicting state.

Examples:

* Duplicate account
* Duplicate category
* Duplicate transaction fingerprint

HTTP Status:

```text
409
```

---

# Category 6

Business Rule Violations

Cause:

Domain rules violated.

Examples:

* Transfer linking different users
* Reconcile archived account
* Delete protected category

HTTP Status:

```text
422
```

---

# Category 7

External Integration Errors

Cause:

External dependency failure.

Examples:

* Telegram unavailable
* SMTP unavailable
* AA unavailable

HTTP Status:

```text
503
```

---

# Category 8

Infrastructure Errors

Cause:

Internal technical failures.

Examples:

* PostgreSQL unavailable
* Redis unavailable
* Disk full

HTTP Status:

```text
500
```

---

# 4. Standard Error Response

Every error response must follow:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "request_id": "uuid",
    "correlation_id": "uuid"
  }
}
```

---

# 5. Error Codes

---

## Validation Errors

```text
VALIDATION_ERROR

INVALID_UUID

INVALID_DATE

INVALID_AMOUNT

INVALID_CURRENCY

INVALID_CATEGORY

INVALID_ACCOUNT_TYPE
```

---

## Authentication Errors

```text
INVALID_CREDENTIALS

INVALID_TOKEN

TOKEN_EXPIRED

ACCOUNT_DISABLED
```

---

## Authorization Errors

```text
ACCESS_DENIED

USER_MISMATCH

RESOURCE_FORBIDDEN
```

---

## Resource Errors

```text
USER_NOT_FOUND

ACCOUNT_NOT_FOUND

TRANSACTION_NOT_FOUND

CATEGORY_NOT_FOUND

MERCHANT_NOT_FOUND

TRANSFER_NOT_FOUND
```

---

## Conflict Errors

```text
ACCOUNT_ALREADY_EXISTS

CATEGORY_ALREADY_EXISTS

DUPLICATE_TRANSACTION

DUPLICATE_FINGERPRINT

DUPLICATE_RAW_EVENT
```

---

## Business Rule Errors

```text
TRANSFER_USER_MISMATCH

INVALID_TRANSFER

INVALID_BALANCE_RECONCILIATION

SYSTEM_CATEGORY_PROTECTED

AUDIT_LOG_IMMUTABLE
```

---

## Infrastructure Errors

```text
DATABASE_UNAVAILABLE

TELEGRAM_UNAVAILABLE

SMTP_UNAVAILABLE

SERVICE_UNAVAILABLE

UNEXPECTED_ERROR
```

---

# 6. Validation Error Standards

Validation should occur in:

```text
API Layer
```

before entering business logic.

Example:

```python
amount > 0

currency in supported currencies

valid UUID
```

Invalid requests must never reach repositories.

---

# 7. Authentication Error Standards

JWT validation failures:

Return:

```http
401 Unauthorized
```

Example:

```json
{
  "success": false,
  "error": {
    "code": "TOKEN_EXPIRED",
    "message": "Your session has expired."
  }
}
```

---

# 8. Authorization Error Standards

Every user-owned entity must validate ownership.

Example:

```text
transaction.user_id
==
jwt.user_id
```

If mismatch:

```http
403 Forbidden
```

Return:

```json
{
  "success": false,
  "error": {
    "code": "ACCESS_DENIED"
  }
}
```

---

# 9. Database Error Handling

Repository layer must translate database errors.

Never expose:

```text
IntegrityError

ForeignKeyViolation

UniqueViolation
```

Convert to domain errors.

Example:

```text
UniqueViolation
↓
ACCOUNT_ALREADY_EXISTS
```

---

# 10. SMS Ingestion Errors

---

## Invalid SMS Payload

Cause:

Missing sender or message text.

Action:

Reject request.

HTTP:

```text
400
```

---

## Duplicate Raw Event

Cause:

Same message hash.

Action:

Store status as:

```text
DUPLICATE
```

Do not create transaction.

Return:

```http
200
```

Reason:

Duplicate is not a system failure.

---

## Parser Failure

Cause:

Unknown bank format.

Action:

```text
Store Raw Event
Mark FAILED
Store processing_error
```

Do not lose message.

---

# 11. Parser Error Handling

Parser errors must not stop ingestion.

Example:

```text
Raw Event Stored
Parser Failed
```

Result:

```text
processing_status = FAILED
```

User may review later.

---

## Unknown Format

Status:

```text
UNKNOWN_FORMAT
```

Store:

```text
sender

message_text

processing_error
```

---

# 12. Transaction Creation Errors

---

## Duplicate Transaction Fingerprint

Action:

Reject transaction creation.

Store:

```text
DUPLICATE
```

Audit optional.

---

## Missing Account

Action:

Create pending account.

Do not fail.

---

## Missing Merchant

Action:

Use:

```text
Unknown Merchant
```

Do not fail.

---

## Missing Category

Action:

Leave uncategorized.

Do not fail.

---

# 13. Telegram Error Handling

Telegram is non-critical.

Transaction creation must never fail because Telegram failed.

---

## Telegram Down

Action:

```text
Log Error
Retry
Continue
```

Do not rollback transaction.

---

## Telegram Timeout

Action:

Retry.

Maximum:

```text
3 Attempts
```

After:

Store failed notification.

---

# 14. Retry Standards

Only retry transient failures.

Examples:

```text
Telegram Timeout

Database Connection Timeout

Network Failure
```

Do not retry:

```text
Validation Errors

Invalid UUID

Invalid JWT

Duplicate Transaction
```

---

## Retry Policy

Recommended:

```text
Attempt 1
1 Second

Attempt 2
5 Seconds

Attempt 3
30 Seconds
```

After:

Move to dead letter queue table.

---

# 15. Dead Letter Queue Strategy

Create future table:

```text
failed_jobs
```

Purpose:

Store failed processing tasks.

Columns:

```text
id

job_type

payload

error_message

retry_count

created_at
```

---

# 16. Balance Engine Errors

Balance calculation failures are critical.

---

## Rule

Transaction creation and balance update must occur in one database transaction.

Example:

Bad:

```text
Transaction Created
Balance Failed
```

Good:

```text
Transaction Created
Balance Updated
Commit
```

or

```text
Rollback All
```

---

# 17. Audit Log Errors

Audit failures must be treated as critical.

Reason:

Financial traceability.

---

## Rule

If transaction update succeeds:

Audit record must succeed.

Otherwise:

Rollback.

---

# 18. Batch Import Errors

Historical imports must isolate failures.

Example:

1000 messages.

If message 503 fails:

Messages 1-502 remain processed.

Messages 504-1000 continue.

---

## Batch Processing Rule

One failed message must not fail entire batch.

---

# 19. Logging Standards

Every error log must contain:

```text
timestamp

environment

service

module

user_id

request_id

correlation_id

error_code

error_message

stack_trace
```

---

## Example Log

```json
{
  "timestamp": "2026-06-02T10:00:00Z",
  "service": "transaction-service",
  "user_id": "uuid",
  "request_id": "uuid",
  "correlation_id": "uuid",
  "error_code": "DUPLICATE_TRANSACTION",
  "message": "Fingerprint already exists"
}
```

---

# 20. Correlation IDs

Every request must generate:

```text
request_id
```

Every workflow must use:

```text
correlation_id
```

Example:

```text
SMS Received
↓
Parse
↓
Transaction
↓
Balance Update
↓
Telegram
```

All share same correlation ID.

---

# 21. Observability Standards

The platform must support:

* Structured Logging
* Error Metrics
* Processing Metrics
* Failed Event Tracking

Future:

* OpenTelemetry
* Prometheus
* Grafana

---

# 22. AI Error Handling

Future AI modules may fail.

AI failures must never block:

* Transaction Creation
* Balance Updates
* Reporting

AI is advisory only.

---

## Example

AI unavailable.

Result:

```text
Transaction Created
Category = Uncategorized
```

Continue processing.

---

# 23. Error Ownership Matrix

| Error Type          | Owner                |
| ------------------- | -------------------- |
| Validation          | API Layer            |
| Authentication      | Auth Module          |
| Authorization       | Auth Module          |
| Parsing             | Parser Module        |
| Duplicate Detection | Transaction Module   |
| Merchant Resolution | Merchant Module      |
| Balance Calculation | Balance Module       |
| Telegram            | Notification Module  |
| Audit Logging       | Audit Module         |
| Database            | Infrastructure Layer |

---

# 24. AI Agent Implementation Rules

AI coding agents must:

* Use custom exception classes.
* Use centralized exception middleware.
* Use structured logging.
* Translate database errors.
* Include request IDs.
* Include correlation IDs.
* Rollback financial operations on failure.

AI coding agents must not:

* Swallow exceptions.
* Return stack traces.
* Log secrets.
* Ignore audit failures.
* Ignore ownership validation.

---

# 25. Approval

Status: Approved

This document is the authoritative error handling standard for the Personal Finance Tracking Platform.

All APIs, services, repositories, workers, Telegram integrations, and future AI modules must comply with these standards.
