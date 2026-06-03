# 14-sprint_roadmap.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Sprint Roadmap

Methodology: Agile Scrum

Sprint Duration: 2 Weeks

Target Release: MVP → SaaS

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines the implementation roadmap for the Personal Finance Tracking Platform.

The roadmap provides:

* Development sequence
* Sprint objectives
* Deliverables
* Dependencies
* Milestones
* MVP scope
* Post-MVP scope

This roadmap is optimized for:

```text
Solo Developer
+
AI Coding Agents
+
Incremental Delivery
```

The objective is to build a production-quality system with minimal rework.

---

# 2. Roadmap Philosophy

The platform must be built in layers.

Order:

```text
Foundation
↓
Core Financial Engine
↓
SMS Automation
↓
Telegram Feedback
↓
Reporting
↓
AI Assistance
↓
SaaS Expansion
```

---

# 3. Release Plan

## Release 1

Foundation

Goal:

```text
System Skeleton
```

---

## Release 2

Financial Core

Goal:

```text
Transaction Engine
```

---

## Release 3

Automation

Goal:

```text
SMS Processing
```

---

## Release 4

User Experience

Goal:

```text
Telegram Feedback Loop
```

---

## Release 5

Insights

Goal:

```text
Reporting + AI
```

---

## Release 6

SaaS

Goal:

```text
Multi User Platform
```

---

# 4. Sprint Overview

| Sprint    | Focus                |
| --------- | -------------------- |
| Sprint 0  | Project Foundation   |
| Sprint 1  | Authentication       |
| Sprint 2  | Accounts             |
| Sprint 3  | Transactions         |
| Sprint 4  | SMS Ingestion        |
| Sprint 5  | Parsing Engine       |
| Sprint 6  | Merchant Engine      |
| Sprint 7  | Categories           |
| Sprint 8  | Telegram Bot         |
| Sprint 9  | Reporting            |
| Sprint 10 | Balance Engine       |
| Sprint 11 | Historical Imports   |
| Sprint 12 | AI Foundation        |
| Sprint 13 | Learning Engine      |
| Sprint 14 | Production Hardening |
| Sprint 15 | SaaS Preparation     |

---

# 5. Sprint 0 — Project Foundation

Duration:

```text
2 Weeks
```

---

## Goal

Create the platform foundation.

---

## Deliverables

### Repository

```text
GitHub Repository
```

---

### Project Structure

```text
backend/
docs/
infra/
scripts/
```

---

### Docker

```text
Dockerfile
docker-compose.yml
```

---

### Database

```text
PostgreSQL
Alembic
SQLModel
```

---

### CI/CD

```text
GitHub Actions
```

---

### Environment Configuration

```text
.env
.env.example
```

---

## Definition of Done

* Docker starts successfully
* Database connects
* Migration system works
* CI pipeline passes

---

# 6. Sprint 1 — Authentication

## Goal

User registration and login.

---

## Deliverables

Tables:

```text
users
user_settings
```

---

Features:

```text
Register

Login

JWT

Refresh Token

Current User
```

---

Endpoints:

```text
/auth/register

/auth/login

/auth/refresh

/users/me
```

---

Definition of Done:

* Authentication complete
* JWT working
* Ownership model ready

---

# 7. Sprint 2 — Accounts

## Goal

Account management.

---

## Deliverables

Tables:

```text
accounts
```

---

Features:

```text
Create Account

Update Account

Archive Account

List Accounts
```

---

Account Types:

```text
BANK

CREDIT_CARD

CASH

WALLET
```

---

Definition of Done:

* Account CRUD complete

---

# 8. Sprint 3 — Transactions

## Goal

Transaction engine.

---

## Deliverables

Tables:

```text
transactions
audit_log
```

---

Features:

```text
Create Transaction

Update Transaction

List Transactions

Duplicate Detection

Fingerprint Engine
```

---

Definition of Done:

* Transaction lifecycle complete

---

# 9. Sprint 4 — SMS Ingestion

## Goal

Receive SMS data.

---

## Deliverables

Tables:

```text
raw_events
```

---

Features:

```text
Ingest SMS

Store Raw SMS

API Key Auth

Deduplication
```

---

Endpoint:

```text
POST /ingest/sms
```

---

Definition of Done:

* SMS stored successfully

---

# 10. Sprint 5 — Parsing Engine

## Goal

Convert SMS to structured transactions.

---

## Deliverables

Modules:

```text
parser/
```

---

Parsers:

```text
ICICI

HDFC

SBI

Generic
```

---

Features:

```text
Amount Extraction

Direction Detection

Account Detection

Merchant Extraction
```

---

Definition of Done:

* Sample SMS successfully parsed

---

# 11. Sprint 6 — Merchant Engine

## Goal

Merchant normalization.

---

## Deliverables

Tables:

```text
merchants

merchant_patterns
```

---

Features:

```text
Merchant Matching

Pattern Matching

Merchant Resolution
```

---

Example:

```text
UPISWIGGY@ICICI
↓
Swiggy
```

---

Definition of Done:

* Merchant normalization working

---

# 12. Sprint 7 — Categories

## Goal

Category management.

---

## Deliverables

Tables:

```text
categories
```

---

Features:

```text
Default Categories

Custom Categories

Category Assignment
```

---

Definition of Done:

* Transactions categorized

---

# 13. Sprint 8 — Telegram Bot

## Goal

User interaction layer.

---

## Deliverables

Features:

```text
Transaction Notifications

Description Requests

Account Naming

Category Corrections
```

---

Commands:

```text
/start
/help
/accounts
/settings
```

---

Definition of Done:

* Telegram feedback loop working

---

# 14. Sprint 9 — Reporting

## Goal

Financial visibility.

---

## Deliverables

Reports:

```text
Monthly Summary

Category Breakdown

Income vs Expense

Account Summary
```

---

Endpoints:

```text
/reports/*
```

---

Definition of Done:

* Reports generated correctly

---

# 15. Sprint 10 — Balance Engine

## Goal

Balance tracking.

---

## Deliverables

Tables:

```text
balance_snapshots
```

---

Features:

```text
Estimated Balances

Credit Card Liability

Balance Updates

Reconciliation
```

---

Definition of Done:

* Balance calculations accurate

---

# 16. Sprint 11 — Historical Import

## Goal

Import old SMS data.

---

## Deliverables

Features:

```text
Date Range Import

Batch Processing

Duplicate Protection

Reprocessing
```

---

Options:

```text
Last Month

3 Months

6 Months

1 Year

Custom Range

All Messages
```

---

Definition of Done:

* Historical imports complete

---

# 17. Sprint 12 — AI Foundation

## Goal

Introduce AI safely.

---

## Deliverables

Modules:

```text
ai/
```

---

Infrastructure:

```text
Ollama

Provider Abstraction
```

---

Features:

```text
Merchant Suggestions

Category Suggestions
```

---

Definition of Done:

* AI suggestions stored

---

# 18. Sprint 13 — Learning Engine

## Goal

Learn from user corrections.

---

## Deliverables

Tables:

```text
ai_suggestions

user_feedback
```

---

Features:

```text
Merchant Learning

Category Learning

Rule Creation
```

---

Example:

```text
KA51AJ*
↓
Transport
```

---

Definition of Done:

* User feedback influences future suggestions

---

# 19. Sprint 14 — Production Hardening

## Goal

Make platform production ready.

---

## Deliverables

Features:

```text
Structured Logging

Monitoring

Error Handling

Backup Automation

Security Review
```

---

Definition of Done:

* Production checklist passed

---

# 20. Sprint 15 — SaaS Preparation

## Goal

Prepare for multi-user scale.

---

## Deliverables

Features:

```text
Role System

Rate Limiting

MFA

Session Tracking

Admin APIs
```

---

Definition of Done:

* Multi-user ready

---

# 21. MVP Definition

MVP ends after:

```text
Sprint 10
```

Features included:

```text
Authentication

Accounts

Transactions

SMS Automation

Telegram

Reporting

Balance Tracking
```

---

# 22. Post-MVP Features

## Phase 2

```text
Historical Imports

AI Suggestions

Learning Engine
```

---

## Phase 3

```text
Budgeting

Financial Goals

Insights

Anomaly Detection
```

---

## Phase 4

```text
Account Aggregator

Investment Tracking

Net Worth
```

---

## Phase 5

```text
Mobile Apps

SaaS

Subscriptions
```

---

# 23. Technical Debt Sprint

Every 4 sprints:

Reserve:

```text
20%
```

capacity for:

```text
Refactoring

Performance

Testing

Documentation
```

---

# 24. Testing Roadmap

Unit Tests:

```text
Sprint 1+
```

---

Integration Tests:

```text
Sprint 3+
```

---

End-to-End Tests:

```text
Sprint 8+
```

---

Performance Tests:

```text
Sprint 14+
```

---

# 25. Documentation Roadmap

Maintain:

```text
PRD

ERD

API Docs

Architecture Docs

Runbooks
```

throughout project.

---

# 26. Success Metrics

MVP Success:

```text
SMS → Transaction < 5 seconds

Duplicate Accuracy > 99%

Parser Accuracy > 90%

System Uptime > 99%
```

---

AI Success:

```text
Category Accuracy > 85%

Merchant Accuracy > 90%
```

---

# 27. Risk Management

Major Risks:

```text
Bank SMS Format Changes

Duplicate Messages

Balance Drift

Telegram Failures

Parser Accuracy
```

---

Mitigation:

```text
Parser Plugins

Audit Logs

Reconciliation

Retry Logic
```

---

# 28. Solo Developer Strategy

Recommended Workflow:

```text
Requirement
↓
Design
↓
Generate Code With AI
↓
Review
↓
Test
↓
Merge
```

---

Never:

```text
Generate Entire System At Once
```

Build sprint-by-sprint.

---

# 29. AI Agent Execution Strategy

For each sprint:

Provide AI with:

```text
PRD

ERD

API Contracts

Coding Standards

Sprint Scope
```

Only.

---

Do NOT generate future sprint code early.

---

# 30. Final Recommended Build Order

Phase 1

```text
Sprint 0 → Sprint 5
```

Build core platform.

---

Phase 2

```text
Sprint 6 → Sprint 10
```

Build user experience.

---

Phase 3

```text
Sprint 11 → Sprint 13
```

Build intelligence.

---

Phase 4

```text
Sprint 14 → Sprint 15
```

Production and SaaS readiness.

---

# 31. Approval

Status: Approved

This document is the authoritative Sprint Roadmap for the Personal Finance Tracking Platform.

All project planning, sprint execution, AI-assisted development, and release management activities must align with this roadmap.
