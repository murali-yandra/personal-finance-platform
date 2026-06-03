# 03-domain_model.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Domain Model

Architectural Style: Domain Driven Design (DDD)

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines the business domain model for the Personal Finance Tracking Platform.

The goal of this document is to define:

* Business Concepts
* Domain Boundaries
* Bounded Contexts
* Aggregates
* Entities
* Value Objects
* Domain Events
* Domain Invariants
* Ownership Rules

This document serves as the bridge between:

```text
Business Requirements
↓
Technical Design
```

and must be referenced before creating:

* Database Models
* APIs
* Services
* Event Handlers
* AI Workflows

---

# 2. Domain Overview

The platform exists to convert financial events into a structured financial ledger.

The platform does not manage money.

The platform manages information about money.

Core business capabilities:

* Financial Tracking
* Account Tracking
* Balance Tracking
* Categorization
* Merchant Resolution
* Reporting
* Learning

---

# 3. Ubiquitous Language

All developers, architects, AI agents, and stakeholders must use the same business language.

---

## Account

A container that holds money or financial value.

Examples:

* Bank Account
* Credit Card
* Cash Wallet
* Investment Account
* Loan Account

---

## Transaction

A financial event representing movement of value.

Examples:

* Expense
* Income
* Refund
* Transfer
* Investment

---

## Merchant

A normalized business entity involved in a transaction.

Examples:

* Swiggy
* Amazon
* SmartQ
* BMTC

---

## Category

A user-facing classification.

Examples:

* Food
* Shopping
* Salary
* Travel

---

## Transfer

Movement of money between accounts owned by the same user.

Transfer is NOT:

* Expense
* Income

---

## Balance

Estimated account value at a point in time.

---

## Raw Event

Original source message.

Examples:

* SMS
* Email
* CSV Record
* AA Transaction

---

## User Feedback

User-provided correction or enhancement.

Examples:

* Category Change
* Merchant Correction
* Description Update

---

# 4. Bounded Contexts

The platform is divided into business domains.

---

# Identity Context

Purpose:

Manage user identity.

Responsibilities:

* Registration
* Login
* JWT Authentication
* User Preferences
* Roles

Primary Aggregate:

User

---

# Financial Context

Purpose:

Manage accounts and balances.

Responsibilities:

* Accounts
* Balance Calculation
* Reconciliation
* Snapshots

Primary Aggregate:

Account

---

# Transaction Context

Purpose:

Manage financial activity.

Responsibilities:

* Expenses
* Income
* Refunds
* Transfers

Primary Aggregate:

Transaction

---

# Merchant Context

Purpose:

Normalize merchant information.

Responsibilities:

* Merchant Catalog
* Merchant Patterns
* Merchant Resolution

Primary Aggregate:

Merchant

---

# Categorization Context

Purpose:

Classify transactions.

Responsibilities:

* Categories
* Classification Rules
* User Overrides

Primary Aggregate:

Category

---

# Notification Context

Purpose:

Communicate with users.

Responsibilities:

* Telegram
* Notifications
* Feedback Collection

Primary Aggregate:

Notification Session

---

# Reporting Context

Purpose:

Generate insights.

Responsibilities:

* Monthly Reports
* Net Worth
* Spending Trends

Primary Aggregate:

Report

---

# Learning Context

Purpose:

Improve classification over time.

Responsibilities:

* User Corrections
* Rule Learning
* AI Suggestions

Primary Aggregate:

Learning Rule

---

# Integration Context

Purpose:

Connect external systems.

Responsibilities:

* SMS
* Email
* CSV
* AA
* APIs

Primary Aggregate:

Raw Event

---

# 5. Aggregate Roots

Aggregate Roots represent consistency boundaries.

---

# User

Aggregate Root

Description:

Represents a platform user.

Responsibilities:

* Own Accounts
* Own Transactions
* Own Categories
* Own Rules

Attributes:

* User ID
* Email
* Display Name
* Preferences
* Timezone

Rules:

User owns all financial data.

---

# Account

Aggregate Root

Description:

Represents a financial account.

Types:

* BANK
* CREDIT_CARD
* CASH
* INVESTMENT
* LOAN

Attributes:

* Name
* Currency
* Balance
* Status

Rules:

Account belongs to one User.

---

# Transaction

Aggregate Root

Description:

Represents a financial movement.

Attributes:

* Amount
* Currency
* Direction
* Business Type
* Merchant
* Category
* Timestamp

Rules:

Transaction belongs to exactly one Account.

---

# Merchant

Aggregate Root

Description:

Represents normalized merchants.

Attributes:

* Merchant Name
* Merchant Group
* Default Category

Rules:

Many Transactions may reference one Merchant.

---

# Category

Aggregate Root

Description:

Represents user-facing classifications.

Examples:

* Food
* Travel
* Shopping

Rules:

Categories may be System Categories or User Categories.

---

# Transfer

Aggregate Root

Description:

Links two transactions.

Source Transaction

↓

Destination Transaction

Rules:

Transfers are never categorized as Income or Expense.

---

# Balance Snapshot

Aggregate Root

Description:

Historical balance record.

Purpose:

* Trend Analysis
* Reporting
* Forecasting

---

# Audit Log

Aggregate Root

Description:

Stores immutable history of changes.

Purpose:

* Auditability
* Traceability
* Debugging

---

# 6. Entities

Entities possess identity.

---

## User

Identity:

User ID

---

## Account

Identity:

Account ID

---

## Transaction

Identity:

Transaction ID

---

## Merchant

Identity:

Merchant ID

---

## Category

Identity:

Category ID

---

## Transfer

Identity:

Transfer ID

---

## Balance Snapshot

Identity:

Snapshot ID

---

## Audit Log

Identity:

Audit ID

---

# 7. Value Objects

Value Objects have no identity.

---

## Money

Represents:

Amount + Currency

Example:

Amount: 70

Currency: INR

Rules:

Money is immutable.

---

## Account Reference

Represents:

Bank Name + Last Four Digits

Example:

ICICI + 0452

Used for account discovery.

---

## Merchant Pattern

Represents:

Matching rule.

Example:

upiswiggy@%

Used for merchant resolution.

---

## Category Assignment

Represents:

Transaction Category + Confidence

Example:

Food

Confidence: 0.95

---

# 8. Domain Events

Events represent business facts.

---

## TransactionCreated

Occurs when:

Transaction inserted.

Consumers:

* Balance Engine
* Telegram Notifier
* Learning Engine
* Audit Logger

---

## TransactionUpdated

Occurs when:

Transaction modified.

Consumers:

* Audit Logger
* Learning Engine

---

## NewAccountDetected

Occurs when:

Unknown account discovered.

Consumers:

* Telegram Notifier

---

## UserFeedbackReceived

Occurs when:

Telegram feedback received.

Consumers:

* Learning Engine

---

## MerchantRuleCreated

Occurs when:

New merchant pattern added.

Consumers:

* Categorization Engine

---

## BalanceReconciled

Occurs when:

User performs reconciliation.

Consumers:

* Reporting Engine

---

## AuditEventCreated

Occurs when:

Auditable action occurs.

Consumers:

* Audit Storage

---

# 9. Ownership Rules

Ownership determines data access.

---

User owns:

* Accounts
* Transactions
* Categories
* Merchant Patterns
* Feedback

---

System owns:

* Default Categories
* Global Merchant Rules

---

Future SaaS Rule:

Every business entity must contain:

user_id

except:

* System Categories
* Global Rules

---

# 10. Domain Invariants

Domain Invariants are rules that must never be violated.

---

Invariant 1

Raw Events Never Deleted.

---

Invariant 2

Transactions Never Hard Deleted.

---

Invariant 3

Every Transaction Must Have Origin Traceability.

Transaction

↓

Raw Event

---

Invariant 4

Transfers Are Not Expenses.

---

Invariant 5

Credits Are Not Always Income.

---

Invariant 6

User Rules Override Global Rules.

---

Invariant 7

Audit Records Are Immutable.

---

Invariant 8

AI Cannot Modify Financial Records Without User Approval.

---

Invariant 9

Every Financial Record Must Belong To A User.

---

Invariant 10

Balances Are Estimated Until Reconciled.

---

# 11. Future Domain Expansion

Future Aggregates:

* Budget
* Goal
* Investment Portfolio
* Loan Schedule
* Recurring Transaction
* AI Suggestion
* Account Aggregator Link

These additions should not require redesign of existing aggregates.

---

# 12. Architectural Principles

The domain model shall follow:

* Domain Driven Design
* Modular Monolith
* Event Driven Internal Architecture
* Rich Domain Model
* Explicit Business Rules

The domain model is the authoritative business language for the Personal Finance Tracking Platform.

All future technical artifacts must align with this document.
