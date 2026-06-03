# 04-database_schema.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Database Schema Specification

Database: PostgreSQL

ORM Target: SQLModel

Migration Tool: Alembic

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines the production-grade relational database schema for the Personal Finance Tracking Platform.

It specifies:

* Tables
* Columns
* Data types
* Enums
* Foreign keys
* Constraints
* Indexes
* Audit strategy
* Multi-currency support
* Transfer modeling
* SaaS readiness
* Future extension points

This document must be used as the source of truth when generating:

* SQLModel models
* Alembic migrations
* Repository classes
* Query services
* Reporting queries

---

# 2. Database Principles

## 2.1 PostgreSQL as System of Record

PostgreSQL is the primary operational database.

It stores:

* Users
* Accounts
* Raw events
* Transactions
* Merchants
* Categories
* Feedback
* Audit logs

---

## 2.2 UUID Primary Keys

All primary keys must use UUID.

No integer primary keys are allowed.

Reason:

* SaaS readiness
* Easier distributed systems support
* Safer external references
* Avoid leaking record counts

---

## 2.3 Multi-Tenant Ready

Every user-owned business table must include:

```sql
user_id UUID NOT NULL
```

This supports future multi-user SaaS deployment.

---

## 2.4 Raw Events Are Immutable

Raw events must never be deleted.

Raw event data is the original source of truth for parsed transactions.

---

## 2.5 Transactions Are Never Hard Deleted

Financial records must not be physically deleted.

If deletion is required in the future, implement soft-delete using:

```sql
deleted_at TIMESTAMP NULL
```

MVP does not require transaction deletion.

---

## 2.6 Auditability

All financial modifications must be recorded in `audit_log`.

Examples:

* Category change
* Merchant change
* Description update
* Account rename
* Balance reconciliation

---

## 2.7 Multi-Currency Ready

Every financial amount must store:

* amount
* currency

Future conversion support must store:

* exchange_rate
* base_currency_amount
* base_currency

---

# 3. Enum Definitions

The following enums should be implemented as PostgreSQL enums or controlled string fields.

For MVP, controlled strings are acceptable if validation is enforced in the application layer.

---

## 3.1 account_type

Allowed Values:

```text
BANK
CREDIT_CARD
CASH
INVESTMENT
LOAN
```

---

## 3.2 account_status

Allowed Values:

```text
PENDING
ACTIVE
ARCHIVED
DISABLED
```

---

## 3.3 source_type

Allowed Values:

```text
SMS
TELEGRAM
EMAIL
CSV
AA
API
MANUAL
```

---

## 3.4 processing_status

Allowed Values:

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

---

## 3.5 transaction_direction

Allowed Values:

```text
DEBIT
CREDIT
```

---

## 3.6 business_type

Allowed Values:

```text
EXPENSE
INCOME
TRANSFER
REFUND
INVESTMENT
LOAN
EMI
FEE
INTEREST
CASHBACK
UNKNOWN
```

---

## 3.7 feedback_type

Allowed Values:

```text
CATEGORY_CHANGE
MERCHANT_CHANGE
DESCRIPTION_UPDATE
ACCOUNT_UPDATE
BUSINESS_TYPE_CHANGE
TRANSFER_LINK
BALANCE_RECONCILIATION
```

---

## 3.8 audit_source

Allowed Values:

```text
USER
SYSTEM
TELEGRAM
AI
IMPORT
AA
API
```

---

## 3.9 audit_action

Allowed Values:

```text
CREATE
UPDATE
DELETE
LOGIN
LOGOUT
PASSWORD_CHANGE
CATEGORY_CHANGE
MERCHANT_CHANGE
DESCRIPTION_UPDATE
ACCOUNT_UPDATE
BALANCE_RECONCILIATION
RULE_CREATED
RULE_UPDATED
```

---

## 3.10 notification_mode

Allowed Values:

```text
ALWAYS
LOW_CONFIDENCE_ONLY
DAILY_SUMMARY
WEEKLY_SUMMARY
DISABLED
```

---

# 4. Core Tables

---

# 4.1 users

Stores platform users.

Even though MVP is single-user, the schema is SaaS-ready.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    telegram_chat_id VARCHAR(100),
    timezone VARCHAR(100) NOT NULL DEFAULT 'Asia/Kolkata',
    default_currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Indexes:

```sql
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_telegram_chat_id ON users(telegram_chat_id);
```

---

# 4.2 user_settings

Stores user preferences.

```sql
CREATE TABLE user_settings (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    notification_mode VARCHAR(50) NOT NULL DEFAULT 'LOW_CONFIDENCE_ONLY',
    ai_suggestions_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    historical_import_mode VARCHAR(50),
    preferred_language VARCHAR(20) NOT NULL DEFAULT 'en',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Constraints:

```sql
ALTER TABLE user_settings
ADD CONSTRAINT uq_user_settings_user UNIQUE(user_id);
```

---

# 4.3 accounts

Stores all financial accounts.

Examples:

* ICICI Salary Account
* HDFC Savings
* HDFC Credit Card
* Cash Wallet

```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),

    account_name VARCHAR(255),
    account_type VARCHAR(50) NOT NULL,
    bank_name VARCHAR(100),
    last_four_digits VARCHAR(10),

    currency VARCHAR(3) NOT NULL DEFAULT 'INR',

    opening_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
    estimated_balance NUMERIC(18,2) NOT NULL DEFAULT 0,

    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Recommended Constraints:

```sql
ALTER TABLE accounts
ADD CONSTRAINT uq_user_bank_lastfour_type
UNIQUE(user_id, bank_name, last_four_digits, account_type);
```

Indexes:

```sql
CREATE INDEX idx_accounts_user_id ON accounts(user_id);
CREATE INDEX idx_accounts_status ON accounts(status);
CREATE INDEX idx_accounts_bank_last_four ON accounts(bank_name, last_four_digits);
```

---

# 4.4 raw_events

Stores all incoming source events.

Sources:

* SMS
* Telegram
* Email
* CSV
* AA

Raw events must be preserved permanently.

```sql
CREATE TABLE raw_events (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),

    source_type VARCHAR(50) NOT NULL,
    sender VARCHAR(255),
    message_text TEXT NOT NULL,

    received_at TIMESTAMP NOT NULL,
    message_hash VARCHAR(255) NOT NULL,

    processing_status VARCHAR(50) NOT NULL DEFAULT 'RECEIVED',
    processing_error TEXT,

    correlation_id UUID,
    request_id UUID,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Indexes:

```sql
CREATE INDEX idx_raw_events_user_id ON raw_events(user_id);
CREATE INDEX idx_raw_events_hash ON raw_events(message_hash);
CREATE INDEX idx_raw_events_received_at ON raw_events(received_at);
CREATE INDEX idx_raw_events_status ON raw_events(processing_status);
CREATE INDEX idx_raw_events_correlation_id ON raw_events(correlation_id);
```

Notes:

`message_hash` is used for exact duplicate detection.

Transaction-level deduplication must not rely only on raw message text.

---

# 4.5 categories

Stores system and user categories.

System categories have:

```sql
user_id IS NULL
```

User categories have:

```sql
user_id IS NOT NULL
```

```sql
CREATE TABLE categories (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),

    name VARCHAR(255) NOT NULL,
    parent_category_id UUID REFERENCES categories(id),

    is_system BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Indexes:

```sql
CREATE INDEX idx_categories_user_id ON categories(user_id);
CREATE INDEX idx_categories_parent ON categories(parent_category_id);
CREATE INDEX idx_categories_name ON categories(name);
```

Recommended uniqueness:

```sql
CREATE UNIQUE INDEX uq_system_category_name
ON categories(name)
WHERE user_id IS NULL;

CREATE UNIQUE INDEX uq_user_category_name
ON categories(user_id, name)
WHERE user_id IS NOT NULL;
```

---

# 4.6 merchants

Stores normalized merchants.

Examples:

* Swiggy
* Amazon
* SmartQ
* BMTC

```sql
CREATE TABLE merchants (
    id UUID PRIMARY KEY,

    merchant_name VARCHAR(255) NOT NULL,
    merchant_group VARCHAR(255),

    default_category_id UUID REFERENCES categories(id),

    is_global BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Indexes:

```sql
CREATE INDEX idx_merchants_name ON merchants(merchant_name);
CREATE INDEX idx_merchants_group ON merchants(merchant_group);
```

---

# 4.7 merchant_patterns

Stores matching patterns used to resolve raw merchant strings.

A global rule has:

```sql
user_id IS NULL
```

A personal user rule has:

```sql
user_id IS NOT NULL
```

User rules always override global rules.

```sql
CREATE TABLE merchant_patterns (
    id UUID PRIMARY KEY,

    user_id UUID REFERENCES users(id),
    merchant_id UUID NOT NULL REFERENCES merchants(id),

    pattern VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL DEFAULT 'LIKE',

    confidence NUMERIC(5,2) NOT NULL DEFAULT 1.00,

    created_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Allowed `pattern_type` values:

```text
EXACT
LIKE
REGEX
AI_SUGGESTED
```

Indexes:

```sql
CREATE INDEX idx_merchant_patterns_user_id ON merchant_patterns(user_id);
CREATE INDEX idx_merchant_patterns_pattern ON merchant_patterns(pattern);
CREATE INDEX idx_merchant_patterns_merchant_id ON merchant_patterns(merchant_id);
```

---

# 4.8 transactions

Main financial transaction table.

Stores expenses, income, transfers, refunds, and other financial events.

```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY,

    user_id UUID NOT NULL REFERENCES users(id),
    account_id UUID NOT NULL REFERENCES accounts(id),
    raw_event_id UUID REFERENCES raw_events(id),
    merchant_id UUID REFERENCES merchants(id),
    category_id UUID REFERENCES categories(id),

    amount NUMERIC(18,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',

    exchange_rate NUMERIC(18,6),
    base_currency VARCHAR(3),
    base_currency_amount NUMERIC(18,2),

    direction VARCHAR(20) NOT NULL,
    business_type VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN',

    merchant_raw VARCHAR(255),
    description TEXT,

    reference_number VARCHAR(255),
    upi_id VARCHAR(255),

    transaction_timestamp TIMESTAMP,
    sms_received_timestamp TIMESTAMP,

    transaction_fingerprint VARCHAR(255),

    confidence_score NUMERIC(5,2),
    is_reviewed BOOLEAN NOT NULL DEFAULT FALSE,

    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Recommended Constraints:

```sql
ALTER TABLE transactions
ADD CONSTRAINT chk_transaction_amount_positive
CHECK (amount >= 0);

ALTER TABLE transactions
ADD CONSTRAINT chk_transaction_direction
CHECK (direction IN ('DEBIT', 'CREDIT'));
```

Indexes:

```sql
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_account_id ON transactions(account_id);
CREATE INDEX idx_transactions_raw_event_id ON transactions(raw_event_id);
CREATE INDEX idx_transactions_merchant_id ON transactions(merchant_id);
CREATE INDEX idx_transactions_category_id ON transactions(category_id);
CREATE INDEX idx_transactions_timestamp ON transactions(transaction_timestamp);
CREATE INDEX idx_transactions_business_type ON transactions(business_type);
CREATE INDEX idx_transactions_direction ON transactions(direction);
CREATE INDEX idx_transactions_fingerprint ON transactions(transaction_fingerprint);
```

Optional uniqueness:

```sql
CREATE UNIQUE INDEX uq_transaction_fingerprint_user
ON transactions(user_id, transaction_fingerprint)
WHERE transaction_fingerprint IS NOT NULL;
```

---

# 4.9 transfers

Links two transactions representing one transfer.

Example:

Bank Account Debit

↓

Credit Card Payment Credit

```sql
CREATE TABLE transfers (
    id UUID PRIMARY KEY,

    user_id UUID NOT NULL REFERENCES users(id),

    source_transaction_id UUID NOT NULL REFERENCES transactions(id),
    destination_transaction_id UUID REFERENCES transactions(id),

    transfer_type VARCHAR(50) NOT NULL DEFAULT 'INTERNAL',

    confidence_score NUMERIC(5,2),
    is_confirmed BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Transfer Types:

```text
INTERNAL
CREDIT_CARD_PAYMENT
CASH_WITHDRAWAL
ACCOUNT_TRANSFER
LOAN_PAYMENT
```

Indexes:

```sql
CREATE INDEX idx_transfers_user_id ON transfers(user_id);
CREATE INDEX idx_transfers_source ON transfers(source_transaction_id);
CREATE INDEX idx_transfers_destination ON transfers(destination_transaction_id);
```

---

# 4.10 user_feedback

Stores corrections and user input.

Used by:

* Telegram
* Future mobile app
* Web dashboard

```sql
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY,

    user_id UUID NOT NULL REFERENCES users(id),
    transaction_id UUID REFERENCES transactions(id),

    feedback_type VARCHAR(50) NOT NULL,

    old_value TEXT,
    new_value TEXT,

    source VARCHAR(50) NOT NULL DEFAULT 'USER',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Indexes:

```sql
CREATE INDEX idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX idx_user_feedback_transaction_id ON user_feedback(transaction_id);
CREATE INDEX idx_user_feedback_type ON user_feedback(feedback_type);
```

---

# 4.11 balance_snapshots

Stores historical account balance snapshots.

Used for:

* Net worth trends
* Monthly balance reports
* Future forecasting

```sql
CREATE TABLE balance_snapshots (
    id UUID PRIMARY KEY,

    user_id UUID NOT NULL REFERENCES users(id),
    account_id UUID NOT NULL REFERENCES accounts(id),

    snapshot_date DATE NOT NULL,

    balance NUMERIC(18,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Indexes:

```sql
CREATE INDEX idx_balance_snapshots_user_id ON balance_snapshots(user_id);
CREATE INDEX idx_balance_snapshots_account_id ON balance_snapshots(account_id);
CREATE INDEX idx_balance_snapshots_date ON balance_snapshots(snapshot_date);
```

Uniqueness:

```sql
ALTER TABLE balance_snapshots
ADD CONSTRAINT uq_balance_snapshot_account_date
UNIQUE(account_id, snapshot_date);
```

---

# 4.12 audit_log

Stores immutable audit history.

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY,

    user_id UUID NOT NULL REFERENCES users(id),

    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,

    action VARCHAR(100) NOT NULL,
    field_name VARCHAR(100),

    old_value TEXT,
    new_value TEXT,

    source VARCHAR(50) NOT NULL,

    correlation_id UUID,
    request_id UUID,
    session_id UUID,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Indexes:

```sql
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_correlation_id ON audit_log(correlation_id);
CREATE INDEX idx_audit_log_request_id ON audit_log(request_id);
```

Rules:

* Audit logs must not be updated.
* Audit logs must not be deleted.
* Audit logs must be append-only.

---

# 5. Future Extension Tables

These are not required in MVP but should be considered later.

---

## 5.1 ai_suggestions

Future AI-generated suggestions.

```sql
CREATE TABLE ai_suggestions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    transaction_id UUID REFERENCES transactions(id),

    suggestion_type VARCHAR(50) NOT NULL,
    suggested_value TEXT NOT NULL,
    confidence_score NUMERIC(5,2),

    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP
);
```

---

## 5.2 recurring_transactions

Future scheduled transactions.

```sql
CREATE TABLE recurring_transactions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),

    account_id UUID REFERENCES accounts(id),
    category_id UUID REFERENCES categories(id),

    amount NUMERIC(18,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',

    business_type VARCHAR(50) NOT NULL,
    description TEXT,

    recurrence_rule TEXT NOT NULL,

    next_run_date DATE,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5.3 account_aggregator_links

Future AA integration.

```sql
CREATE TABLE account_aggregator_links (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),

    provider_name VARCHAR(255) NOT NULL,
    consent_id VARCHAR(255) NOT NULL,
    consent_status VARCHAR(50) NOT NULL,

    granted_at TIMESTAMP,
    expires_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

# 6. Seed Data

The system should seed default categories.

Default categories:

```text
Food
Transport
Shopping
Bills
Health
Travel
Entertainment
Salary
Investment
Transfer
Loan
EMI
Refund
Miscellaneous
```

System categories must have:

```sql
user_id IS NULL
is_system = TRUE
```

---

# 7. Deduplication Strategy

Duplicate detection has two layers.

---

## 7.1 Raw Event Duplicate Detection

Uses:

```text
message_hash
```

This detects exact duplicate messages.

---

## 7.2 Transaction Duplicate Detection

Uses:

```text
transaction_fingerprint
```

Fingerprint should be generated from:

* user_id
* account_id
* amount
* direction
* transaction_timestamp
* merchant_raw
* reference_number

Raw SMS text alone must not be used for transaction-level deduplication.

---

# 8. Balance Calculation Strategy

Balances are estimated.

Rules:

## Bank Account

Debit:

Subtract amount.

Credit:

Add amount.

---

## Credit Card

Debit transaction:

Increase liability.

Credit transaction:

Decrease liability.

---

## Transfer

Must not affect expense/income reporting.

Transfer affects account balances only.

---

# 9. Data Retention

## Raw Events

Retain forever.

---

## Transactions

Retain forever.

---

## Audit Logs

Retain forever.

---

## Processing Logs

Future retention policy may be defined.

---

# 10. Migration Strategy

All schema changes must be performed through Alembic migrations.

Rules:

* Never modify database manually in production.
* Every schema change must include migration.
* Migration files must be committed to Git.
* Migration must be reversible when practical.

---

# 11. AI Agent Instructions

When generating SQLModel models:

* Use UUID primary keys.
* Use explicit foreign keys.
* Include indexes.
* Preserve nullable rules.
* Use Decimal for money.
* Do not use Float for financial amounts.
* Do not omit audit_log.
* Do not remove user_id from business tables.
* Do not create integer primary keys.
* Do not introduce MongoDB or BigQuery for MVP.

---

# 12. Approval

Status: Approved

This document is the authoritative database schema specification for the Personal Finance Tracking Platform.

All migrations, ORM models, repository classes, and reporting queries must comply with this document.
