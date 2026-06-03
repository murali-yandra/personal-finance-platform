# 06-high_level_design.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: High Level Design

Architecture Style: Modular Monolith

Backend Framework: FastAPI

Database: PostgreSQL

Deployment Target: Docker Compose

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines the high-level architecture for the Personal Finance Tracking Platform.

It explains:

* System architecture
* Module boundaries
* Data flow
* Integration points
* Deployment topology
* Security boundaries
* Future scalability path

This document must be used when implementing:

* Backend services
* API routes
* Domain services
* Repositories
* Workers
* Telegram integration
* Future AI modules

---

# 2. Architecture Summary

The platform follows a Modular Monolith architecture.

The system is deployed as a single backend application with clearly separated internal modules.

The architecture is intentionally designed to start simple for MVP while remaining scalable for future SaaS deployment.

---

# 3. Primary Architecture Decisions

## 3.1 Backend Framework

Selected:

```text
FastAPI
```

Reason:

* Strong API development support
* Built-in OpenAPI documentation
* Python ecosystem
* Good AI-generation compatibility
* Good fit for ETL-style processing

---

## 3.2 Database

Selected:

```text
PostgreSQL
```

Reason:

* ACID compliance
* Financial data integrity
* Strong relational model
* Good reporting support
* Docker-friendly

---

## 3.3 Deployment

Selected:

```text
Docker Compose
```

Reason:

* Local laptop deployment
* VPS-ready
* Easy PostgreSQL integration
* Simple migration path

---

## 3.4 Ingestion

Selected for MVP:

```text
MacroDroid
```

Reason:

* Fastest Android SMS ingestion
* No Android app development required initially
* Easy webhook forwarding

---

## 3.5 User Interaction

Selected:

```text
Telegram Bot
```

Reason:

* Free
* Reliable Bot API
* Supports delayed replies
* Useful for account naming and feedback

---

## 3.6 Authentication

Selected:

```text
JWT Authentication
```

Reason:

* SaaS-ready
* Mobile-app-ready
* API-friendly
* Better than Telegram-only identity

---

## 3.7 AI Strategy

Selected for future:

```text
Ollama
```

Models:

* Qwen
* Gemma
* Llama

AI is not part of MVP transaction creation.

AI may suggest, but must not modify financial records without approval.

---

# 4. System Context

## 4.1 Current MVP Context

```text
Android Phone
    ↓
MacroDroid
    ↓
FastAPI Backend
    ↓
PostgreSQL
    ↓
Telegram Bot
```

---

## 4.2 Future Context

```text
Android App
iOS Alternative Inputs
Email Parser
CSV Import
Account Aggregator
AI Assistant
Web Dashboard
Mobile App
```

All future inputs must flow through the same ingestion layer.

---

# 5. High-Level Component Diagram

```text
+------------------+
| Android SMS      |
+--------+---------+
         |
         v
+------------------+
| MacroDroid       |
+--------+---------+
         |
         v
+------------------+
| Ingestion API    |
+--------+---------+
         |
         v
+------------------+
| Raw Event Store  |
+--------+---------+
         |
         v
+------------------+
| Parser Engine    |
+--------+---------+
         |
         v
+----------------------+
| Transaction Engine   |
+------+-------+-------+
       |       |
       |       |
       v       v
+-----------+ +----------------+
| Accounts  | | Merchant       |
| Resolver  | | Resolver       |
+-----------+ +----------------+
       |       |
       v       v
+-----------+ +----------------+
| Category  | | Balance Engine |
| Resolver  | +----------------+
+-----------+
       |
       v
+------------------+
| PostgreSQL       |
+--------+---------+
         |
         v
+------------------+
| Telegram Bot     |
+------------------+
```

---

# 6. Internal Modules

The backend must be organized as a Modular Monolith.

Recommended folder structure:

```text
backend/src/

api/
ingestion/
parser/
accounts/
transactions/
merchants/
categories/
telegram/
reporting/
settings/
auth/
common/
database/
events/
```

---

# 7. Module Responsibilities

## 7.1 API Module

Responsibilities:

* Expose HTTP endpoints
* Validate requests
* Return standard responses
* Call service layer

Must not contain:

* Business logic
* SQL queries
* Parsing logic
* Balance calculations

---

## 7.2 Auth Module

Responsibilities:

* Registration
* Login
* JWT access token generation
* Refresh token handling
* Password hashing
* Auth middleware

Technology:

* Argon2 for password hashing
* JWT for authentication

---

## 7.3 Ingestion Module

Responsibilities:

* Receive raw input events
* Validate source payloads
* Generate message hash
* Store raw events
* Trigger parsing workflow

Supported MVP source:

* SMS via MacroDroid

Future sources:

* Email
* CSV
* AA
* Android App
* API

---

## 7.4 Parser Module

Responsibilities:

* Parse raw events
* Extract structured transaction data
* Support bank-specific parsers
* Return standardized parser output

Parser Types:

* ICICI Parser
* HDFC Parser
* SBI Parser
* Axis Parser
* Generic Parser

Output Contract:

```json
{
  "amount": 70.00,
  "currency": "INR",
  "direction": "DEBIT",
  "bank_name": "ICICI",
  "account_last_four": "0452",
  "merchant_raw": "SmartQ",
  "upi_id": null,
  "reference_number": null,
  "transaction_timestamp": "2026-06-01T10:00:00"
}
```

---

## 7.5 Account Module

Responsibilities:

* Resolve account from bank and last digits
* Create pending account if unknown
* Maintain opening balance
* Maintain estimated balance
* Support reconciliation

Rules:

* Unknown accounts become PENDING.
* User must name pending accounts.
* Account ownership must always be enforced.

---

## 7.6 Transaction Module

Responsibilities:

* Create transactions
* Classify business type
* Detect duplicates
* Create fingerprints
* Publish domain events
* Prevent hard deletes

Business Types:

* EXPENSE
* INCOME
* TRANSFER
* REFUND
* INVESTMENT
* LOAN
* EMI
* UNKNOWN

---

## 7.7 Merchant Module

Responsibilities:

* Normalize merchants
* Resolve merchant patterns
* Apply user rules
* Apply global rules

Priority:

1. User Merchant Patterns
2. Global Merchant Patterns
3. AI Suggestions Future
4. Unknown Merchant

---

## 7.8 Category Module

Responsibilities:

* Manage categories
* Resolve default category
* Support custom categories
* Support system categories

Rules:

* User categories override system behavior.
* Transactions may remain uncategorized.

---

## 7.9 Balance Engine

Responsibilities:

* Update estimated account balances
* Apply debit/credit rules
* Apply credit card liability rules
* Create balance snapshots
* Support reconciliation

Rules:

Bank Account:

* Debit decreases balance
* Credit increases balance

Credit Card:

* Debit increases liability
* Credit decreases liability

Transfer:

* Impacts account balances
* Does not count as expense or income

---

## 7.10 Telegram Module

Responsibilities:

* Send transaction messages
* Ask for account names
* Ask for descriptions
* Receive delayed replies
* Process feedback
* Trigger learning

User Interactions:

* Account Naming
* Category Correction
* Description Update
* Merchant Correction
* Reports

---

## 7.11 Learning Module

Responsibilities:

* Store user corrections
* Generate merchant patterns from feedback
* Improve future classification

Rules:

* User feedback is authoritative.
* User rules override global rules.
* AI suggestions require approval.

---

## 7.12 Reporting Module

Responsibilities:

* Monthly summary
* Category breakdown
* Income vs expense
* Account balance summary
* Net worth calculation

Reports must exclude transfers from expense and income totals.

---

## 7.13 Events Module

Responsibilities:

* Publish internal domain events
* Dispatch event handlers
* Decouple modules

Key Events:

* TransactionCreated
* TransactionUpdated
* NewAccountDetected
* UserFeedbackReceived
* BalanceReconciled
* AuditEventCreated

---

## 7.14 Database Module

Responsibilities:

* Session management
* Connection handling
* Repository base classes
* Transaction management
* Alembic migrations

---

# 8. Internal Event-Driven Design

Even though the platform is a Modular Monolith, it should use internal domain events.

Example:

```text
TransactionCreated
    ↓
Balance Engine
    ↓
Telegram Notifier
    ↓
Audit Logger
```

This prevents tight coupling between modules.

---

# 9. Primary Data Flow

## 9.1 SMS to Transaction Flow

```text
Bank SMS
    ↓
MacroDroid
    ↓
POST /api/v1/ingest/sms
    ↓
Ingestion Service
    ↓
raw_events
    ↓
Parser Engine
    ↓
Account Resolver
    ↓
Merchant Resolver
    ↓
Category Resolver
    ↓
Transaction Engine
    ↓
transactions
    ↓
TransactionCreated Event
```

---

## 9.2 Telegram Feedback Flow

```text
Telegram Message
    ↓
Telegram Webhook
    ↓
Feedback Service
    ↓
Transaction Update
    ↓
Audit Log
    ↓
Learning Engine
```

---

## 9.3 Account Discovery Flow

```text
Parser detects unknown account
    ↓
Account Resolver
    ↓
Pending Account Created
    ↓
NewAccountDetected Event
    ↓
Telegram asks user to name account
```

---

# 10. Deployment Architecture

## 10.1 MVP Deployment

```text
Docker Compose

Services:
- backend
- postgres
```

Optional:

* telegram-worker

---

## 10.2 Local Deployment

Target:

```text
Developer Laptop
```

Use:

```text
docker-compose up
```

---

## 10.3 Future VPS Deployment

Target:

```text
Ubuntu VPS
```

Services:

* FastAPI Backend
* PostgreSQL
* Nginx
* Let's Encrypt

---

## 10.4 Future Cloud Deployment

Possible future targets:

* GCP
* AWS
* Azure
* Kubernetes

No redesign should be required.

---

# 11. Security Architecture

## 11.1 Authentication

Use JWT.

All APIs require JWT except:

* Register
* Login
* Health Check

---

## 11.2 Authorization

Every request must be scoped to:

```text
user_id
```

Users must never access another user's data.

---

## 11.3 Secrets

Secrets must be stored in environment variables.

Never commit:

* Database passwords
* JWT secrets
* Telegram bot tokens

---

## 11.4 Audit Logging

All important changes must be recorded in:

```text
audit_log
```

---

# 12. Scalability Architecture

## 12.1 MVP Scale

Expected:

* Single user
* Low transaction volume
* Local deployment

---

## 12.2 Future Scale

Target:

* 10,000+ users

Possible future changes:

* Managed PostgreSQL
* Redis
* Background workers
* Message queue
* Separate notification service
* Read replicas

---

## 12.3 No Early Microservices

Microservices are intentionally avoided for MVP.

Reason:

* Extra complexity
* More deployment overhead
* Harder debugging
* Not needed initially

---

# 13. AI Extension Architecture

AI is a future extension.

AI integration must be isolated inside:

```text
ai/
```

AI use cases:

* Merchant suggestion
* Category suggestion
* Monthly insight
* Natural language queries

Rules:

* AI cannot mutate financial data directly.
* AI suggestions must be stored and reviewed.
* Local models are preferred via Ollama.

---

# 14. Future Account Aggregator Support

AA integration must be implemented as another ingestion adapter.

AA flow:

```text
AA Provider
    ↓
AA Adapter
    ↓
Raw Event
    ↓
Normalizer
    ↓
Transaction Engine
```

Core transaction logic must not depend on SMS.

---

# 15. Non-Functional Requirements

## Performance

SMS to transaction target:

```text
< 2 seconds
```

Maximum:

```text
< 10 seconds
```

---

## Reliability

Raw events must be stored before parsing.

If parsing fails, raw event must remain available for reprocessing.

---

## Maintainability

Modules must be independent.

Business logic must live in service layer.

API routes must remain thin.

---

## Observability

System must log:

* Incoming raw events
* Parsing results
* Transaction creation
* Errors
* Audit events

---

# 16. Risks and Mitigations

## Risk 1

Bank SMS formats change.

Mitigation:

Parser Plugin Architecture.

---

## Risk 2

Duplicate SMS messages.

Mitigation:

Raw hash + transaction fingerprint.

---

## Risk 3

Telegram outage.

Mitigation:

Transactions still stored.

Feedback can happen later.

---

## Risk 4

Balance drift.

Mitigation:

Reconciliation workflow.

---

## Risk 5

User ignores feedback requests.

Mitigation:

Allow Uncategorized transactions.

---

# 17. AI Agent Implementation Rules

AI coding agents must:

* Follow Modular Monolith structure.
* Keep API routes thin.
* Place business logic in services.
* Place DB access in repositories.
* Use SQLModel.
* Use Alembic.
* Use UUID primary keys.
* Use Decimal for money.
* Use JWT for auth.
* Preserve raw events.
* Never hard delete financial records.
* Generate tests for each module.

AI coding agents must not:

* Introduce microservices.
* Replace PostgreSQL with BigQuery.
* Add OpenAI API dependencies.
* Skip audit logging.
* Skip user ownership checks.
* Remove Telegram integration.
* Put SQL queries inside API routes.

---

# 18. Approval

Status: Approved

This document is the authoritative High Level Design for the Personal Finance Tracking Platform.

All implementation decisions must align with this design.
