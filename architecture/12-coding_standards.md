# 12-coding_standards.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Coding Standards

Framework: FastAPI

ORM: SQLModel

Database: PostgreSQL

Language: Python 3.12+

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines the coding standards for the Personal Finance Tracking Platform.

The goals are:

* Maintainability
* Consistency
* Readability
* Scalability
* Testability
* AI-Agent Compatibility

This document is the authoritative source for:

* Backend Development
* AI Code Generation
* Code Reviews
* Pull Requests
* Repository Structure

---

# 2. Core Principles

## Principle 1

Code should be easy to understand.

Prefer:

```python
estimated_balance = account.balance + transaction.amount
```

Avoid:

```python
eb = b + amt
```

---

## Principle 2

Explicit is better than implicit.

---

## Principle 3

Business logic belongs in services.

Never in:

* Controllers
* API Routes
* Repositories
* Models

---

## Principle 4

Financial calculations must be deterministic.

Use:

```python
Decimal
```

Never:

```python
float
```

---

## Principle 5

Code must be AI-friendly.

AI agents should easily understand:

* Naming
* Structure
* Boundaries
* Responsibilities

---

# 3. Project Structure

Required structure:

```text
backend/

src/
│
├── api/
│   ├── v1/
│   └── dependencies/
│
├── auth/
│
├── accounts/
│
├── transactions/
│
├── categories/
│
├── merchants/
│
├── transfers/
│
├── reporting/
│
├── telegram/
│
├── ingestion/
│
├── parser/
│
├── audit/
│
├── settings/
│
├── ai/
│
├── common/
│
├── database/
│
├── events/
│
├── scheduler/
│
└── tests/
```

---

# 4. Layered Architecture

Every module must follow:

```text
API
↓
Service
↓
Repository
↓
Database
```

---

## Forbidden

```text
API
↓
Database
```

---

## Forbidden

```text
Service
↓
Raw SQL Everywhere
```

---

# 5. Module Structure

Example:

```text
transactions/

├── models.py
├── schemas.py
├── repository.py
├── service.py
├── exceptions.py
├── constants.py
├── events.py
└── tests/
```

---

# 6. Naming Standards

## Classes

PascalCase

Example:

```python
TransactionService

TransactionRepository

CreateTransactionRequest
```

---

## Functions

snake_case

Example:

```python
create_transaction()

resolve_merchant()

update_balance()
```

---

## Variables

snake_case

Example:

```python
transaction_amount

account_balance

merchant_name
```

---

## Constants

UPPER_CASE

Example:

```python
MAX_RETRY_COUNT = 3

DEFAULT_CURRENCY = "INR"
```

---

# 7. File Naming Standards

Use:

```text
snake_case.py
```

Examples:

```text
transaction_service.py

merchant_resolver.py

balance_engine.py
```

Avoid:

```text
TransactionService.py

BalanceEngine.py
```

---

# 8. API Standards

API routes must remain thin.

Allowed:

```python
@router.post("/")
async def create():
    return service.create()
```

---

Forbidden:

```python
@router.post("/")
async def create():

    query = session.query(...)

    ...

    business_logic()

    ...
```

---

# 9. Service Layer Standards

Services contain:

* Business Rules
* Domain Logic
* Validation
* Event Publishing

Example:

```python
class TransactionService:

    def create_transaction(self):
        ...
```

---

Services must not:

* Return ORM objects directly
* Execute raw SQL
* Access HTTP Request Objects

---

# 10. Repository Standards

Repositories handle:

* Queries
* Persistence
* Filtering

Only.

---

Example:

```python
class TransactionRepository:
    def get_by_id(self):
        ...
```

---

Repositories must not:

* Contain business rules
* Publish events
* Call Telegram APIs

---

# 11. DTO Standards

Request Models:

```python
CreateTransactionRequest
```

Response Models:

```python
TransactionResponse
```

Update Models:

```python
UpdateTransactionRequest
```

---

Forbidden:

```python
TransactionDTO
```

Too generic.

---

# 12. SQLModel Standards

Every model:

```python
class Transaction(SQLModel, table=True):
```

Must use:

```python
UUID
```

Primary keys.

---

Example:

```python
id: UUID = Field(default_factory=uuid4)
```

---

# 13. Money Standards

All money fields:

```python
Decimal("70.129").quantize(
    Decimal("0.01"),
    ROUND_HALF_UP
)
```

Database:

```python
NUMERIC(18,2)
```

---

Forbidden:

```python
float
```

Reason:

Floating point inaccuracies.

---

# 14. Enum Standards

Use enums.

Example:

```python
class TransactionType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
```

---

Avoid:

```python
transaction.type = "debit"
```

---

# 15. Validation Standards

Use:

```python
Pydantic
```

Validation occurs before service layer.

Example:

```python
amount > 0
```

---

Invalid requests must never reach repositories.

---

# 16. Exception Standards

Create custom exceptions.

Example:

```python
TransactionNotFoundException

AccountNotFoundException

DuplicateTransactionException
```

---

Avoid:

```python
raise Exception()
```

---

# 17. Logging Standards

Use:

```python
structlog
```

Preferred.

Alternative:

```python
logging
```

---

Every log must include:

```text
request_id

correlation_id

user_id
```

when available.

---

# 18. Audit Standards

Any user-driven change must create:

```text
audit_log
```

Examples:

```text
Category Change

Description Change

Account Rename

Balance Reconciliation
```

---

# 19. Transaction Management

Financial operations must use:

```python
database transaction
```

---

Example:

```text
Create Transaction
Update Balance
Create Audit Log
Commit
```

or

```text
Rollback
```

---

# 20. Dependency Injection Standards

Use FastAPI DI.

Example:

```python
Depends(get_current_user)
```

---

Avoid:

```python
global database_session
```

---

# 21. Event Standards

Use domain events.

Example:

```python
TransactionCreatedEvent

AccountCreatedEvent

FeedbackReceivedEvent
```

---

Format:

```python
PastTenseEvent
```

---

# 22. Parser Standards

Every bank parser:

```python
BaseParser
```

must implement:

```python
parse()
```

---

Example:

```python
ICICIParser

HDFCParser

SBIParser
```

---

# 23. Telegram Standards

Telegram integration belongs only inside:

```text
telegram/
```

---

Forbidden:

```python
transaction_service.send_telegram()
```

Use events.

---

# 24. Configuration Standards

All config comes from:

```env
.env
```

---

Never:

```python
JWT_SECRET = "secret"
```

---

Use:

```python
Settings()
```

pattern.

---

# 25. Testing Standards

Minimum:

```text
80% Coverage
```

Target:

```text
90%+
```

---

# 26. Unit Test Standards

Every service must have tests.

Example:

```python
test_create_transaction()

test_duplicate_transaction()

test_balance_update()
```

---

# 27. Integration Test Standards

Required for:

```text
API

Database

Authentication

Telegram
```

---

# 28. Test Naming Standards

Format:

```python
test_<action>_<expected_result>()
```

Example:

```python
test_create_transaction_success()

test_create_transaction_duplicate()
```

---

# 29. Git Standards

Repository:

```text
GitHub
```

---

Branches:

```text
main

develop

feature/*
```

---

Example:

```text
feature/transaction-module

feature/telegram-bot
```

---

# 30. Commit Standards

Format:

```text
type(scope): message
```

Examples:

```text
feat(transaction): add duplicate detection

fix(parser): handle ICICI SMS format

refactor(account): simplify balance update

test(auth): add JWT tests
```

---

# 31. Pull Request Standards

Every PR must include:

```text
Purpose

Changes

Testing

Screenshots (if UI)
```

---

# 32. Documentation Standards

Every module must contain:

```text
README.md
```

describing:

* Purpose
* Responsibilities
* Public Interfaces

---

# 33. AI Code Generation Standards

AI-generated code must:

* Follow module boundaries.
* Use service layer.
* Use repository layer.
* Use UUIDs.
* Use Decimal for money.
* Use Pydantic validation.
* Include tests.
* Include docstrings.

---

# 34. AI Forbidden Actions

AI agents must not:

* Use floats for money.
* Put SQL in API routes.
* Hardcode secrets.
* Skip audit logging.
* Skip ownership validation.
* Create circular imports.
* Bypass service layer.
* Introduce microservices.

---

# 35. Performance Standards

Avoid:

```python
for transaction in transactions:
    query_database()
```

N+1 queries.

---

Use:

```python
bulk queries
```

when possible.

---

# 36. Security Coding Standards

Never log:

```text
Passwords

JWT Tokens

Secrets

API Keys
```

---

Mask:

```text
Account Numbers

Card Numbers
```

---

# 37. Type Hint Standards

Required everywhere.

Example:

```python
def create_transaction(
    request: CreateTransactionRequest
) -> TransactionResponse:
```

---

# 38. Docstring Standards

Public methods require docstrings.

Example:

```python
def create_transaction():
    """
    Creates a financial transaction
    and updates balances.
    """
```

---

# 39. Code Review Checklist

Before merge:

* Tests pass
* Lint passes
* Types pass
* Ownership validation exists
* Audit logging exists
* No secrets committed
* Documentation updated

---

# 40. AI Agent Master Rules

AI coding agents must:

* Generate production-quality code.
* Follow layered architecture.
* Use FastAPI.
* Use SQLModel.
* Use PostgreSQL.
* Use Alembic.
* Use JWT.
* Use Argon2.
* Use Decimal.
* Use UUID.

AI coding agents must not:

* Use floats for money.
* Skip tests.
* Skip migrations.
* Skip ownership validation.
* Skip audit logging.
* Introduce unnecessary complexity.

---

# 41. Approval

Status: Approved

This document is the authoritative coding standard for the Personal Finance Tracking Platform.

All source code, pull requests, reviews, tests, AI-generated implementations, and future contributions must comply with these standards.
