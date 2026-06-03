# 01-product_requirements.md

# Personal Finance Tracking Platform (PFTP)

Version: 1.0

Status: Approved

Document Type: Product Requirements Document (PRD)

Owner: Product Owner

Architect: Solution Architect

Target Release: MVP

Last Updated: 2026-06-02

---

# 1. Introduction

## 1.1 Purpose

This document defines the business vision, product objectives, functional requirements, non-functional requirements, scope, constraints, and success criteria for the Personal Finance Tracking Platform.

This document serves as the highest-priority business artifact for the project and acts as the primary source of truth for all future technical and implementation decisions.

All subsequent architecture documents must align with this document.

Priority Order:

1. Product Requirements Document (this document)
2. Business Requirements
3. Domain Model
4. Database Schema
5. High Level Design
6. API Contracts
7. Coding Standards

---

# 2. Product Vision

Create a highly automated personal finance platform that tracks financial activity with minimal user effort by leveraging transaction notifications already sent by banks, UPI providers, and financial institutions.

The platform should eliminate the need for manual expense tracking while providing accurate financial visibility, categorization, balance tracking, and future financial insights.

The long-term vision is to evolve the platform into an intelligent financial assistant capable of:

* Automated financial tracking
* Expense management
* Income tracking
* Budget planning
* Financial forecasting
* AI-powered recommendations
* Multi-account aggregation
* Multi-user SaaS deployment

---

# 3. Problem Statement

Most users do not consistently track expenses because:

* Manual entry is tedious
* Existing finance apps require discipline
* Bank statements are difficult to analyze
* Spending habits are not visible in real-time

However, nearly all financial transactions already generate SMS notifications.

These SMS messages contain valuable financial data that can be automatically transformed into a structured financial ledger.

The platform exists to automate this transformation.

---

# 4. Product Objectives

## Primary Objectives

The platform shall:

* Automatically ingest transaction notifications
* Automatically create financial records
* Automatically identify expenses
* Automatically identify income
* Automatically identify transfers
* Track account balances
* Normalize merchants
* Categorize transactions
* Generate financial reports

---

## Secondary Objectives

The platform shall:

* Learn from user corrections
* Support merchant pattern learning
* Support custom categories
* Support account discovery
* Support historical imports

---

## Long-Term Objectives

The platform shall eventually support:

* AI categorization
* AI financial assistant
* Natural language financial queries
* Budget planning
* Forecasting
* Account Aggregator integration
* Multi-user SaaS deployment
* Android application
* Email statement ingestion

---

# 5. Product Scope

## MVP Scope

Included:

### SMS Ingestion

Receive SMS messages through Android automation.

Initial implementation:

* MacroDroid

Future implementations:

* Native Android App
* SMS Gateway

---

### Raw Event Storage

Store all incoming messages.

Requirements:

* Preserve original message
* Preserve sender
* Preserve timestamp
* Preserve source

Raw events must never be deleted.

---

### Transaction Parsing

Extract:

* Amount
* Currency
* Direction
* Merchant
* Bank
* Account Identifier
* UPI Identifier
* Reference Number
* Transaction Timestamp

---

### Account Discovery

Automatically discover new accounts.

Unknown accounts shall:

* Create Pending Account
* Notify User
* Request Friendly Name

Examples:

* Salary Account
* Personal Savings
* Emergency Fund
* HDFC Credit Card

---

### Transaction Classification

Supported Business Types:

* Expense
* Income
* Transfer
* Refund
* Investment
* Loan
* EMI

Supported Directions:

* Debit
* Credit

Direction and Business Type are independent concepts.

Example:

A Credit may represent:

* Income
* Refund
* Transfer

---

### Merchant Resolution

Normalize merchants.

Example:

upiswiggy@icici

↓

Swiggy

Resolution Priority:

1. User Rules
2. Global Rules
3. AI Suggestions (Future)
4. Unknown Merchant

---

### Categorization

Default Categories:

* Food
* Transport
* Shopping
* Salary
* Bills
* Health
* Travel
* Entertainment
* Investment
* Transfer
* Miscellaneous

Users may create custom categories.

---

### Telegram Interaction

Telegram shall be used for:

* Account Naming
* Description Collection
* Category Corrections
* Merchant Corrections
* Reports

Telegram shall support delayed responses.

Users may respond hours or days later.

---

### Balance Tracking

The platform shall maintain estimated balances.

Balance Formula:

Opening Balance

* Credits

- Debits

± Transfers

Balance calculations shall support reconciliation.

---

### Reporting

The platform shall provide:

* Monthly Summary
* Income Summary
* Expense Summary
* Category Breakdown
* Account Balances
* Net Worth

---

# 6. Out Of Scope (MVP)

The following features are intentionally excluded:

* Direct Bank APIs
* Account Aggregator Integration
* iOS SMS Integration
* Subscription Billing
* Multi-user Onboarding
* Investment Tracking
* Tax Filing
* OCR Receipt Scanning
* Budget Planning
* Forecasting

These may be implemented in future phases.

---

# 7. User Personas

## Primary Persona

Individual User

Characteristics:

* Uses multiple bank accounts
* Uses UPI frequently
* Wants automatic expense tracking
* Prefers minimal manual effort

---

## Future Personas

### Family

Shared household expense tracking.

### Freelancer

Business expense tracking.

### Professional

Income and spending analysis.

### Small Business

Lightweight financial monitoring.

---

# 8. Functional Requirements

## FR-001 SMS Ingestion

The system shall receive transaction notifications from Android devices.

Supported Sources:

* SMS

Future:

* Email
* CSV
* AA
* APIs

---

## FR-002 Raw Event Storage

The system shall store every incoming message.

The system shall never delete raw events.

---

## FR-003 Duplicate Detection

The system shall prevent duplicate transaction creation.

The system shall support:

* SMS retransmission
* Historical imports
* Reprocessing

---

## FR-004 Account Discovery

The system shall discover accounts automatically.

Unknown accounts shall be marked as Pending.

---

## FR-005 Transaction Creation

The system shall create structured transactions from parsed financial events.

---

## FR-006 Merchant Resolution

The system shall normalize merchant names.

---

## FR-007 Categorization

The system shall assign categories automatically when possible.

---

## FR-008 User Corrections

The system shall allow users to modify:

* Categories
* Merchants
* Descriptions
* Account Names

---

## FR-009 Learning

The system shall learn from user corrections.

---

## FR-010 Reporting

The system shall generate financial summaries.

---

# 9. Non-Functional Requirements

## Performance

Target:

SMS Received

↓

Transaction Created

Within:

2 Seconds

Maximum:

10 Seconds

---

## Availability

MVP:

Best Effort Availability

Future:

99.9% Availability

---

## Scalability

Current:

Single User

Future:

10,000+ Users

Architecture must support future SaaS deployment.

---

## Maintainability

System must follow:

* Modular Monolith
* Domain Driven Design
* Repository Pattern
* Service Layer Pattern

---

## Security

Use:

* JWT Authentication
* Argon2 Password Hashing
* HTTPS
* Audit Logging

No secrets shall be committed to source control.

---

# 10. Data Requirements

## Raw Data

Store:

* Original Message
* Sender
* Timestamp

---

## Financial Data

Store:

* Amount
* Currency
* Merchant
* Category
* Description
* Direction
* Business Type

---

## User Data

Store:

* Preferences
* Notification Settings
* Categories
* Merchant Rules

---

# 11. Multi-Currency Requirements

The platform shall be multi-currency ready.

All financial entities shall store:

* Amount
* Currency

Future Support:

* Exchange Rate
* Base Currency Amount

Supported Future Currencies:

* INR
* USD
* EUR
* GBP
* SGD

---

# 12. Audit Requirements

The system shall maintain a complete audit trail.

Changes requiring audit:

* Category Changes
* Merchant Changes
* Description Updates
* Account Updates
* Balance Adjustments

Audit records shall never be deleted.

---

# 13. AI Requirements

AI is not part of MVP.

Future AI capabilities:

* Merchant Suggestions
* Category Suggestions
* Financial Insights
* Forecasting

AI shall never modify financial records automatically without user approval.

---

# 14. Success Metrics

The MVP shall be considered successful when:

* 90%+ transaction SMS messages parse correctly
* Duplicate transactions are prevented
* Balances remain accurate
* Users can classify transactions easily
* Reports are generated correctly
* Telegram feedback workflow functions correctly

---

# 15. Future Roadmap

Phase 1:
SMS Tracking

Phase 2:
Telegram Feedback

Phase 3:
AI Categorization

Phase 4:
Account Aggregator Integration

Phase 5:
Android Application

Phase 6:
Multi-User SaaS

Phase 7:
AI Financial Assistant

Phase 8:
Forecasting and Budget Planning

---

# 16. Approval

Status: Approved

This document serves as the highest-priority business artifact for the Personal Finance Tracking Platform and must be used as the primary source of truth for all future design and implementation decisions.

