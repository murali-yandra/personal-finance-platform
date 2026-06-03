# ADR-012: Use Soft Delete for Financial Records

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead
* Data Architect

---

# Context

The Personal Finance Tracking Platform manages financial data including:

```text
Users

Accounts

Transactions

Balances

Transfers

Credit Card Records

Merchant Rules

Categories

Audit Logs

AI Suggestions
```

Financial systems require:

```text
Auditability

Traceability

Historical Accuracy

Recovery Capability

Regulatory Readiness
```

Users may occasionally:

```text
Create Incorrect Transactions

Create Duplicate Transactions

Create Incorrect Accounts

Create Incorrect Categories
```

The platform must determine how records should be removed.

---

# Problem Statement

Traditional applications often use:

```sql
DELETE FROM transactions
WHERE id = :id;
```

This permanently removes data.

Problems:

```text
No Recovery

Broken Audit Trails

Loss Of Financial History

Difficult Debugging

Difficult Reconciliation
```

For financial systems, permanent deletion creates significant risk.

---

# Decision Drivers

## Auditability

Requirements:

```text
Full Historical Traceability

Change Tracking

Recovery Capability
```

---

## Financial Integrity

Requirements:

```text
Preserve Historical Calculations

Preserve Balance History

Preserve Audit Trails
```

---

## User Error Recovery

Requirements:

```text
Undo Mistakes

Restore Records

Investigate Issues
```

---

## Future Compliance

Requirements:

```text
Data Lineage

Historical Reporting

Audit Readiness
```

---

# Alternatives Considered

## Option 1 — Hard Delete

Example:

```sql
DELETE FROM transactions
WHERE id = :id;
```

Advantages:

```text
Simple

Less Storage
```

Disadvantages:

```text
Data Loss

No Recovery

Audit Risks
```

---

## Option 2 — Soft Delete

Example:

```sql
is_deleted = TRUE
deleted_at = NOW()
```

Advantages:

```text
Recoverable

Auditable

Safer
```

Disadvantages:

```text
Additional Query Logic

Slightly More Storage
```

---

# Decision

The platform shall use:

```text
Soft Delete
```

for all financial records.

Records shall never be physically removed during normal operations.

---

# Soft Delete Standard

Every soft-deletable table must contain:

```sql
is_deleted BOOLEAN NOT NULL DEFAULT FALSE

deleted_at TIMESTAMP NULL

deleted_by UUID NULL
```

---

# Delete Workflow

Instead of:

```sql
DELETE FROM transactions
WHERE id = :id;
```

Use:

```sql
UPDATE transactions
SET
    is_deleted = TRUE,
    deleted_at = NOW(),
    deleted_by = :user_id
WHERE id = :id;
```

---

# Tables Using Soft Delete

Mandatory:

```text
accounts

transactions

categories

merchant_patterns

user_feedback

ai_suggestions
```

---

# Tables NOT Using Soft Delete

The following tables are immutable:

```text
audit_log

event_log
```

Reason:

```text
Audit Records Must Never Change
```

---

# Transaction Deletion Rule

Transactions shall never be physically deleted.

When a transaction is deleted:

```text
Transaction Marked Deleted
↓
Balance Recalculated
↓
Audit Log Created
```

---

# Account Deletion Rule

Accounts shall never be physically deleted.

Example:

```text
Salary Account Closed
```

Action:

```text
Account Archived
```

Not:

```text
Account Removed
```

---

# Category Deletion Rule

Categories may be deleted logically.

Example:

```text
Old Category

"Covid Expenses"
```

Result:

```text
is_deleted = TRUE
```

Historical transactions remain intact.

---

# Query Filtering Standard

All business queries must include:

```sql
WHERE is_deleted = FALSE
```

Example:

```sql
SELECT *
FROM transactions
WHERE user_id = :user_id
AND is_deleted = FALSE;
```

---

# Repository Layer Rule

Filtering must occur automatically.

Example:

```python
TransactionRepository
```

shall automatically exclude:

```text
is_deleted = TRUE
```

records.

---

# Restore Workflow

Example:

```text
User Deleted Transaction By Mistake
```

Recovery:

```sql
UPDATE transactions
SET
    is_deleted = FALSE,
    deleted_at = NULL,
    deleted_by = NULL
WHERE id = :id;
```

---

# Audit Requirements

Every soft delete must create:

```text
Audit Log Entry
```

Example:

```text
TRANSACTION_DELETED

ACCOUNT_ARCHIVED

CATEGORY_DELETED
```

---

# Financial Consistency Rule

Deleting a transaction impacts:

```text
Balances

Reports

Savings Calculations

Net Worth
```

Therefore:

```text
Delete
+
Balance Recalculation
+
Audit Log
```

must occur inside a single database transaction.

---

# Protected Financial Records

The following entities are considered financial records:

```text
transactions

accounts

balance_snapshots

transfers
```

These records must never be physically deleted through application workflows.

---

# Reversal Before Deletion Rule

For financial transactions, the preferred approach is:

Transaction
↓
Reversal Transaction
↓
Audit Log

instead of:

Transaction
↓
Soft Delete

Examples:

- Wrong Expense Entry
- Incorrect Transfer
- Duplicate Transaction

Create:

REVERSAL transaction

linked_to_transaction_id

Benefits:

- Preserves Accounting History
- Preserves Balance Trail
- Simplifies Auditing
- Matches Real Banking Systems

Soft delete remains available for administrative correction workflows.

---

# Historical Reporting Rule

Historical reports must continue to work.

Example:

```text
2025 Expense Report
```

must remain reproducible even if:

```text
Transaction Deleted In 2026
```

Soft delete enables this capability.

---

# Soft Delete Metadata

Every deleted record should capture:

```text
deleted_at

deleted_by

delete_reason
```

Recommended additional field:

```sql
delete_reason VARCHAR(500)
```

---

# Administrative Recovery

Future Admin Functions:

```text
Restore Transaction

Restore Account

Restore Category
```

Supported because records remain stored.

---

# Data Retention Rule

Soft-deleted records remain stored indefinitely.

Future archival process may move old records to:

```text
Archive Tables

Cold Storage

Data Warehouse
```

but records must remain recoverable.

---

# AI Learning Implications

Soft-deleted transactions shall not participate in:

```text
Merchant Learning

Category Learning

AI Training
```

unless explicitly restored.

---

# API Behavior

Normal APIs return:

```text
Active Records Only
```

Administrative APIs may support:

```text
include_deleted=true
```

for investigation purposes.

---

# Security Benefits

Advantages:

```text
Reduced Risk Of Accidental Data Loss

Improved Recovery

Improved Auditing
```

---

# Financial Benefits

Advantages:

```text
Preserves Financial History

Supports Reconciliation

Supports Investigations
```

---

# Consequences

## Positive Consequences

### Recoverability

Mistakes can be undone.

---

### Auditability

Full historical record preserved.

---

### Financial Integrity

Historical reports remain accurate.

---

### Better User Experience

Accidental deletions are reversible.

---

## Negative Consequences

### More Storage

Deleted records remain stored.

---

### Query Complexity

Requires filtering.

---

### Maintenance Overhead

Need periodic archival strategy.

---

# Hard Delete Exception Rule

Hard delete is prohibited except for:

```text
Data Retention Policies

Legal Requests

Administrative Maintenance
```

Such operations require:

```text
Administrative Authorization

Audit Logging

Backup Verification
```

---

# Immutable Record Rule

The following tables are immutable:

```text
audit_log

event_log
```

Records may only be:

```text
Inserted

Read
```

Never:

```text
Updated

Deleted
```

---

# Soft Delete First Principle

The platform follows:

```text
Delete Request
↓
Soft Delete
↓
Audit Log
↓
Recovery Possible
```

Never:

```text
Delete Request
↓
Hard Delete
↓
Data Lost
```

---

# Rejected Alternatives

## Hard Delete

Rejected because:

```text
Financial Risk

No Recovery

Poor Auditability
```

---

# Review Criteria

This ADR should be revisited if:

```text
Legal Requirements Change

Data Volumes Become Extremely Large

Archival Requirements Emerge
```

---

# Related Documents

```text
04-database_schema.md

05-data_dictionary.md

18-database_erd.md

ADR-001-use-postgresql-as-system-of-record.md

ADR-011-use-decimal-for-financial-calculations.md
```

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall use soft delete for all financial and business records.

Financial data shall remain recoverable, auditable, and historically traceable. Physical deletion is prohibited during normal application workflows, ensuring long-term financial integrity and preserving the ability to reproduce historical reports, balances, and audit trails.
