# 10-security_standards.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Security Standards

Architecture Style: Modular Monolith

Framework: FastAPI

Database: PostgreSQL

Authentication: JWT

Last Updated: 2026-06-14

---

# 1. Purpose

This document defines the security standards for the Personal Finance Tracking Platform.

The platform processes highly sensitive financial information including:

* Bank transaction data
* Credit card transaction data
* Income records
* Account balances
* User identities
* Financial habits

Security is therefore a first-class requirement.

This document defines:

* Authentication
* Authorization
* Data Protection
* Secrets Management
* Infrastructure Security
* API Security
* Audit Requirements
* AI Security Rules
* Future SaaS Security Requirements

---

# 2. Security Principles

## Principle 1

Default Deny.

Everything is denied unless explicitly allowed.

---

## Principle 2

Least Privilege.

Every user, service, API, and module receives only the minimum permissions required.

---

## Principle 3

Defense In Depth.

Security controls must exist at multiple layers:

```text
Network
↓
API
↓
Authentication
↓
Authorization
↓
Database
↓
Audit
```

---

## Principle 4

Financial Data Integrity.

Financial records must be protected against:

* Unauthorized modification
* Unauthorized deletion
* Tampering
* Data corruption

---

## Principle 5

Traceability.

Every important financial change must be auditable.

---

## Principle 6

Zero Trust Between Users.

Every request must validate ownership.

Never assume trust.

---

# 3. Data Classification

The system stores different classifications of data.

---

## Public Data

Examples:

```text
System Categories
Global Merchant Definitions
Application Metadata
```

Risk Level:

```text
LOW
```

---

## Internal Data

Examples:

```text
Application Logs
Health Metrics
Processing Statistics
```

Risk Level:

```text
MEDIUM
```

---

## Sensitive Data

Examples:

```text
Email Address
Telegram Chat ID
Account Names
```

Risk Level:

```text
HIGH
```

---

## Highly Sensitive Data

Examples:

```text
SMS Messages
Financial Transactions
Account Balances
Credit Card Information
Income Records
```

Risk Level:

```text
CRITICAL
```

---

# 4. Authentication Standards

## Authentication Method

Selected:

```text
JWT Authentication
```

Components:

```text
Access Token
Refresh Token
```

---

## Password Storage

Passwords must never be stored.

Store only:

```text
Argon2 Hash
```

Example:

```text
argon2id
```

Forbidden:

```text
MD5
SHA1
Plain Text
Base64
```

---

## Password Policy

Minimum:

```text
8 Characters
```

Recommended:

```text
12+ Characters
```

Require:

```text
Uppercase
Lowercase
Number
```

Special characters optional.

---

## Account Lockout

After:

```text
5 Failed Login Attempts
```

Lock account for:

```text
15 Minutes
```

Future SaaS Requirement.

---

# 5. JWT Standards

## Access Token

Lifetime:

```text
15 Minutes
```

---

## Refresh Token

Lifetime:

```text
30 Days
```

---

## JWT Claims

Required:

```json
{
  "sub": "user_id",
  "user_id": "user_id",
  "email": "user_email",
  "role": "USER",
  "token_type": "access",
  "iat": 123456000,
  "exp": 123456900,
  "jti": "token_uuid"
}
```

---

## JWT Signing

Algorithm:

```text
HS256
```

MVP

Future SaaS:

```text
RS256
```

---

## JWT Storage

Frontend:

```text
HttpOnly Cookies
```

Preferred.

Alternative:

```text
Secure Storage
```

for mobile.

---

# 6. Authorization Standards

Authorization must occur on every request.

---

## Ownership Rule

Every query must include:

```python
transaction.user_id == current_user.id
```

Never:

```python
SELECT * FROM transactions WHERE id = ?
```

Always:

```python
SELECT *
FROM transactions
WHERE id = ?
AND user_id = ?
```

---

## Protected Resources

Must validate ownership:

```text
Accounts
Transactions
Transfers
Balance Snapshots
Feedback
Audit Records
```

---

## Multi-Tenant Security Rule

No user must ever access another user's data.

This is a critical security requirement.

---

# 7. API Security Standards

## HTTPS Only

Production:

```text
HTTPS Required
```

No HTTP.

---

## TLS Version

Minimum:

```text
TLS 1.2
```

Recommended:

```text
TLS 1.3
```

---

## Request Validation

All request bodies must be validated using:

```text
Pydantic Models
```

Before entering business logic.

---

## Request Size Limits

Recommended:

```text
1 MB
```

Maximum:

```text
10 MB
```

---

## API Rate Limiting

Future SaaS Requirement.

Recommended:

```text
100 Requests / Minute / User
```

---

## API Key Security

MacroDroid endpoint requires:

```text
X-API-KEY
```

Header.

Example:

```http
POST /api/v1/ingest/sms

X-API-KEY: abc123
```

---

## API Key Storage

Store hashed API keys.

Never store plaintext.

---

# 8. SMS Security Standards

SMS data is highly sensitive.

---

## Raw SMS Storage

Allowed:

```text
Store original SMS
```

Required for:

* Traceability
* Reprocessing
* Auditing

---

## SMS Access

Only:

```text
Owner
Admin (future)
```

may access SMS content.

---

## SMS Export

Exports must require authentication.

---

## SMS Deletion

Not supported in MVP.

Future:

Soft delete only.

---

# 9. Database Security Standards

## Database Access

Application users must not connect directly.

All access through backend APIs.

---

## Principle of Least Privilege

Application database user should have only:

```text
SELECT
INSERT
UPDATE
DELETE
```

on required tables.

No superuser privileges.

---

## Production Database User

Forbidden:

```text
postgres
```

Create dedicated service account.

Example:

```text
finance_app_user
```

---

## Database Backups

Backups must be encrypted.

---

## Backup Retention

Recommended:

```text
Daily Backups
30 Day Retention
```

---

# 10. Secrets Management

## Secrets

Examples:

```text
JWT Secret
Database Password
Telegram Bot Token
API Keys
Encryption Keys
```

---

## Storage Method

Use:

```text
Environment Variables
```

MVP

Future:

```text
Vault
AWS Secrets Manager
GCP Secret Manager
Azure Key Vault
```

---

## Git Rules

Never commit:

```text
.env
secrets.json
private.pem
```

---

## Required Files

```text
.env.example
```

must be committed.

---

# 11. Logging Security

## Never Log

```text
Passwords
JWT Tokens
Refresh Tokens
Credit Card Numbers
Full Account Numbers
Secrets
```

Forbidden.

---

## Mask Sensitive Values

Example:

Instead of:

```text
Account: 1234567890
```

Log:

```text
Account: ******7890
```

---

## Structured Logging

Required fields:

```text
Timestamp
Request ID
Correlation ID
User ID
Module
Event Type
```

---

# 12. Audit Security

Audit logs are immutable.

---

## Audit Events Required

Examples:

```text
Login
Password Change
Account Update
Category Change
Description Update
Balance Reconciliation
Transfer Confirmation
```

---

## Audit Protection

Audit logs must:

```text
Never Be Updated
Never Be Deleted
```

Append only.

---

# 13. Financial Data Integrity

## Rule 1

Transactions cannot be hard deleted.

---

## Rule 2

Raw Events cannot be hard deleted.

---

## Rule 3

Audit Logs cannot be modified.

---

## Rule 4

Balance updates must occur inside database transactions.

---

## Rule 5

Transaction creation and balance update must commit together.

---

# 14. Credit Card Data Standards

The platform is not intended to store full card details.

Allowed:

```text
Last Four Digits
Card Nickname
Issuer
```

Forbidden:

```text
Full PAN
CVV
PIN
```

---

# 15. Telegram Security Standards

## Telegram Chat Validation

Every webhook request must validate:

```text
Telegram Chat ID
```

against user mapping.

---

## User Mapping

One Telegram chat should map to one user.

---

## Sensitive Operations

Examples:

```text
Balance Reconciliation
Account Rename
Transfer Confirmation
```

must validate ownership before execution.

---

# 16. AI Security Standards

AI is advisory only.

---

## AI Cannot

```text
Create Transactions
Delete Transactions
Modify Balances
Modify Audit Logs
Change Ownership
```

---

## AI Can

```text
Suggest Categories
Suggest Merchants
Suggest Descriptions
Generate Reports
```

---

## AI Prompt Security

Never send:

```text
Passwords
Secrets
JWT Tokens
Database Credentials
```

to AI systems.

---

## Local AI Preference

Preferred:

```text
Ollama
Qwen
Llama
Gemma
```

Reason:

Financial data remains local.

---

# 17. File Upload Security

Future feature.

Requirements:

```text
Virus Scan
Content Validation
File Size Limits
```

---

## Allowed Formats

```text
CSV
PDF
JSON
```

Future.

---

# 18. Historical Import Security

Historical SMS imports may contain years of financial data.

Requirements:

```text
Authenticated User
Ownership Validation
Audit Logging
```

---

## Import Limits

Recommended:

```text
10,000 Messages Per Batch
```

Maximum:

```text
100,000 Messages
```

with chunking.

---

# 19. Infrastructure Security

## Docker

Containers must run:

```text
Non-Root User
```

---

## Container Images

Use:

```text
Official Images
```

or trusted sources only.

---

## Firewall

Expose only:

```text
443 HTTPS
```

Production.

---

## PostgreSQL

Never expose publicly.

Only backend should access PostgreSQL.

---

# 20. Dependency Security

Dependencies must be scanned.

Recommended tools:

```text
pip-audit
safety
dependabot
```

---

## Update Policy

Security patches:

```text
Immediately
```

Critical vulnerabilities:

```text
Within 24 Hours
```

---

# 21. Future SaaS Security Requirements

When platform becomes multi-user:

Required additions:

```text
Rate Limiting
MFA
Email Verification
RBAC
Security Monitoring
WAF
SOC Logging
```

---

## Recommended MFA

```text
TOTP
Authenticator Apps
```

Preferred over SMS.

---

# 22. Incident Response

## Security Incident Examples

```text
Data Leak
Unauthorized Access
Credential Exposure
Database Compromise
```

---

## Response Process

```text
Detect
Contain
Investigate
Recover
Document
```

---

## Audit Requirement

All incidents must generate audit records.

---

# 23. Security Checklist

Before Production Release:

* HTTPS Enabled
* JWT Enabled
* Ownership Validation Implemented
* Audit Logging Enabled
* Secrets Externalized
* Database Backups Enabled
* API Keys Configured
* Structured Logging Enabled
* Error Handling Implemented
* Dependency Scan Passed

---

# 24. AI Agent Implementation Rules

AI coding agents must:

* Use Argon2 password hashing.
* Use JWT authentication.
* Validate ownership on every query.
* Use HTTPS assumptions.
* Store secrets in environment variables.
* Implement audit logging.
* Use database transactions for financial operations.
* Mask sensitive values in logs.

AI coding agents must not:

* Store plaintext passwords.
* Store full card numbers.
* Log JWT tokens.
* Disable ownership checks.
* Allow hard deletes for financial records.
* Commit secrets to Git.

---

# 25. Approval

Status: Approved

This document is the authoritative security standard for the Personal Finance Tracking Platform.

All backend services, APIs, workers, Telegram integrations, AI modules, and future SaaS components must comply with these standards.
