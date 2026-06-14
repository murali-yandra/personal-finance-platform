# ADR-009: Use JWT Authentication

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Security Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform requires a secure authentication mechanism for:

* User Login
* User Registration
* API Access
* Mobile Clients
* Web Clients
* Telegram Integration
* Future SaaS Expansion

The platform stores highly sensitive financial data:

```text
Bank Accounts
Credit Cards
Transactions
Income
Expenses
Balances
Financial Insights
```

Authentication must provide:

```text
Strong Security
Scalability
Statelessness
Developer Simplicity
Future SaaS Support
```

---

# Problem Statement

The system must identify:

```text
Who Is Making The Request
```

and determine:

```text
What Data They Can Access
```

Every request must support:

```text
Authentication

Authorization

Ownership Validation
```

The chosen authentication mechanism must work across:

```text
Web Applications

Mobile Applications

Telegram Integrations

Future APIs
```

without introducing server-side session complexity.

---

# Decision Drivers

## Security

Requirements:

```text
Strong Authentication

Secure Token Storage

Token Expiration

Revocation Support
```

---

## Scalability

Requirements:

```text
Stateless Authentication

Horizontal Scaling

Load Balancer Compatibility
```

---

## Developer Productivity

Requirements:

```text
FastAPI Support

OpenAPI Support

Simple Integration
```

---

## Future SaaS Support

Requirements:

```text
Multi User

Role Based Access

API Ecosystem
```

---

# Alternatives Considered

## Option 1 — JWT

Advantages:

```text
Stateless

Widely Adopted

Scalable

Mobile Friendly

API Friendly
```

Disadvantages:

```text
Requires Secure Token Management
```

---

## Option 2 — Server Sessions

Advantages:

```text
Simple Conceptually
```

Disadvantages:

```text
Server State

Scaling Complexity

Session Storage
```

---

## Option 3 — OAuth Provider Only

Examples:

```text
Google

Microsoft

GitHub
```

Advantages:

```text
User Convenience
```

Disadvantages:

```text
External Dependency

Not Required For MVP
```

---

## Option 4 — API Keys

Advantages:

```text
Simple
```

Disadvantages:

```text
Poor User Authentication

No User Sessions
```

API keys remain suitable only for:

```text
MacroDroid SMS Ingestion
```

---

# Decision

The platform shall use:

```text
JWT (JSON Web Tokens)
```

for user authentication.

Authentication shall be:

```text
Stateless
```

and validated on every request.

---

# Authentication Architecture

```text
User
 ↓
Login
 ↓
JWT Issued
 ↓
API Requests
 ↓
JWT Validation
 ↓
Current User
```

---

# Token Types

The platform shall use:

## Access Token

Purpose:

```text
API Access
```

Lifetime:

```text
15 Minutes
```

---

## Refresh Token

Purpose:

```text
Generate New Access Tokens
```

Lifetime:

```text
30 Days
```

---

# Session Management Principle

The platform shall maintain:

One User
↓
Multiple Sessions

Examples:

- Laptop
- Mobile App
- Future Web App

Each refresh token represents a session.

Future table:

user_sessions

Fields:

- session_id
- user_id
- device_name
- created_at
- last_seen_at
- refresh_token_hash
- revoked_at

This enables:

- View Active Sessions
- Revoke Individual Sessions
- Detect Suspicious Logins

---

# Login Flow

```text
User Login
 ↓
Validate Credentials
 ↓
Generate Access Token
 ↓
Generate Refresh Token
 ↓
Return Tokens
```

Response:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

---

# JWT Claims

Required claims:

```text
sub
user_id
email
role
iat
exp
jti
token_type
```

---

## Example

```json
{
  "sub": "user_uuid",
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "USER",
  "iat": 1717000000,
  "exp": 1717000900,
  "jti": "uuid",
  "token_type": "access"
}
```

---

# JWT Signing

Algorithm:

```text
HS256
```

MVP.

Future:

```text
RS256
```

for multi-service deployments.

---

# Password Storage

Passwords shall never be stored.

Store:

```text
password_hash
```

only.

Algorithm:

```text
Argon2
```

---

Forbidden:

```text
MD5

SHA1

SHA256 Only
```

---

# Authorization Model

Authentication identifies:

```text
Who
```

Authorization determines:

```text
What
```

---

# Ownership Validation Rule

Every user-owned entity contains:

```text
user_id
```

Every query must enforce:

```sql
WHERE user_id = :current_user_id
```

JWT alone is not authorization.

---

# Protected Endpoints

Examples:

```text
/accounts

/transactions

/reports

/settings
```

Require:

```text
Valid JWT
```

---

# Public Endpoints

Examples:

```text
/health

/auth/login

/auth/register

/auth/refresh
```

Do not require an access token. Refresh requests must submit a valid refresh
token in the request body.

---

# Refresh Flow

```text
Access Token Expired
 ↓
Send Refresh Token
 ↓
Validate Refresh Token
 ↓
Issue New Access Token
```

---

# Logout Strategy

MVP:

```text
Client Deletes Tokens
```

---

Future:

```text
Refresh Token Revocation
```

using:

```text
token_blacklist
```

table.

---

# Token Storage

## Web

Store:

```text
HTTP Only Cookies
```

Preferred.

---

## Mobile

Store:

```text
Secure Storage
```

Examples:

```text
Android Keystore

iOS Keychain
```

---

Forbidden:

```text
LocalStorage
```

for sensitive production environments.

---

# Telegram Authentication Rule

Telegram is:

```text
Communication Channel
```

Only.

---

Telegram is NOT:

```text
Authentication Provider
```

User identity must be mapped through:

```text
telegram_chat_id
```

to a valid authenticated user.

---

# MacroDroid Authentication Rule

MacroDroid shall not use JWT.

MacroDroid shall use:

```text
API Key Authentication
```

Reason:

```text
Machine To Machine Communication
```

---

# Token Expiration Standards

Access Token:

```text
15 Minutes
```

---

Refresh Token:

```text
30 Days
```

---

Future:

Configurable.

---

# MFA Future Support

Future authentication may support:

```text
TOTP

Authenticator Apps

Passkeys
```

without changing JWT architecture.

---

# Security Requirements

JWT Secret:

```text
Environment Variable
```

Only.

---

Forbidden:

```text
Hardcoded Secrets
```

---

JWT Secret Rotation:

Future support required.

---

# Audit Requirements

Log:

```text
Login Success

Login Failure

Logout

Password Change

Token Refresh
```

Store in:

```text
audit_log
```

---

# Rate Limiting

Future support:

```text
Login Attempts

Password Reset Requests

Token Refresh Requests
```

---

# Operational Benefits

Advantages:

```text
Stateless

Simple Deployment

Horizontal Scaling

Cloud Ready
```

---

# Financial Benefits

Advantages:

```text
Strong User Isolation

Secure Financial Access

Reduced Risk Of Data Leakage
```

---

# Consequences

## Positive Consequences

### Scalable

Works across multiple FastAPI instances.

---

### Stateless

No session storage required.

---

### API Friendly

Excellent support for future mobile and web apps.

---

### Standards Based

Industry standard approach.

---

## Negative Consequences

### Token Management Complexity

Requires expiration and refresh handling.

---

### Revocation Complexity

Immediate invalidation requires additional mechanisms.

---

# Authentication Boundary Rule

Authentication determines:

```text
Who Is Calling
```

Authorization determines:

```text
What They Can Access
```

The platform must never assume:

```text
Valid JWT
=
Access To Resource
```

Ownership validation is always required.

---

# Rejected Alternatives

## Server Sessions

Rejected because:

```text
Stateful

Harder To Scale
```

---

## API Keys For Users

Rejected because:

```text
Weak User Experience

Poor Session Management
```

---

## OAuth Only

Rejected because:

```text
Not Required For MVP
```

---

# Review Criteria

This ADR should be revisited if:

```text
Multiple External Identity Providers Added

Enterprise SSO Required

Multi-Service Architecture Introduced
```

---

# Related Documents

```text
16-authentication_design.md

10-security_standards.md

17-user_management.md

08-api_contracts.md
```

---

# JWT First Principle

The platform follows:

```text
JWT
↓
Ownership Validation
↓
Business Logic
```

Never:

```text
JWT
↓
Business Logic
```

without ownership validation.

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall use JWT authentication with short-lived access tokens and long-lived refresh tokens.

JWT will provide scalable, stateless authentication while ownership validation and authorization rules enforce secure access to financial data.
