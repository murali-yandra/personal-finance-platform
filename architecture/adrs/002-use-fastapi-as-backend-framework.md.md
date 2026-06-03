# ADR-002: Use FastAPI as Backend Framework

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform requires a backend framework capable of supporting:

* REST APIs
* JWT Authentication
* User Management
* SMS Ingestion APIs
* Telegram Webhooks
* AI Service Integration
* Financial Transaction Processing
* Future SaaS Expansion

The backend framework must support both:

## Current MVP

```text
Single User
Docker Deployment
PostgreSQL
Telegram Bot
MacroDroid SMS Ingestion
```

and

## Future Scale

```text
Thousands of Users
Millions of Transactions
Multi-Tenant SaaS
AI Services
Mobile Applications
```

The selected framework must enable rapid development without compromising maintainability, security, performance, or scalability.

---

# Decision Drivers

The backend framework must provide:

## API Development

Requirements:

```text
REST APIs
JSON Support
Request Validation
Response Validation
OpenAPI Documentation
```

---

## Security

Requirements:

```text
JWT Authentication
Dependency Injection
Role-Based Authorization Support
Secure Request Handling
```

---

## Developer Productivity

Requirements:

```text
Python Ecosystem
Strong Typing
IDE Support
AI-Friendly Code Generation
```

---

## Scalability

Requirements:

```text
Async Support
Background Tasks
High Concurrency
Future Horizontal Scaling
```

---

## Integration Requirements

The platform must integrate with:

```text
PostgreSQL
Telegram
Ollama
Future Account Aggregator
Future Mobile Apps
```

---

# Alternatives Considered

## Option 1 — FastAPI

Advantages:

```text
High Performance
Native Async Support
Automatic OpenAPI
Pydantic Validation
Strong Typing
Dependency Injection
Excellent Documentation
Modern Python Design
```

Disadvantages:

```text
Smaller Ecosystem Than Django
Requires More Architecture Decisions
```

---

## Option 2 — Flask

Advantages:

```text
Simple
Flexible
Large Community
```

Disadvantages:

```text
No Built-In Validation
No Native OpenAPI
More Boilerplate
Requires Additional Libraries
```

---

## Option 3 — Django

Advantages:

```text
Mature Ecosystem
Built-In Admin
ORM Included
Authentication Included
```

Disadvantages:

```text
Heavier Framework
Less API-Centric
More Components Than Required
```

---

## Option 4 — Spring Boot

Advantages:

```text
Enterprise Ready
Extremely Mature
Scalable
```

Disadvantages:

```text
Java Ecosystem
Higher Complexity
Longer Development Time
```

---

## Option 5 — Node.js / Express

Advantages:

```text
Large Ecosystem
Fast Development
```

Disadvantages:

```text
Weaker Type Safety
Less Alignment With Python AI Stack
Additional Complexity For AI Integration
```

---

# Decision

The platform will use:

```text
FastAPI
```

as the primary backend framework.

FastAPI shall serve as the entry point for:

```text
Authentication APIs
User APIs
Account APIs
Transaction APIs
Reporting APIs
Telegram Webhooks
SMS Ingestion APIs
Future AI APIs
```

---

# Architecture Implications

The platform architecture becomes:

```text
Client
    ↓
FastAPI
    ↓
Services
    ↓
Repositories
    ↓
PostgreSQL
```

---

## Layered Architecture

Mandatory structure:

```text
API Layer
↓
Service Layer
↓
Repository Layer
↓
Database Layer
```

---

## Forbidden Architecture

```text
API
↓
Database
```

Direct database access from routes is prohibited.

---

# OpenAPI Integration

FastAPI automatically generates:

```text
Swagger UI
OpenAPI Specification
ReDoc Documentation
```

Endpoints:

```text
/docs

/redoc

/openapi.json
```

This provides:

* Developer Documentation
* API Testing
* SDK Generation
* Future Frontend Integration

---

# Request Validation

Validation shall be handled using:

```text
Pydantic
```

Example:

```python
class CreateTransactionRequest(BaseModel):
    amount: Decimal
    account_id: UUID
```

Benefits:

```text
Input Validation
Type Safety
Automatic Error Responses
```

---

# Dependency Injection

FastAPI Dependency Injection shall be used.

Examples:

```python
Depends(get_current_user)

Depends(get_db)
```

Benefits:

```text
Testability
Loose Coupling
Clean Architecture
```

---

# Authentication Integration

FastAPI shall manage:

```text
JWT Validation
Current User Resolution
Ownership Validation
```

Example:

```python
current_user = Depends(get_current_user)
```

---

# Async Support

FastAPI supports:

```text
Async Endpoints
Async HTTP Calls
Future Background Processing
```

Examples:

```text
Telegram Notifications

AI Requests

Future Email Notifications
```

---

# AI Integration Benefits

The platform will use:

```text
FastAPI
+
Ollama
```

FastAPI works naturally with:

```text
Qwen
Gemma
Llama
OpenAI
Anthropic
```

This simplifies future AI expansion.

---

# Telegram Integration

FastAPI shall expose:

```text
POST /api/v1/telegram/webhook
```

Responsibilities:

```text
Receive Telegram Messages
Process User Feedback
Trigger Learning Engine
```

---

# SMS Ingestion Integration

FastAPI shall expose:

```text
POST /api/v1/ingest/sms
```

Responsibilities:

```text
Receive MacroDroid Payloads
Store Raw Events
Trigger Processing
```

---

# Future Mobile Support

Future mobile applications will communicate through:

```text
FastAPI REST APIs
```

Supported clients:

```text
Android
iOS
Web
Telegram
```

No architecture changes required.

---

# Future SaaS Support

FastAPI supports:

```text
Multiple Instances
Load Balancers
Container Scaling
Cloud Deployments
```

Future architecture:

```text
Load Balancer
       ↓
FastAPI Instances
       ↓
PostgreSQL
```

---

# Security Implications

FastAPI supports:

```text
JWT Authentication
OAuth2
Dependency-Based Authorization
Input Validation
```

Required security controls:

```text
Ownership Validation
Request Validation
Audit Logging
Rate Limiting (Future)
```

---

# Testing Implications

Testing framework:

```text
Pytest
```

FastAPI provides:

```text
TestClient
Dependency Overrides
Mock Injection
```

Benefits:

```text
Unit Testing
Integration Testing
API Testing
```

---

# Developer Productivity Benefits

FastAPI provides:

```text
Auto Documentation
Strong Typing
IDE Autocomplete
Reduced Boilerplate
```

This significantly improves AI-generated code quality.

---

# AI Coding Agent Compatibility

FastAPI is highly compatible with:

```text
Claude Code
Cursor
Cline
Roo Code
OpenClaw
ChatGPT
Codex
```

Reasons:

```text
Clear Patterns
Strong Typing
Modern Architecture
Excellent Documentation
```

---

# Consequences

## Positive Consequences

### Faster Development

Reduced boilerplate.

---

### Better API Documentation

Automatic OpenAPI generation.

---

### Better Validation

Built-in request validation.

---

### Strong Typing

Improves maintainability.

---

### AI-Friendly

Produces more reliable AI-generated code.

---

### SaaS Ready

Supports future scaling.

---

## Negative Consequences

### More Architectural Freedom

Requires discipline.

Framework does not enforce project structure.

---

### Smaller Ecosystem Than Django

Some features require additional implementation.

---

### Team Learning Curve

Developers unfamiliar with FastAPI must learn:

```text
Pydantic
Dependency Injection
Async Programming
```

---

# Rejected Alternatives

## Flask

Rejected because:

```text
More Boilerplate
No Native Validation
No Native OpenAPI
```

---

## Django

Rejected because:

```text
Too Heavy For Current Requirements
Admin Features Not Required
Less API-Centric
```

---

## Spring Boot

Rejected because:

```text
Higher Complexity
Longer Development Time
Not Aligned With Python AI Stack
```

---

## Node.js / Express

Rejected because:

```text
Weaker Type Safety
Less Alignment With AI Components
Additional Ecosystem Complexity
```

---

# Review Criteria

This ADR should be revisited if:

```text
Performance Requirements Change Significantly

Python Becomes Unsuitable

Large Enterprise Constraints Emerge

Alternative Runtime Provides Significant Benefits
```

---

# Related Documents

```text
06-high_level_design.md

08-api_contracts.md

10-security_standards.md

11-deployment_standards.md

12-coding_standards.md

16-authentication_design.md
```

---

# Final Decision

Accepted.

FastAPI shall serve as the primary backend framework for the Personal Finance Tracking Platform.

All APIs, authentication workflows, SMS ingestion endpoints, Telegram integrations, AI services, and future SaaS capabilities shall be implemented using FastAPI.

The combination of:

```text
FastAPI
+
SQLModel
+
PostgreSQL
+
Docker
```

is the approved backend foundation for the platform.
