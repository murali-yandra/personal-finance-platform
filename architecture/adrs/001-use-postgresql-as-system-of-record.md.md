# ADR-001: Use PostgreSQL as System of Record

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform requires a primary operational database capable of supporting:

* Financial transaction storage
* Account balance tracking
* Audit logging
* User management
* Merchant learning
* AI feedback storage
* Telegram workflow state
* Historical SMS ingestion
* Future SaaS multi-tenancy

The platform processes financial information where:

* Data integrity is critical
* Consistency is mandatory
* Auditability is required
* Financial balances must remain accurate
* Transactions must not be lost

The database must support both:

1. Current MVP

```text
Single User
Android SMS
Telegram Bot
Docker Deployment
```

2. Future Growth

```text
Thousands of Users
Millions of Transactions
Multi-Tenant SaaS
AI Features
Analytics
```

---

# Decision Drivers

The selected database must provide:

## Financial Integrity

Requirements:

```text
ACID Transactions
Referential Integrity
Constraints
Rollback Support
```

---

## Reliability

Requirements:

```text
Backups
Recovery
Replication Support
Mature Ecosystem
```

---

## Scalability

Requirements:

```text
Vertical Scaling
Future Read Replicas
Future Partitioning
```

---

## Developer Productivity

Requirements:

```text
Python Ecosystem
SQLModel Support
Alembic Support
Docker Support
```

---

## Cost

Requirements:

```text
Free For MVP
Low Cost For VPS Deployment
```

---

# Alternatives Considered

## Option 1 — PostgreSQL

Advantages:

```text
ACID Compliant
Open Source
Excellent Python Support
Strong SQL Support
JSON Support
Rich Indexing
Extensible
Mature Ecosystem
```

Disadvantages:

```text
Requires Backup Management
Requires Operations Knowledge
```

---

## Option 2 — MySQL

Advantages:

```text
Widely Used
Good Tooling
Open Source
```

Disadvantages:

```text
Less Rich Feature Set
Inferior JSON Capabilities
Less Flexible For Future Analytics
```

---

## Option 3 — MongoDB

Advantages:

```text
Flexible Schema
Easy JSON Storage
```

Disadvantages:

```text
Not Ideal For Financial Transactions
Weaker Relational Modeling
More Complex Financial Integrity Rules
```

---

## Option 4 — BigQuery

Advantages:

```text
Massive Analytics Scale
Serverless
Excellent Reporting
```

Disadvantages:

```text
Not Designed For OLTP
Not ACID Transactional For Application Workloads
Higher Cost For Frequent Writes
Poor Fit For Real-Time Transaction Processing
```

---

## Option 5 — SQLite

Advantages:

```text
Simple
Zero Setup
```

Disadvantages:

```text
Limited Concurrency
Not Suitable For SaaS Growth
Not Suitable For Large Financial Workloads
```

---

# Decision

The platform will use:

```text
PostgreSQL
```

as the primary System of Record.

All operational data shall be stored in PostgreSQL.

Examples:

```text
Users
Accounts
Transactions
Balance Snapshots
Audit Logs
Merchant Patterns
User Feedback
AI Suggestions
Raw SMS Events
```

PostgreSQL will be the authoritative source of truth.

---

# Architecture Implications

## Current Architecture

```text
Android Phone
      ↓
MacroDroid
      ↓
FastAPI
      ↓
PostgreSQL
      ↓
Telegram
```

---

## Future Analytics Architecture

```text
PostgreSQL
      ↓
ETL Pipeline
      ↓
BigQuery
      ↓
Analytics
Dashboards
ML
```

BigQuery may be added later.

BigQuery will never replace PostgreSQL as the operational database.

---

# Data Ownership

All user-owned records must contain:

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
audit_log
```

PostgreSQL enforces ownership boundaries through:

```sql
WHERE user_id = :current_user_id
```

---

# Financial Integrity Requirements

All financial operations must use database transactions.

Example:

```text
Create Transaction
Update Balance
Create Audit Log
Commit
```

If any step fails:

```text
Rollback Entire Transaction
```

---

# Backup Strategy

MVP:

```text
Daily PostgreSQL Backup
30 Day Retention
```

Future:

```text
Automated Backups
Point-In-Time Recovery
Cross-Region Replication
```

---

# Security Requirements

PostgreSQL must:

```text
Run Inside Docker Network
Not Be Exposed Publicly
Use Dedicated Application User
Use Strong Passwords
```

Application access only through:

```text
FastAPI Backend
```

Direct user access is prohibited.

---

# Migration Strategy

Schema changes must be managed using:

```text
Alembic
```

Manual production schema changes are prohibited.

---

# Consequences

## Positive Consequences

### Strong Consistency

Financial records remain accurate.

---

### Reliable Balance Calculations

Supports transaction-based balance tracking.

---

### Auditability

Supports immutable audit trails.

---

### SaaS Ready

Supports future multi-user growth.

---

### Cost Effective

Free for development.

Low VPS operating cost.

---

### Excellent Ecosystem

Supports:

```text
FastAPI
SQLModel
Alembic
Docker
Python
```

---

## Negative Consequences

### Operational Responsibility

Backups must be managed.

---

### Future Scaling Effort

Large-scale deployments may require:

```text
Read Replicas
Partitioning
Connection Pooling
```

---

### Analytics Requires Additional Pipeline

Future reporting at very large scale may require:

```text
PostgreSQL
→ ETL
→ BigQuery
```

---

# Rejected Alternatives

## BigQuery As Primary Database

Rejected because:

```text
Not Designed For OLTP
Not Ideal For Frequent Writes
Poor Fit For Transactional Financial Workloads
```

---

## MongoDB As Primary Database

Rejected because:

```text
Financial Integrity More Complex
Relational Data Model Required
Balance Calculations Better Suited To SQL
```

---

## SQLite As Primary Database

Rejected because:

```text
Not Suitable For Future SaaS Growth
Limited Concurrency
```

---

# Review Criteria

This ADR should be revisited if:

```text
User Count Exceeds 100,000

Transaction Volume Exceeds 100 Million Records

Multi-Region Deployment Required

Extreme Analytics Requirements Emerge
```

---

# Related Documents

```text
03-domain_model.md

04-database_schema.md

05-data_dictionary.md

06-high_level_design.md

10-security_standards.md

11-deployment_standards.md

18-database_erd.md
```

---

# Final Decision

Accepted.

PostgreSQL shall serve as the authoritative System of Record for all operational and financial data within the Personal Finance Tracking Platform.

BigQuery may be introduced later as an analytical data warehouse but will not replace PostgreSQL for transactional workloads.
