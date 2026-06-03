# 02-business_requirements.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Business Requirements Document (BRD)

Owner: Product Owner

Architect: Solution Architect

Last Updated: 2026-06-02

---

# 1. Introduction

## 1.1 Purpose

This document defines the business requirements for the Personal Finance Tracking Platform.

The purpose of this document is to describe:

* Business objectives
* Business capabilities
* Business rules
* Stakeholders
* Success metrics
* Future business expansion opportunities

This document complements the Product Requirements Document (PRD).

The PRD explains:

```text
What the product must do.
```

This BRD explains:

```text
Why the business needs those capabilities.
```

---

# 2. Business Vision

Enable users to maintain a complete and accurate financial ledger automatically without requiring manual transaction entry.

The platform should become a trusted source of financial truth for users.

Long-term vision:

```text
Financial Operating System
for Individuals
```

Users should be able to understand:

* Where money comes from
* Where money goes
* Current balances
* Savings trends
* Net worth
* Financial habits

without manually tracking anything.

---

# 3. Business Objectives

## Objective 1

Reduce Manual Financial Tracking

Current State:

Users manually track expenses or do not track them at all.

Target State:

Financial activity is automatically captured.

Success Indicator:

Less than 5% manual transaction creation.

---

## Objective 2

Increase Financial Visibility

Users should know:

* Monthly spending
* Income sources
* Spending categories
* Account balances

at any time.

Success Indicator:

User can generate a monthly financial summary in seconds.

---

## Objective 3

Improve Financial Awareness

Users should understand:

* Spending habits
* Savings rate
* Major expenses
* Income trends

Success Indicator:

User can identify top spending categories.

---

## Objective 4

Create a Scalable Financial Platform

The architecture should support:

* Single-user deployment
* Family deployment
* SaaS deployment

without redesign.

---

# 4. Business Drivers

## Driver 1

Financial Awareness

Most users lack visibility into spending behavior.

---

## Driver 2

Automation

Users prefer automation over manual bookkeeping.

---

## Driver 3

Data Ownership

Users should own their financial data.

---

## Driver 4

Cost Efficiency

The solution should remain low cost for personal users.

Initial deployment should run on:

* Personal Laptop
* Local Docker

Future deployment should support:

* VPS
* Cloud Infrastructure

---

## Driver 5

Future Monetization

The architecture should allow future monetization.

Monetization is NOT part of MVP.

---

# 5. Business Capabilities

The platform must provide the following business capabilities.

---

## Capability 1

Transaction Capture

Description:

Capture financial activity automatically.

Sources:

Current:

* SMS

Future:

* AA
* Email
* CSV
* APIs

---

## Capability 2

Account Management

Users can manage:

* Bank Accounts
* Credit Cards
* Cash Wallets
* Investment Accounts
* Loan Accounts

---

## Capability 3

Financial Classification

Users can classify:

* Expenses
* Income
* Transfers
* Investments
* Loans
* Refunds

---

## Capability 4

Merchant Normalization

Users should see:

```text
Swiggy
```

instead of:

```text
upiswiggy@icici
```

---

## Capability 5

Categorization

Users should understand:

* Food Spend
* Travel Spend
* Shopping Spend
* Utility Spend

---

## Capability 6

Balance Management

Users should know:

Current Estimated Balance

for every account.

---

## Capability 7

Reporting

Users should access:

* Monthly Reports
* Income Reports
* Expense Reports
* Net Worth Reports

---

## Capability 8

Learning

The system should improve over time using user corrections.

---

# 6. Stakeholders

## Primary Stakeholder

End User

Responsible For:

* Reviewing transactions
* Providing corrections
* Using reports

---

## Secondary Stakeholder

Future Family Members

Shared financial tracking.

---

## Future Stakeholders

### Administrators

Platform management.

### Support Teams

Customer support.

### Compliance Teams

Audit and governance.

---

# 7. Business Rules

These rules represent core business logic.

---

## BR-001

Every financial transaction must originate from a source event.

Examples:

* SMS
* Email
* AA

No transaction may exist without origin traceability.

---

## BR-002

Raw events must never be deleted.

Reason:

Auditability.

---

## BR-003

Transactions must never be hard deleted.

Reason:

Financial integrity.

---

## BR-004

Transfers are not expenses.

Example:

Salary Account

↓

Credit Card Account

This is:

```text
Transfer
```

not:

```text
Expense
```

---

## BR-005

Credits are not always income.

Example:

Refund

↓

Credit

Business Type:

```text
Refund
```

not:

```text
Income
```

---

## BR-006

User-defined rules override global rules.

Example:

User maps:

```text
KA51AJ7604
```

to:

```text
Transport
```

Future matching transactions must use user preference.

---

## BR-007

User feedback is authoritative.

Manual user corrections override:

* System Rules
* AI Suggestions
* Global Rules

---

## BR-008

Financial history must remain auditable.

All modifications require audit logging.

---

# 8. Key Performance Indicators (KPIs)

## KPI-001

Parsing Accuracy

Target:

90%

Goal:

95%

---

## KPI-002

Duplicate Prevention

Target:

100%

No duplicate transactions.

---

## KPI-003

Balance Accuracy

Target:

99%

---

## KPI-004

Categorization Accuracy

Target:

85%

Goal:

95%

after learning.

---

## KPI-005

Processing Time

Target:

< 2 seconds

Maximum:

< 10 seconds

---

# 9. Operating Model

## Current Operating Model

Single User

Single Telegram Bot

Single PostgreSQL Instance

Single Deployment

---

## Future Operating Model

Multi-Tenant SaaS

Multiple Users

Shared Infrastructure

Subscription Plans

---

# 10. Future Revenue Opportunities

Potential Premium Features:

---

## Premium Reports

Advanced analytics.

---

## AI Insights

Spending recommendations.

---

## Budget Planning

Budget creation and tracking.

---

## Family Accounts

Multiple users under one household.

---

## Financial Coaching

AI financial assistant.

---

## Account Aggregation

Automatic financial institution connections.

---

# 11. Future Business Expansion

Potential future products:

---

## Personal Finance SaaS

Consumer platform.

---

## Family Finance Platform

Shared household tracking.

---

## Freelancer Finance Platform

Business expense management.

---

## Small Business Finance Monitoring

Lightweight operational financial tracking.

---

# 12. Risks

## Risk 1

Bank SMS formats may change.

Mitigation:

Parser Framework.

---

## Risk 2

User may ignore categorization requests.

Mitigation:

Default categorization.

---

## Risk 3

Balance drift.

Mitigation:

Reconciliation workflows.

---

## Risk 4

Telegram dependency.

Mitigation:

Future notification providers.

---

# 13. Assumptions

Current assumptions:

* User receives SMS transaction notifications.
* Android device available.
* Telegram available.
* PostgreSQL available.
* Docker available.

---

# 14. Constraints

Current constraints:

* MVP is Android-first.
* SMS is primary source.
* Budget-conscious deployment.
* Local-first architecture.
* AI optional.

---

# 15. Success Criteria

The business considers MVP successful when:

* Transactions are captured automatically.
* User does not need manual entry.
* Financial reports are generated accurately.
* Balances are maintained reliably.
* User corrections improve future classification.

---

# 16. Approval

Status: Approved

This document serves as the authoritative business requirements specification for the Personal Finance Tracking Platform and must be used alongside the Product Requirements Document for all future design and implementation decisions.
