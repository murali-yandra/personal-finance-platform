# ADR-004: Use Telegram as Primary User Interface

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform requires a mechanism to interact with users after transactions are processed.

The system must support:

* Transaction notifications
* Description collection
* Category corrections
* Merchant corrections
* AI feedback collection
* Account management
* Balance queries
* Future financial insights

The MVP is intended to be built quickly without developing:

```text
Android App
iOS App
Web Application
Desktop Application
```

The chosen user interface must provide:

```text
Low Cost
Fast Delivery
Real-Time Communication
Automation Support
Future Scalability
```

---

# Problem Statement

After receiving an SMS and creating a transaction, the system often lacks important contextual information.

Examples:

```text
₹120 debit
Merchant: SmartQ

Description: Unknown
```

```text
₹45 debit

Merchant:
KA51AJ7604@CNRB

Description: Unknown
Category: Unknown
```

The platform requires a mechanism to ask the user:

```text
What was this expense?

Which category should be used?

Should this merchant be remembered?
```

without requiring a custom frontend application.

---

# Decision Drivers

The solution must support:

## Real-Time Messaging

Requirements:

```text
Instant Notifications
User Replies
Bidirectional Communication
```

---

## Cost

Requirements:

```text
Free Or Very Low Cost
```

---

## Ease Of Development

Requirements:

```text
Webhook Support
Bot Support
Simple APIs
```

---

## User Experience

Requirements:

```text
Mobile Friendly
Fast Response
Minimal Setup
```

---

## Future Growth

Requirements:

```text
Support Thousands Of Users
Support AI Workflows
Support Financial Insights
```

---

# Alternatives Considered

## Option 1 — Telegram

Advantages:

```text
Free API
Bot Support
Webhooks
Buttons
Commands
Rich Messaging
No Approval Process
```

Disadvantages:

```text
Requires Telegram Installation
Not Universal
```

---

## Option 2 — WhatsApp Business

Advantages:

```text
Massive User Base
Familiar Interface
```

Disadvantages:

```text
Business Verification
Message Costs
Template Approval
Restrictions
```

---

## Option 3 — Custom Mobile Application

Advantages:

```text
Full Control
Native Experience
```

Disadvantages:

```text
High Development Cost
Android Development
iOS Development
App Store Requirements
```

---

## Option 4 — Email

Advantages:

```text
Simple
Universal
```

Disadvantages:

```text
Poor User Experience
Delayed Responses
Not Interactive
```

---

## Option 5 — Web Application

Advantages:

```text
Full Control
Rich UI
```

Disadvantages:

```text
Longer Development Timeline
Hosting Complexity
Authentication Complexity
```

---

# Decision

The platform shall use:

```text
Telegram
```

as the primary user interface for MVP and early production phases.

Telegram shall act as:

```text
Notification Channel
Feedback Channel
Configuration Channel
Financial Assistant Channel
```

---

# Telegram Responsibilities

Telegram is responsible for:

```text
Transaction Notifications

Description Collection

Category Corrections

Merchant Corrections

Balance Queries

Settings Management

AI Feedback Collection
```

---

# Telegram Is NOT

Telegram shall not be used as:

```text
Authentication Provider

System Of Record

Financial Storage

Business Logic Layer
```

Telegram is only a communication channel.

---

# Architecture

```text
Android Phone
      ↓
MacroDroid
      ↓
FastAPI
      ↓
PostgreSQL
      ↓
Telegram Bot
      ↓
User
```

---

# User Linking Flow

Each user must link Telegram.

Flow:

```text
User
↓
Start Bot
↓
Receive Verification Code
↓
Enter Code
↓
Link Account
↓
Store Telegram Chat ID
```

Store:

```text
telegram_chat_id
```

inside:

```text
users
```

table.

---

# Transaction Notification Flow

Example:

```text
₹120 Debit

Account:
ICICI XXXX0452

Merchant:
SmartQ

Suggested Category:
Food

Transaction ID:
TXN-ABCD1234
```

Telegram sends:

```text
₹120 spent at SmartQ

Category:
Food

Reply:
DESC TXN-ABCD1234 Lunch

or

CAT TXN-ABCD1234 Groceries
```

---

# Description Collection Workflow

Problem:

SMS messages rarely contain descriptions.

Solution:

Every transaction may generate a Telegram prompt.

Example:

```text
Transaction ID:
TXN-ABCD1234

Amount:
₹150

Merchant:
Swiggy

Description:
Not Provided

Reply:

DESC TXN-ABCD1234 Dinner with friends
```

System updates transaction later.

---

# Delayed Responses

Users are not required to respond immediately.

Example:

```text
Transaction Created
10:00 AM

Description Added
11:30 PM
```

The system shall match responses using:

```text
transaction_reference
```

or

```text
transaction_uuid
```

---

# AI Feedback Workflow

Example:

```text
Merchant:
KA51AJ7604@CNRB

Suggested Category:
Transport

Confidence:
82%
```

Telegram Message:

```text
Suggested:

Transport

Reply:

ACCEPT

or

CATEGORY Food
```

---

# Learning Workflow

User correction:

```text
KA51AJ7604@CNRB

Transport
```

Store:

```text
merchant_pattern

category_mapping
```

Future transactions receive improved suggestions.

---

# User Preference Modes

Supported:

## Mode 1

```text
Always Ask
```

Telegram notifies every transaction.

---

## Mode 2

```text
Ask Low Confidence Only
```

Telegram notifies only when:

```text
confidence < threshold
```

---

## Mode 3

```text
Never Ask
```

Telegram receives only summaries.

---

# Notification Granularity

Users may configure:

- Notify On Every Transaction
- Notify Above Amount Threshold
- Notify Low Confidence Only
- Daily Summary Only
- Weekly Summary Only

Example:

Threshold:
₹500

Transactions below ₹500 generate no notification unless AI confidence is low.

---

# Telegram Commands

Required Commands:

```text
/start

/help

/accounts

/balance

/settings

/reports
```

---

# Future Commands

```text
/networth

/budget

/insights

/investments
```

---

# Balance Queries

Example:

```text
/balance
```

Response:

```text
Salary Account
₹42,000

Credit Card
₹8,500 Due

Cash Wallet
₹1,200
```

---

# Reporting Queries

Example:

```text
/reports
```

Response:

```text
This Month

Income:
₹75,000

Expenses:
₹24,500

Savings:
₹50,500
```

---

# Telegram Notification Categories

Supported:

```text
Transaction Alerts

AI Suggestions

Balance Alerts

Large Transaction Alerts

Monthly Reports

System Notifications
```

---

# Large Transaction Alerts

Future Feature.

Example:

```text
Large Transaction Detected

₹15,000

Merchant:
Amazon
```

User may confirm legitimacy.

---

# Telegram Security

Telegram messages must never contain:

```text
Full Account Number

Full Card Number

Passwords

JWT Tokens

Secrets
```

---

## Allowed Format

```text
ICICI XXXX0452
```

---

# Telegram Reliability

Failures must not block transaction processing.

If Telegram fails:

```text
Transaction Still Created
Balance Still Updated
Audit Log Still Created
```

Telegram retry handled asynchronously.

---

# Retry Strategy

Telegram failures stored in:

```text
notification_queue
```

Retry:

```text
1 Minute

5 Minutes

15 Minutes

1 Hour
```

---

# Future Interactive Buttons

Future support:

```text
Accept Category

Change Category

Add Description

Mark Transfer
```

via Telegram inline buttons.

---

# Multi-User Support

Each user has:

```text
One Telegram Chat ID
```

Ownership validation required before processing commands.

---

# Operational Benefits

Advantages:

```text
Zero Mobile Development

Fast MVP

Free Messaging

Rich User Feedback
```

---

# Financial Benefits

Allows:

```text
Transaction Context Collection

Merchant Learning

Description Enrichment

Improved Categorization
```

which SMS alone cannot provide.

---

# Consequences

## Positive Consequences

### Faster MVP Delivery

No custom UI required.

---

### Lower Cost

Telegram API is free.

---

### Better User Feedback

Interactive workflows supported.

---

### AI Learning Enabled

User corrections improve future suggestions.

---

### Future Assistant Experience

Telegram becomes a personal finance assistant.

---

## Negative Consequences

### Telegram Dependency

User must install Telegram.

---

### Limited Rich UI

Compared to a native application.

---

### Internet Required

Telegram communication requires connectivity.

---

# Rejected Alternatives

## WhatsApp

Rejected because:

```text
Message Costs

Approval Process

Business Restrictions
```

---

## Mobile App

Rejected because:

```text
Longer Delivery Time

Higher Development Cost
```

---

## Email

Rejected because:

```text
Poor User Experience

Slow Feedback Loop
```

---

## Web Application

Rejected because:

```text
Not Required For MVP

Increased Complexity
```

---

# Future Evolution

Current:

```text
Telegram First
```

Future:

```text
Telegram
+
Web Application
+
Mobile Application
```

Telegram remains supported.

---

# Review Criteria

This ADR should be revisited if:

```text
Telegram API Restrictions Change

User Base Exceeds Expectations

Mobile Applications Become Priority

Business Requirements Demand Rich UI
```

---

# Related Documents

```text
06-high_level_design.md

07-sequence_diagrams.md

08-api_contracts.md

13-ai_integration_standards.md

17-user_management.md
```

---

# Final Decision

Accepted.

Telegram shall serve as the primary user interface for the Personal Finance Tracking Platform during MVP and early production phases.

Telegram will provide transaction notifications, feedback collection, AI learning workflows, account management interactions, and future financial assistant capabilities while minimizing development cost and maximizing delivery speed.
