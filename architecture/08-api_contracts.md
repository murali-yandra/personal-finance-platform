# 08-api_contracts.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: API Contracts Specification

Architecture Style: REST API

Framework: FastAPI

Authentication: JWT

Content-Type: application/json

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines all API contracts for the Personal Finance Tracking Platform.

It serves as the authoritative specification for:

* FastAPI Routes
* Request Models
* Response Models
* DTOs
* Validation Rules
* Authentication
* Error Handling

This document must be used by:

* Backend Developers
* Frontend Developers
* Mobile Developers
* AI Coding Agents
* QA Engineers

---

# 2. API Design Principles

## 2.1 RESTful Design

All APIs shall follow REST principles.

Examples:

```http
GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/{id}
PATCH  /api/v1/accounts/{id}
DELETE /api/v1/accounts/{id}
```

---

## 2.2 JSON Only

All requests and responses must use:

```http
Content-Type: application/json
```

---

## 2.3 JWT Authentication

All endpoints require JWT except:

```text
POST /auth/register
POST /auth/login
GET  /health
```

---

## 2.4 UUID Identifiers

All entity identifiers use UUID.

Example:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 2.5 Consistent Response Format

All successful responses must follow:

```json
{
  "success": true,
  "data": {},
  "meta": {}
}
```

---

## 2.6 Consistent Error Format

All failures must follow:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Amount must be greater than zero"
  }
}
```

---

# 3. Authentication APIs

Base Path:

```text
/api/v1/auth
```

---

# 3.1 Register

Endpoint:

```http
POST /api/v1/auth/register
```

Purpose:

Create user account.

Request:

```json
{
  "email": "murali@example.com",
  "password": "StrongPassword123",
  "display_name": "Murali Yandra"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "user_id": "uuid"
  }
}
```

Validation:

* Email required
* Email unique
* Password minimum 8 chars

---

# 3.2 Login

Endpoint:

```http
POST /api/v1/auth/login
```

Request:

```json
{
  "email": "murali@example.com",
  "password": "StrongPassword123"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "access_token": "jwt",
    "refresh_token": "jwt",
    "expires_in": 3600
  }
}
```

---

# 3.3 Refresh Token

Endpoint:

```http
POST /api/v1/auth/refresh
```

Request:

```json
{
  "refresh_token": "jwt"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "access_token": "new_jwt"
  }
}
```

---

# 4. User APIs

Base Path:

```text
/api/v1/users
```

---

# 4.1 Get Current User

Endpoint:

```http
GET /api/v1/users/me
```

Response:

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "email": "murali@example.com",
    "display_name": "Murali Yandra",
    "timezone": "Asia/Kolkata",
    "default_currency": "INR"
  }
}
```

---

# 4.2 Update User

Endpoint:

```http
PATCH /api/v1/users/me
```

Request:

```json
{
  "display_name": "Murali",
  "timezone": "Asia/Kolkata"
}
```

---

# 5. User Settings APIs

Base Path:

```text
/api/v1/settings
```

---

# 5.1 Get Settings

Endpoint:

```http
GET /api/v1/settings
```

Response:

```json
{
  "success": true,
  "data": {
    "notification_mode": "LOW_CONFIDENCE_ONLY",
    "ai_suggestions_enabled": false,
    "preferred_language": "en"
  }
}
```

---

# 5.2 Update Settings

Endpoint:

```http
PATCH /api/v1/settings
```

Request:

```json
{
  "notification_mode": "ALWAYS",
  "ai_suggestions_enabled": true
}
```

---

# 6. SMS Ingestion APIs

Base Path:

```text
/api/v1/ingest
```

---

# 6.1 Ingest SMS

Used by:

```text
MacroDroid
Future Android App
```

Endpoint:

```http
POST /api/v1/ingest/sms
```

Authentication:

```text
API Key
```

Request:

```json
{
  "sender": "VK-HDFCBK",
  "message_text": "Rs.70 debited from A/C XXXX0452 at SmartQ",
  "received_at": "2026-06-02T10:00:00Z"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "raw_event_id": "uuid",
    "status": "RECEIVED"
  }
}
```

---

# 6.2 Batch SMS Import

Endpoint:

```http
POST /api/v1/ingest/sms/batch
```

Request:

```json
{
  "messages": [
    {
      "sender": "VK-HDFCBK",
      "message_text": "...",
      "received_at": "..."
    }
  ]
}
```

Response:

```json
{
  "success": true,
  "data": {
    "accepted": 500,
    "duplicates": 20
  }
}
```

---

# 7. Accounts APIs

Base Path:

```text
/api/v1/accounts
```

---

# 7.1 Get Accounts

Endpoint:

```http
GET /api/v1/accounts
```

Response:

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "account_name": "Salary Account",
      "account_type": "BANK",
      "estimated_balance": 25000
    }
  ]
}
```

---

# 7.2 Get Account

Endpoint:

```http
GET /api/v1/accounts/{account_id}
```

---

# 7.3 Update Account

Endpoint:

```http
PATCH /api/v1/accounts/{account_id}
```

Request:

```json
{
  "account_name": "Salary Account",
  "status": "ACTIVE"
}
```

Audit Required:

```text
Yes
```

---

# 7.4 Reconcile Account Balance

Endpoint:

```http
POST /api/v1/accounts/{account_id}/reconcile
```

Request:

```json
{
  "actual_balance": 25000
}
```

Response:

```json
{
  "success": true,
  "data": {
    "estimated_balance": 24800,
    "actual_balance": 25000,
    "difference": 200
  }
}
```

---

# 8. Transactions APIs

Base Path:

```text
/api/v1/transactions
```

---

# 8.1 List Transactions

Endpoint:

```http
GET /api/v1/transactions
```

Supported Filters:

```text
account_id
category_id
merchant_id
business_type
start_date
end_date
```

Example:

```http
GET /api/v1/transactions?category_id=uuid
```

---

# 8.2 Get Transaction

Endpoint:

```http
GET /api/v1/transactions/{transaction_id}
```

---

# 8.3 Update Transaction

Endpoint:

```http
PATCH /api/v1/transactions/{transaction_id}
```

Request:

```json
{
  "description": "Lunch with team",
  "category_id": "uuid"
}
```

Audit Required:

```text
Yes
```

---

# 8.4 Manually Create Transaction

Future Use.

Endpoint:

```http
POST /api/v1/transactions
```

Request:

```json
{
  "account_id": "uuid",
  "amount": 100,
  "currency": "INR",
  "business_type": "EXPENSE"
}
```

---

# 9. Categories APIs

Base Path:

```text
/api/v1/categories
```

---

# 9.1 List Categories

Endpoint:

```http
GET /api/v1/categories
```

---

# 9.2 Create Category

Endpoint:

```http
POST /api/v1/categories
```

Request:

```json
{
  "name": "Pets"
}
```

---

# 9.3 Update Category

Endpoint:

```http
PATCH /api/v1/categories/{category_id}
```

---

# 10. Merchants APIs

Base Path:

```text
/api/v1/merchants
```

---

# 10.1 List Merchants

Endpoint:

```http
GET /api/v1/merchants
```

---

# 10.2 Get Merchant

Endpoint:

```http
GET /api/v1/merchants/{merchant_id}
```

---

# 10.3 Create Merchant Pattern

Endpoint:

```http
POST /api/v1/merchants/patterns
```

Request:

```json
{
  "merchant_id": "uuid",
  "pattern": "KA51AJ%",
  "pattern_type": "LIKE"
}
```

---

# 11. Transfers APIs

Base Path:

```text
/api/v1/transfers
```

---

# 11.1 List Transfers

Endpoint:

```http
GET /api/v1/transfers
```

---

# 11.2 Confirm Transfer

Endpoint:

```http
POST /api/v1/transfers/{transfer_id}/confirm
```

Request:

```json
{
  "confirmed": true
}
```

---

# 12. Reporting APIs

Base Path:

```text
/api/v1/reports
```

---

# 12.1 Monthly Summary

Endpoint:

```http
GET /api/v1/reports/monthly-summary
```

Parameters:

```text
year
month
```

Example:

```http
GET /api/v1/reports/monthly-summary?year=2026&month=6
```

Response:

```json
{
  "success": true,
  "data": {
    "income": 80000,
    "expenses": 35000,
    "savings": 45000
  }
}
```

---

# 12.2 Category Breakdown

Endpoint:

```http
GET /api/v1/reports/category-breakdown
```

Response:

```json
{
  "success": true,
  "data": [
    {
      "category": "Food",
      "amount": 5000
    }
  ]
}
```

---

# 12.3 Net Worth

Endpoint:

```http
GET /api/v1/reports/net-worth
```

Response:

```json
{
  "success": true,
  "data": {
    "assets": 500000,
    "liabilities": 100000,
    "net_worth": 400000
  }
}
```

---

# 13. Telegram APIs

Base Path:

```text
/api/v1/telegram
```

---

# 13.1 Telegram Webhook

Endpoint:

```http
POST /api/v1/telegram/webhook
```

Purpose:

Receive Telegram bot updates.

Internal endpoint only.

---

# 13.2 Telegram Test Message

Endpoint:

```http
POST /api/v1/telegram/test
```

Request:

```json
{
  "message": "Hello World"
}
```

---

# 14. Audit APIs

Base Path:

```text
/api/v1/audit
```

---

# 14.1 List Audit Records

Endpoint:

```http
GET /api/v1/audit
```

Filters:

```text
entity_type
entity_id
start_date
end_date
```

---

# 15. Health APIs

Base Path:

```text
/api/v1/health
```

---

# 15.1 Health Check

Endpoint:

```http
GET /api/v1/health
```

Response:

```json
{
  "status": "healthy"
}
```

---

# 16. Pagination Standard

List APIs must support:

```text
page
page_size
sort
order
```

Example:

```http
GET /transactions?page=1&page_size=50
```

Response:

```json
{
  "success": true,
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 50,
    "total_records": 1200
  }
}
```

---

# 17. Security Requirements

All authenticated APIs must:

* Validate JWT
* Validate user ownership
* Log audit events
* Prevent cross-user access

---

# 18. AI Agent Implementation Rules

AI coding agents must:

* Generate Pydantic DTOs
* Generate OpenAPI documentation
* Validate UUID parameters
* Validate enum values
* Use pagination
* Use consistent response envelopes
* Generate repository layer
* Generate service layer

AI coding agents must not:

* Return raw SQL errors
* Skip ownership validation
* Skip audit logging
* Use integer IDs
* Put business logic inside controllers

---

# 19. API Versioning Strategy

Current Version:

```text
v1
```

Base Path:

```text
/api/v1
```

Future:

```text
/api/v2
```

Must not break v1 consumers.

---

# 20. Approval

Status: Approved

This document is the authoritative API contract specification for the Personal Finance Tracking Platform.

All FastAPI routes, DTOs, OpenAPI schemas, service interfaces, and client integrations must comply with this specification.
