# ADR-008: Use PostgreSQL Before BigQuery

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform requires persistent storage for:

* Users
* Accounts
* Transactions
* Balances
* Audit Logs
* Merchant Rules
* Categories
* User Feedback
* AI Suggestions
* Raw SMS Events

During architecture discussions, two primary storage options were considered:

```text
PostgreSQL

BigQuery
```

The platform must support:

```text
Transactional Processing

Financial Integrity

Balance Tracking

Auditability

Real-Time Operations

Future Analytics
```

The architecture must support current MVP requirements while preserving future analytical capabilities.

---

# Problem Statement

The platform has two fundamentally different workloads:

## Operational Workloads (OLTP)

Examples:

```text
Create Transaction

Update Balance

Login User

Store SMS

Generate Audit Log

Update Category
```

Characteristics:

```text
High Write Frequency

Low Latency

Transactional

Strong Consistency
```

---

## Analytical Workloads (OLAP)

Examples:

```text
Monthly Reports

Yearly Spending Analysis

Category Trends

Income Growth

AI Insights

Dashboards
```

Characteristics:

```text
Large Data Scans

Aggregations

Reporting

Historical Analysis
```

The architecture must determine which platform should be used first.

---

# Decision Drivers

The selected primary datastore must support:

## Financial Integrity

Requirements:

```text
ACID Transactions

Rollback Support

Strong Consistency

Referential Integrity
```

---

## Real-Time Processing

Requirements:

```text
Sub-Second Writes

Frequent Updates

Concurrent Operations
```

---

## Cost

Requirements:

```text
Low MVP Cost

Predictable Cost Model
```

---

## Future Scalability

Requirements:

```text
Support Millions Of Transactions

Support Analytics

Support Data Warehousing
```

---

## Developer Productivity

Requirements:

```text
FastAPI Integration

SQLModel Support

Alembic Support

Docker Support
```

---

# Alternatives Considered

## Option 1 — PostgreSQL Only

Advantages:

```text
ACID Transactions

Strong Consistency

Simple Architecture

Low Cost

Excellent Tooling
```

Disadvantages:

```text
Large Analytics Can Become Expensive

Reporting Workloads May Impact OLTP
```

---

## Option 2 — BigQuery Only

Advantages:

```text
Excellent Analytics

Serverless

Massive Scale
```

Disadvantages:

```text
Not Designed For OLTP

Expensive Frequent Writes

Poor Transactional Support

Not Suitable For Balance Tracking
```

---

## Option 3 — PostgreSQL + BigQuery

Advantages:

```text
Best Of Both Worlds
```

Disadvantages:

```text
Additional Complexity

Additional Infrastructure

Requires ETL Pipelines
```

---

# Decision

The platform shall use:

```text
PostgreSQL
```

as the primary operational datastore.

BigQuery shall not be introduced during MVP development.

BigQuery is deferred until a proven analytical need exists.

---

# Architecture Evolution

## Phase 1 — MVP

```text
FastAPI
     ↓
PostgreSQL
```

All workloads run on PostgreSQL.

---

## Phase 2 — Growth

```text
FastAPI
     ↓
PostgreSQL
     ↓
Analytics Views
```

Reporting remains in PostgreSQL.

---

## Phase 3 — Analytics Expansion

```text
FastAPI
     ↓
PostgreSQL
     ↓
ETL Pipeline
     ↓
BigQuery
```

BigQuery becomes an analytics warehouse.

---

# System Of Record Principle

PostgreSQL shall remain:

```text
Source Of Truth
```

for:

```text
Users

Accounts

Transactions

Balances

Audit Logs
```

BigQuery shall never become:

```text
Source Of Truth
```

for operational data.

---

# Data Flow

## Current

```text
SMS
 ↓
FastAPI
 ↓
PostgreSQL
```

---

## Future

```text
SMS
 ↓
FastAPI
 ↓
PostgreSQL
 ↓
ETL
 ↓
BigQuery
```

---

# Why BigQuery Was Not Selected First

## Financial Consistency

Financial operations require:

```text
Atomic Transactions
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

This workflow is natural in PostgreSQL.

BigQuery is not optimized for such workloads.

---

## Update Frequency

The platform performs:

```text
Frequent Inserts

Frequent Updates

Frequent Reads
```

BigQuery performs best with:

```text
Large Analytical Queries
```

not operational transactions.

---

## Cost Model

PostgreSQL:

```text
Infrastructure Cost
```

Predictable.

---

BigQuery:

```text
Storage Cost

Query Cost

Data Scan Cost
```

Usage dependent.

---

For MVP:

```text
PostgreSQL
```

is significantly cheaper.

---

# Reporting Strategy

MVP reports will be generated from PostgreSQL.

Examples:

```text
Monthly Spending

Income vs Expense

Category Breakdown

Account Summary
```

These workloads are small enough to run efficiently inside PostgreSQL.

---

# BigQuery Adoption Criteria

BigQuery may be introduced when:

```text
Transactions > 50 Million

Historical Data > 5 Years

Complex Analytics Become Slow

AI Analytics Requires Warehousing
```

---

# ETL Strategy

Future ETL architecture:

```text
PostgreSQL
 ↓
Extract
 ↓
Transform
 ↓
Load
 ↓
BigQuery
```

Recommended tools:

```text
Airflow

Dagster

Cloud Composer

Custom ETL
```

---

# Data Ownership Rules

PostgreSQL owns:

```text
Users

Accounts

Transactions

Balances

Audit Logs
```

---

BigQuery owns:

```text
Aggregations

Analytics

Reporting Models

Historical Snapshots
```

---

# AI Analytics Future

Future AI workloads may query:

```text
BigQuery
```

for:

```text
Spending Trends

Behavior Analysis

Long-Term Forecasting
```

However:

```text
Transaction Creation

Balance Updates

Audit Logging
```

must always use PostgreSQL.

---

# Backup Strategy

PostgreSQL:

```text
Daily Backups

Point-In-Time Recovery

Replication
```

---

BigQuery:

```text
Analytical Copy

Non-Critical
```

since source data exists in PostgreSQL.

---

# Operational Benefits

Advantages:

```text
Simple Architecture

Lower Cost

Faster Development

Reliable Transactions
```

---

# Financial Benefits

Advantages:

```text
Accurate Balances

Strong Consistency

Reliable Audit Trails
```

---

# Consequences

## Positive Consequences

### Correct Database For Financial Workloads

PostgreSQL is purpose-built for OLTP.

---

### Reduced Complexity

No ETL infrastructure initially.

---

### Lower Cost

Ideal for solo development.

---

### Easier Operations

Single database.

---

### Future Analytics Path Preserved

BigQuery can be added later.

---

## Negative Consequences

### Large Analytics Eventually Need Separate Infrastructure

Future ETL required.

---

### Reporting Workloads Share Database

Must monitor performance as data grows.

---

# Data Warehouse Adoption Rule

BigQuery shall only be introduced when:

```text
A measurable business or technical need exists.
```

Examples:

```text
Slow Reporting

Large Historical Analysis

Data Science Requirements

ML Feature Engineering
```

BigQuery shall not be introduced:

```text
Because It Is Trendy

Because It Is Cloud Native

Because Future Scale Is Assumed
```

---

# Eventual Analytics Architecture

When BigQuery is introduced:

PostgreSQL
↓
CDC / ETL
↓
BigQuery
↓
Dashboards
AI Analytics
Data Science

BigQuery must be fed from PostgreSQL.

Applications must never write directly to BigQuery.

Reason:

Prevents data divergence.

Maintains a single source of truth.

Simplifies governance and auditing.

---

# Architecture Governance Rule

The following modules must always use PostgreSQL:

```text
accounts

transactions

balances

audit

authentication
```

No exceptions.

---

# Rejected Alternatives

## BigQuery As Primary Database

Rejected because:

```text
Poor Fit For OLTP

Weak Transaction Model

Higher Operational Cost
```

---

## Dual Database MVP

Rejected because:

```text
Premature Complexity

Unnecessary Infrastructure
```

---

# Review Criteria

This ADR should be revisited if:

```text
Transaction Count > 50 Million

Reporting Queries Become Slow

Analytics Team Is Created

Data Science Workloads Increase
```

---

# Related Documents

```text
ADR-001-use-postgresql-as-system-of-record.md

06-high_level_design.md

11-deployment_standards.md

14-sprint_roadmap.md
```

---

# PostgreSQL First Principle

The platform follows:

```text
PostgreSQL First
Analytics Later
```

Decision order:

```text
PostgreSQL
↓
Optimize PostgreSQL
↓
Archive Data
↓
Add ETL
↓
Add BigQuery
```

Never:

```text
BigQuery First
```

for transactional financial systems.

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall use PostgreSQL as its primary operational database and system of record.

BigQuery is approved only as a future analytical data warehouse and shall be introduced only when justified by measurable reporting, analytics, or machine learning requirements.

Until that point, PostgreSQL remains the sole database platform for all transactional and operational workloads.
