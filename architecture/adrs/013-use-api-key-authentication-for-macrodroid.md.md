# ADR-013: Use API Key Authentication for MacroDroid

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Security Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform receives SMS messages from Android devices through MacroDroid.

Architecture:

```text
Incoming SMS
      ↓
Android Device
      ↓
MacroDroid
      ↓
FastAPI
      ↓
PostgreSQL
```

MacroDroid acts as a machine-to-machine integration.

It is not:

```text
A User

A Browser

A Mobile App Session

An Interactive Client
```

The platform requires a secure authentication mechanism for SMS ingestion APIs.

---

# Problem Statement

The ingestion endpoint:

```http
POST /api/v1/ingest/sms
```

must be protected against:

```text
Unauthorized Requests

Spam Requests

Malicious Traffic

Fake SMS Payloads

Data Pollution
```

The authentication method must work within MacroDroid's capabilities.

Requirements:

```text
Simple Configuration

Machine Authentication

Low Complexity

Secure Enough For MVP

Easy Rotation
```

---

# Decision Drivers

## Simplicity

Requirements:

```text
Easy To Configure

Easy To Rotate

Minimal Development Effort
```

---

## Security

Requirements:

```text
Request Authentication

Secret Validation

Unauthorized Access Prevention
```

---

## MacroDroid Compatibility

Requirements:

```text
HTTP Headers

Simple Request Configuration

No Login Flow
```

---

## Future Migration

Requirements:

```text
Device Registration

Multiple Devices

Future OAuth Migration
```

---

# Alternatives Considered

## Option 1 — API Key

Advantages:

```text
Simple

Lightweight

Machine Friendly

Easy To Implement
```

Disadvantages:

```text
Single Shared Secret
```

---

## Option 2 — JWT

Advantages:

```text
Industry Standard

Scalable
```

Disadvantages:

```text
Requires Login Flow

Token Refresh

Not Suitable For MacroDroid
```

---

## Option 3 — Mutual TLS

Advantages:

```text
Very Secure
```

Disadvantages:

```text
Complex

Certificate Management

Overkill For MVP
```

---

## Option 4 — Anonymous Access

Advantages:

```text
Simple
```

Disadvantages:

```text
Completely Insecure
```

---

# Decision

The platform shall use:

```text
API Key Authentication
```

for all MacroDroid ingestion endpoints.

JWT authentication shall not be used for MacroDroid.

---

# Authentication Architecture

```text
MacroDroid
     ↓
API Key
     ↓
FastAPI Middleware
     ↓
Endpoint Access
```

---

# Header Standard

MacroDroid must send:

```http
X-API-KEY: <secret>
```

Example:

```http
POST /api/v1/ingest/sms

X-API-KEY: finance_ingest_xxxxxx
```

---

# API Key Storage

API keys must never be hardcoded.

Store in:

```text
Environment Variables

Docker Secrets

Vault (Future)
```

Example:

```env
INGEST_API_KEY=finance_ingest_xxxxxx
```

---

# Validation Flow

```text
Request Arrives
      ↓
Read X-API-KEY
      ↓
Validate Secret
      ↓
Allow Request
```

Invalid:

```text
401 Unauthorized
```

---

# Protected Endpoints

The following endpoints require API key authentication:

```text
POST /api/v1/ingest/sms

POST /api/v1/ingest/bulk-sms

POST /api/v1/ingest/raw-event
```

---

# User APIs

User-facing APIs shall not use API keys.

Examples:

```text
/accounts

/transactions

/reports

/settings
```

These endpoints use:

```text
JWT Authentication
```

---

# Separation Principle

Authentication methods:

```text
Users
↓
JWT

Machines
↓
API Key
```

Never:

```text
Users
↓
API Key
```

Never:

```text
Machines
↓
JWT Login
```

---

# Device Ownership Model

Current MVP:

```text
One User
One Device
One API Key
```

Future:

```text
Multiple Users
Multiple Devices
Multiple API Keys
```

---

# Trusted Device Principle

SMS ingestion is considered a trusted-device workflow.

Trust boundary:

User Device
↓
MacroDroid
↓
API Key
↓
Backend

The backend trusts SMS payloads only after:

- API Key Validation
- Device Validation (Future)
- Schema Validation
- Duplicate Detection

Receiving a valid API key does not automatically make the payload valid.

All SMS messages must still pass:

- Spam Detection
- Parser Validation
- Duplicate Checks
- Transaction Validation

before financial records are created.

---

# Future Device Registration

Future table:

```text
device_registrations
```

Fields:

```text
id

user_id

device_name

device_type

api_key_hash

created_at

last_seen_at

is_active
```

---

# API Key Hashing Rule

API keys must never be stored in plain text.

Store:

```text
api_key_hash
```

Example:

```text
SHA256(api_key)
```

Stored:

```text
ABCD1234HASH...
```

Not:

```text
finance_ingest_xxxxxx
```

---

# Key Rotation Strategy

Supported workflow:

```text
Generate New Key
↓
Update MacroDroid
↓
Verify Traffic
↓
Deactivate Old Key
```

---

# Revocation Strategy

Compromised keys must support:

```text
Immediate Revocation
```

Future table:

```text
api_keys
```

Fields:

```text
id

name

api_key_hash

created_at

expires_at

revoked_at
```

---

# Rate Limiting

Future support:

```text
Requests Per Minute

Requests Per Device

Requests Per API Key
```

Examples:

```text
60 Requests / Minute
```

---

# Request Logging

Every API key request must log:

```text
timestamp

ip_address

endpoint

request_id

api_key_id
```

Store:

```text
audit_log
```

---

# Security Requirements

API keys must never:

```text
Appear In Logs

Appear In Error Messages

Appear In Responses
```

---

# HTTPS Requirement

API keys shall only be transmitted over:

```text
HTTPS
```

Forbidden:

```text
HTTP
```

in production environments.

---

# Local Development

Allowed:

```text
http://localhost
```

only.

---

# Failed Authentication Handling

Invalid key:

```http
401 Unauthorized
```

Response:

```json
{
  "error": "invalid_api_key"
}
```

---

No information leakage:

Forbidden:

```json
{
  "error": "api_key_not_found"
}
```

---

# Future SaaS Architecture

Future:

```text
User
 ↓
Device
 ↓
API Key
 ↓
Ingestion API
```

Each device may have:

```text
Unique API Key
```

---

# Operational Benefits

Advantages:

```text
Simple Setup

Easy MacroDroid Integration

Low Maintenance

Low Overhead
```

---

# Security Benefits

Advantages:

```text
Endpoint Protection

Machine Authentication

Supports Rotation

Supports Revocation
```

---

# Consequences

## Positive Consequences

### Easy To Implement

Minimal development effort.

---

### MacroDroid Compatible

Works with built-in HTTP actions.

---

### Future Device Support

Can evolve to multiple devices.

---

### Clear Security Boundary

Separates machine authentication from user authentication.

---

## Negative Consequences

### Shared Secret Risk

Compromised key requires rotation.

---

### Key Management

Requires secure storage.

---

# API Key Scope Rule

API keys shall be scoped.

Current scope:

```text
sms_ingestion
```

Future scopes:

```text
sms_ingestion

csv_import

account_aggregator

admin_automation
```

An API key may only access endpoints assigned to its scope.

---

# Authentication Layer Order

Request Processing:

```text
Request
↓
Request ID
↓
API Key Validation
↓
Rate Limiting
↓
Business Logic
```

---

# Rejected Alternatives

## JWT For MacroDroid

Rejected because:

```text
Requires Login

Requires Refresh Tokens

Unnecessary Complexity
```

---

## Mutual TLS

Rejected because:

```text
Operational Complexity

Certificate Management Overhead
```

---

## Anonymous Access

Rejected because:

```text
Security Risk

Spam Risk

Data Corruption Risk
```

---

# Review Criteria

This ADR should be revisited if:

```text
Multiple Devices Per User Become Common

Native Mobile Apps Replace MacroDroid

Enterprise Integrations Are Added

Mutual TLS Becomes Necessary
```

---

# Related Documents

```text
ADR-005-use-macrodroid-for-sms-ingestion.md

ADR-009-use-jwt-authentication.md

10-security_standards.md

16-authentication_design.md

17-user_management.md
```

---

# Machine Authentication Principle

The platform follows:

```text
User
↓
JWT

Machine
↓
API Key
```

Authentication methods are selected based on actor type, not technology preference.

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall use API Key Authentication for MacroDroid and other machine-to-machine ingestion integrations.

JWT authentication remains reserved for human users, while API keys provide a lightweight, secure, and operationally simple mechanism for SMS ingestion and future automation workflows.
