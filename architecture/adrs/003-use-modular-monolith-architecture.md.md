# ADR-003: Use Modular Monolith Architecture

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform is being built as:

```text
Single User First
↓
Multi User Ready
↓
SaaS Ready
```

The system will initially support:

* SMS ingestion
* Transaction processing
* Balance tracking
* Merchant normalization
* Category management
* Telegram interactions
* AI-assisted categorization
* Reporting

Although the MVP is intended for a single user, the long-term vision includes:

```text
Thousands of Users
Millions of Transactions
AI Services
Account Aggregator Integration
Mobile Applications
Future Subscription Plans
```

The architecture must support growth while avoiding unnecessary complexity during early development.

---

# Decision Drivers

The architecture must support:

## Rapid MVP Development

Requirements:

```text
Fast Iteration
Simple Deployment
Minimal Operational Overhead
```

---

## Financial Integrity

Requirements:

```text
ACID Transactions
Balance Consistency
Audit Logging
Strong Data Integrity
```

---

## Maintainability

Requirements:

```text
Clear Module Boundaries
Independent Business Domains
AI-Friendly Structure
```

---

## Future Scalability

Requirements:

```text
Support Future Extraction
Support Future SaaS
Support Additional Services
```

---

## Solo Developer Friendly

Requirements:

```text
Low Complexity
Easy Debugging
Low Infrastructure Cost
```

---

# Alternatives Considered

## Option 1 — Modular Monolith

Architecture:

```text
Single Application
Multiple Internal Modules
Single Database
```

Example:

```text
accounts
transactions
categories
merchants
telegram
ingestion
ai
reporting
```

Advantages:

```text
Simple Deployment
Simple Debugging
Shared Transactions
Fast Development
Low Cost
```

Disadvantages:

```text
Larger Codebase Over Time
Requires Discipline To Maintain Boundaries
```

---

## Option 2 — Microservices

Architecture:

```text
Accounts Service

Transactions Service

Telegram Service

AI Service

Reporting Service
```

Advantages:

```text
Independent Scaling
Independent Deployments
Strong Separation
```

Disadvantages:

```text
Distributed Transactions
Higher Complexity
Infrastructure Overhead
Monitoring Complexity
```

---

## Option 3 — Serverless Architecture

Architecture:

```text
Functions
Event Bus
Managed Services
```

Advantages:

```text
Auto Scaling
Minimal Infrastructure
```

Disadvantages:

```text
Cold Starts
Operational Complexity
Vendor Lock-In
```

---

## Option 4 — Layered Monolith Without Modules

Architecture:

```text
Single Application
No Domain Boundaries
```

Advantages:

```text
Simple Initial Development
```

Disadvantages:

```text
Poor Maintainability
High Coupling
Difficult Future Extraction
```

---

# Decision

The platform shall use:

```text
Modular Monolith Architecture
```

for MVP and early SaaS phases.

The application will be deployed as:

```text
One Backend Service
One PostgreSQL Database
```

with clear internal module boundaries.

---

# Architecture Overview

```text
+--------------------------------+
|         FastAPI App            |
+--------------------------------+
| Accounts Module                |
| Transactions Module            |
| Categories Module              |
| Merchants Module               |
| Reporting Module               |
| Telegram Module                |
| AI Module                      |
| Ingestion Module               |
| Audit Module                   |
| Authentication Module          |
+--------------------------------+
              |
              v
+--------------------------------+
|          PostgreSQL            |
+--------------------------------+
```

---

# Module Design

Each module owns:

```text
Business Rules
Services
Repositories
Schemas
Events
Tests
```

Example:

```text
transactions/

├── api/
├── service.py
├── repository.py
├── schemas.py
├── models.py
├── events.py
└── tests/
```

---

# Internal Communication

Modules communicate through:

```text
Service Calls
Domain Events
```

Preferred pattern:

```text
Transaction Created
↓
Publish Event
↓
Balance Module
↓
Telegram Module
↓
AI Module
```

---

# Database Strategy

The entire platform shall use:

```text
One PostgreSQL Database
```

Benefits:

```text
ACID Transactions
Consistent Balances
Simpler Backups
Simpler Deployment
```

---

# Financial Transaction Benefits

Financial systems benefit from:

```text
Single Transaction Boundary
```

Example:

```text
Create Transaction
↓
Update Balance
↓
Create Audit Log
↓
Commit
```

or

```text
Rollback Entire Operation
```

This is significantly easier in a monolith than in distributed services.

---

# Deployment Implications

Current Deployment:

```text
Docker Compose
↓
FastAPI
↓
PostgreSQL
```

Future Deployment:

```text
Nginx
↓
FastAPI Instances
↓
PostgreSQL
```

No architectural changes required.

---

# Future Service Extraction Strategy

The architecture must support future extraction.

Potential candidates:

```text
AI Module

Reporting Module

Notification Module
```

---

# Protected Core Financial Modules

The following modules are considered core financial domains and shall remain inside the monolith unless a clear business and technical justification is approved through a new ADR.

Protected modules:

accounts
transactions
balances
audit

These modules are responsible for:

- Financial integrity
- Balance consistency
- Auditability
- Regulatory traceability
- Transaction atomicity

Separating these modules into independent services would introduce:

- Distributed transactions
- Eventual consistency risks
- Balance reconciliation complexity
- Increased operational overhead
- Higher failure surface area

Therefore, these modules shall remain within the same transactional boundary.

Future extraction is prohibited unless:

1. A documented business requirement exists.
2. A scalability bottleneck is proven with metrics.
3. An ADR is created and approved.
4. Data consistency guarantees are preserved.

Examples of acceptable future extraction candidates:

- AI Module
- Reporting Module
- Notification Module
- Analytics Module

Examples of prohibited extraction candidates:

- Accounts Module
- Transactions Module
- Balance Engine
- Audit Module

---

## Example Future Evolution

Current:

```text
Monolith
```

Future:

```text
Monolith
   ↓
Extract AI Service
   ↓
Extract Reporting Service
```

without redesigning core modules.

---

# Module Ownership

Each module owns its domain.

---

## Accounts Module

Owns:

```text
Accounts
Balances
Reconciliation
```

---

## Transactions Module

Owns:

```text
Transactions
Transfers
Fingerprints
```

---

## Merchants Module

Owns:

```text
Merchant Resolution
Merchant Patterns
```

---

## Categories Module

Owns:

```text
Categories
Assignments
```

---

## AI Module

Owns:

```text
Suggestions
Learning
Prompt Management
```

---

## Telegram Module

Owns:

```text
Bot Communication
Notifications
User Feedback
```

---

# Dependency Rules

Allowed:

```text
API
↓
Service
↓
Repository
```

---

Forbidden:

```text
API
↓
Database
```

---

Forbidden:

```text
Module
↓
Direct Access To Another Module Database Objects
```

Access must occur through services.

---

# Event-Driven Internal Design

The monolith shall use domain events.

Examples:

```text
RawEventReceived

TransactionCreated

BalanceUpdated

FeedbackReceived
```

Benefits:

```text
Loose Coupling
Future Service Extraction
Better Testing
```

---

# Operational Benefits

Advantages for MVP:

```text
Single Deployment
Single Log Stream
Single Database
Simple Monitoring
```

---

Advantages for Solo Development:

```text
Faster Development
Easier Debugging
Lower Cost
```

---

# AI Coding Agent Benefits

Modular Monolith works exceptionally well with:

```text
Claude Code
Cursor
Cline
Roo Code
OpenClaw
ChatGPT
```

Reason:

```text
Clear Module Boundaries
Predictable Structure
Easy Context Loading
```

---

# Performance Considerations

Expected MVP Load:

```text
1 User
Few Thousand Transactions
```

Expected Growth:

```text
Thousands Of Users
Millions Of Transactions
```

PostgreSQL + FastAPI + Modular Monolith is sufficient.

No microservices required.

---

# Security Implications

Benefits:

```text
Single Authentication Layer
Single Authorization Layer
Single Audit Strategy
```

Reduced attack surface compared to distributed services.

---

# Consequences

## Positive Consequences

### Faster Delivery

MVP delivered sooner.

---

### Lower Cost

Single VPS sufficient.

---

### Easier Debugging

No distributed tracing required.

---

### Better Financial Consistency

Single transaction boundary.

---

### Easier Testing

Integration tests simpler.

---

### AI-Friendly Development

Excellent compatibility with AI coding agents.

---

## Negative Consequences

### Larger Codebase

Requires discipline.

---

### Potential Future Bottlenecks

Some modules may require extraction later.

---

### Shared Deployment

Entire application deployed together.

---

# Rejected Alternatives

## Microservices

Rejected because:

```text
Premature Complexity
Distributed Transactions
Higher Infrastructure Cost
```

Current scale does not justify them.

---

## Serverless

Rejected because:

```text
Vendor Lock-In
Cold Starts
More Complex Financial Processing
```

---

## Non-Modular Monolith

Rejected because:

```text
Poor Maintainability
High Coupling
Difficult Future Evolution
```

---

# Review Criteria

This ADR should be revisited if:

```text
User Count > 100,000

Transactions > 100 Million

AI Workloads Become Heavy

Independent Team Ownership Required
```

---

# Related Documents

```text
06-high_level_design.md

07-sequence_diagrams.md

11-deployment_standards.md

12-coding_standards.md

14-sprint_roadmap.md
```

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall use a Modular Monolith Architecture.

The platform will be deployed as a single FastAPI application with clearly defined domain modules and a shared PostgreSQL database.

Future scalability will be achieved through selective service extraction only when justified by actual business and technical requirements, not anticipated complexity.
