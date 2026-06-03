# 17-user_management.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: User Management Design

Framework: FastAPI

Authentication: JWT

Database: PostgreSQL

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines the User Management architecture for the Personal Finance Tracking Platform.

The purpose is to manage:

* User Accounts
* User Profiles
* User Preferences
* User Settings
* User Ownership
* User Lifecycle
* User Data Isolation
* Future Multi-Tenant SaaS Support

This document acts as the authoritative specification for all user-related functionality.

---

# 2. User Management Philosophy

The platform is designed:

```text
Single User First
↓
Multi User Ready
↓
SaaS Ready
```

Even in MVP mode, every record must belong to a user.

Reason:

Avoid redesign when moving from personal use to thousands of users.

---

# 3. User Architecture

```text
User
 ↓
Authentication
 ↓
User Context
 ↓
Accounts
 ↓
Transactions
 ↓
Reports
 ↓
AI Preferences
 ↓
Telegram Integration
```

Every business object must be linked to:

```text
user_id
```

---

# 4. User Entity

Primary Table:

```text
users
```

Purpose:

Store identity and profile information.

---

## Core Fields

```text
id

email

password_hash

display_name

status

telegram_chat_id

default_currency

timezone

created_at

updated_at
```

---

# 5. User Status Lifecycle

Supported statuses:

```text
ACTIVE

PENDING_VERIFICATION

LOCKED

DISABLED

DELETED
```

---

## ACTIVE

User may access all platform features.

---

## LOCKED

Temporary restriction.

Examples:

* Too many login attempts
* Security investigation

---

## DISABLED

Administrative action.

User cannot access platform.

---

## DELETED

Soft deleted account.

Data retained.

User access removed.

---

# 6. User Ownership Model

Every user-owned table must contain:

```text
user_id
```

Examples:

```text
accounts

transactions

categories

merchant_patterns

user_feedback

balance_snapshots

audit_log

ai_suggestions
```

---

## Ownership Rule

Every query must filter:

```sql
WHERE user_id = :current_user_id
```

No exceptions.

---

# 7. User Profile

Purpose:

Store personal profile information.

---

## Fields

```text
display_name

email

timezone

default_currency

preferred_language
```

---

## Example

```json
{
  "display_name": "Murali Yandra",
  "timezone": "Asia/Kolkata",
  "default_currency": "INR",
  "preferred_language": "en"
}
```

---

# 8. User Settings

Stored in:

```text
user_settings
```

Purpose:

Store user preferences separately from identity.

---

## Settings Categories

```text
Notifications

AI Preferences

Reporting

Import Settings

Privacy
```

---

# 9. Notification Preferences

Supported values:

```text
ALWAYS

LOW_CONFIDENCE_ONLY

NEVER
```

---

## Example

```json
{
  "notification_mode": "LOW_CONFIDENCE_ONLY"
}
```

Meaning:

Only notify user when AI confidence is low.

---

# 10. AI Preferences

Supported:

```text
Ask Every Time

Ask Only Low Confidence

Never Ask
```

---

## Example

```json
{
  "ai_mode": "LOW_CONFIDENCE_ONLY"
}
```

---

# 11. Category Preferences

Users may:

```text
Create Categories

Rename Categories

Disable Categories
```

---

## Restrictions

System categories cannot be deleted.

---

# 12. Merchant Preferences

Users may:

```text
Create Merchant Rules

Create Merchant Patterns

Override Global Rules
```

Example:

```text
KA51AJ*
↓
BMTC
↓
Transport
```

---

# 13. Account Preferences

Users may:

```text
Rename Accounts

Archive Accounts

Set Opening Balance

Set Account Type
```

---

## Example

```text
ICICI XXXX0452
↓
Salary Account
```

---

# 14. Telegram Integration

Each user may link:

```text
One Telegram Account
```

---

## User Mapping

Store:

```text
telegram_chat_id
```

inside:

```text
users
```

---

## Verification Flow

```text
User
↓
Start Telegram Bot
↓
Verification Code
↓
Link Telegram
↓
Store Chat ID
```

---

# 15. Telegram Commands

Supported commands:

```text
/start

/help

/accounts

/balance

/reports

/settings
```

Future:

```text
/insights

/budget

/networth
```

---

# 16. User Feedback System

Purpose:

Capture learning signals.

---

Examples:

```text
Category Corrections

Merchant Corrections

Description Updates

Transfer Confirmations
```

Stored in:

```text
user_feedback
```

---

# 17. User Feedback Lifecycle

```text
Feedback Submitted
↓
Validated
↓
Stored
↓
Learning Engine
↓
Future Suggestions Improved
```

---

# 18. User Data Isolation

Critical Requirement.

Users must never see:

```text
Other Users

Other Transactions

Other Accounts

Other Reports
```

---

## Enforcement Layers

```text
API Layer

Service Layer

Repository Layer

Database Queries
```

---

# 19. Multi-Tenant Design

The system is multi-tenant by design.

Tenant:

```text
User
```

---

## Isolation Model

```text
Shared Database
Shared Tables
User-Level Isolation
```

---

## Example

```sql
SELECT *
FROM transactions
WHERE user_id = :current_user_id
```

---

# 20. User Registration

Flow:

```text
Register
↓
Create User
↓
Create User Settings
↓
Create Default Categories
↓
Create Default Preferences
```

---

# 21. Default Categories

Created automatically.

---

## Expense Categories

```text
Food

Transport

Groceries

Entertainment

Shopping

Healthcare

Bills

Travel

Education

Investments

Other
```

---

## Income Categories

```text
Salary

Bonus

Interest

Refund

Business

Other Income
```

---

## Transfer Categories

```text
Transfer

Credit Card Payment

Cash Withdrawal
```

---

# 22. User Deletion Policy

Financial records must never be physically deleted.

---

## User Deletion

Soft delete only.

Status:

```text
DELETED
```

---

## Retained Data

```text
Transactions

Accounts

Audit Logs

Reports

Feedback
```

---

# 23. User Export

Future Feature.

Users may export:

```text
CSV

JSON

Excel
```

---

## Export Scope

```text
Transactions

Accounts

Reports

Categories

Settings
```

---

# 24. User Import

Future Feature.

Users may import:

```text
SMS History

CSV

Bank Statements

Account Aggregator Data
```

---

# 25. User Dashboard Preferences

Store:

```text
Default Date Range

Preferred Charts

Default Account View

Currency Display
```

---

# 26. User Currency Settings

Current:

```text
INR
```

Primary.

Future:

```text
USD

EUR

GBP

AED
```

Supported.

---

# 27. User Timezone

Default:

```text
Asia/Kolkata
```

Must be configurable.

---

Reason:

Future global users.

---

# 28. User Activity Tracking

Track:

```text
Last Login

Last API Request

Telegram Activity

Settings Changes
```

---

## Purpose

Security

Monitoring

Support

---

# 29. User Audit Events

Required:

```text
USER_REGISTERED

USER_LOGIN

USER_LOGOUT

PROFILE_UPDATED

SETTINGS_UPDATED

TELEGRAM_LINKED

TELEGRAM_UNLINKED

ACCOUNT_ARCHIVED
```

---

# 30. User Limits

MVP:

Unlimited.

---

Future SaaS:

Possible limits:

```text
Accounts Per User

Transactions Per Month

AI Requests

Exports
```

---

# 31. User Roles

Current:

```text
USER
```

Only.

---

Future:

```text
USER

ADMIN

SUPPORT

SUPER_ADMIN
```

---

# 32. Role Permissions

## USER

Can access:

```text
Own Data
```

Only.

---

## ADMIN

Can access:

```text
Platform Monitoring
```

Cannot modify financial records.

---

## SUPER_ADMIN

Can manage:

```text
System Configuration
```

Still subject to audit logging.

---

# 33. User API Contracts

Key APIs:

```text
GET /users/me

PATCH /users/me

GET /settings

PATCH /settings

POST /telegram/link

POST /telegram/unlink
```

---

# 34. User Notifications

Supported channels:

```text
Telegram
```

Current.

Future:

```text
Email

Push Notifications

WhatsApp
```

---

# 35. User Learning Preferences

Users may choose:

```text
Enable AI Learning

Disable AI Learning
```

---

## If Disabled

AI suggestions continue.

Learning does not persist.

---

# 36. User Financial Preferences

Store:

```text
Salary Account

Primary Account

Primary Credit Card

Preferred Budget Method
```

---

Future:

```text
Monthly Budget Goals

Savings Goals

Investment Goals
```

---

# 37. User Lifecycle

```text
Register
↓
Active
↓
Uses Platform
↓
Updates Preferences
↓
Provides Feedback
↓
AI Learns
↓
Long-Term Financial History
```

---

# 38. Future Family Accounts

Future Feature.

Support:

```text
Households

Shared Expenses

Multiple Members
```

---

Model:

```text
Household
↓
Users
↓
Shared Transactions
```

---

# 39. Future Subscription Plans

Potential:

```text
Free

Pro

Premium
```

---

Features:

```text
AI Insights

Advanced Reports

Account Aggregator

Investment Tracking
```

---

# 40. User Database Objects

Required Tables:

```text
users

user_settings

user_feedback
```

Future:

```text
user_roles

user_sessions

households

subscriptions

user_preferences_finance
```

---

# 41. AI Agent Implementation Rules

AI coding agents must:

* Attach user_id to all user-owned entities.
* Enforce ownership validation.
* Create default settings during registration.
* Create default categories during registration.
* Support Telegram linking.
* Support future multi-user growth.

AI coding agents must not:

* Allow cross-user access.
* Hard delete user financial data.
* Bypass ownership validation.
* Store settings inside users table.

---

# 42. Approval

Status: Approved

This document is the authoritative User Management Design for the Personal Finance Tracking Platform.

All user management functionality, ownership validation, settings management, Telegram integration, feedback systems, and future SaaS user features must comply with this specification.
