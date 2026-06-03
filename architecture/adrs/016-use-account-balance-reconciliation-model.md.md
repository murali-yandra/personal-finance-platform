# ADR-016: Use Account Balance Reconciliation Model

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Financial Domain Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform tracks balances across:

```text
Bank Accounts

Savings Accounts

Salary Accounts

Credit Cards

Cash Wallets

Future Investment Accounts

Future Loan Accounts
```

The primary transaction source is:

```text
SMS Messages
```

However SMS-based transaction tracking is inherently incomplete.

Examples:

```text
Missed SMS

Deleted SMS

Bank Message Delays

Historical Imports

Account Opening Balances

Manual Cash Adjustments

Offline Transactions
```

Therefore:

```text
Transaction Ledger
≠
Actual Bank Balance
```

in all situations.

The platform requires a mechanism to ensure balances remain trustworthy.

---

# Problem Statement

Example:

Bank Account

```text
Opening Balance:
₹10,000
```

Transactions captured:

```text
Expense:
₹1,000

Expense:
₹500
```

Calculated balance:

```text
₹8,500
```

Actual bank balance:

```text
₹8,000
```

Difference:

```text
₹500
```

Possible reasons:

```text
Missed Transaction

Missed SMS

Manual Bank Adjustment

Interest Credit

Failed Import
```

Without reconciliation:

```text
Balances Become Less Trustworthy Over Time
```

---

# Decision Drivers

## Financial Accuracy

Requirements:

```text
Accurate Balances

Detect Drift

Detect Missing Transactions
```

---

## User Trust

Requirements:

```text
Explain Differences

Allow Corrections

Show Confidence
```

---

## Auditability

Requirements:

```text
Track Adjustments

Track Corrections

Track Balance History
```

---

## Future Account Aggregator Support

Requirements:

```text
Compare Bank Data

Validate Internal Data
```

---

# Alternatives Considered

## Option 1 — Ledger Only

Balance:

```text
Opening Balance
+
Credits
-
Debits
```

Advantages:

```text
Simple
```

Disadvantages:

```text
Drift Accumulates

Cannot Detect Missing Transactions
```

---

## Option 2 — Reconciliation Model

Balance:

```text
Ledger Balance

+

Reconciliation Process

+

Actual Balance Validation
```

Advantages:

```text
Accurate

Detects Problems

Supports Missing Transactions
```

Disadvantages:

```text
Additional Complexity
```

---

# Decision

The platform shall use:

```text
Account Balance Reconciliation
```

for all account types.

The platform shall distinguish between:

```text
Calculated Balance

Actual Balance
```

---

# Core Balance Concepts

Every account maintains:

```text
Opening Balance

Calculated Balance

Actual Balance

Last Reconciled Balance
```

---

# Balance Definitions

## Opening Balance

Balance at account creation.

Example:

```text
₹25,000
```

Stored permanently.

---

## Calculated Balance

Computed from transactions.

Formula:

```text
Opening Balance
+
Credits
-
Debits
```

---

## Actual Balance

User-reported or externally sourced balance.

Examples:

```text
Bank App

Internet Banking

Account Aggregator

User Input
```

---

## Reconciled Balance

Last verified balance.

Used for:

```text
Trust Indicators

Reporting

Validation
```

---

# Account Table Fields

Recommended:

```text
opening_balance

calculated_balance

actual_balance

last_reconciled_balance

last_reconciled_at

balance_confidence_score
```

---

# Balance Confidence Score

The system shall calculate:

```text
0 - 100
```

Example:

```text
100
=
Recently Reconciled

70
=
Reconciled 30 Days Ago

40
=
Large Balance Drift
```

Purpose:

```text
Show User Trustworthiness Of Balance
```

---

# Reconciliation Workflow

## Step 1

Calculate:

```text
Calculated Balance
```

---

## Step 2

User provides:

```text
Actual Balance
```

Example:

```text
₹52,500
```

---

## Step 3

Compare:

```text
Calculated:
₹52,000

Actual:
₹52,500
```

Difference:

```text
₹500
```

---

## Step 4

Create Reconciliation Record

Store:

```text
difference_amount

reconciled_at
```

---

# Reconciliation Table

Table:

```text
account_reconciliations
```

Columns:

```text
id

account_id

calculated_balance

actual_balance

difference_amount

notes

created_by

created_at
```

---

# Difference Handling

## Small Difference

Example:

```text
₹10
```

Action:

```text
Accept
```

---

## Medium Difference

Example:

```text
₹500
```

Action:

```text
Warn User
```

---

## Large Difference

Example:

```text
₹5,000
```

Action:

```text
Flag Investigation
```

---

# Missing Transaction Workflow

Detected:

```text
Actual Balance

>

Calculated Balance
```

Possible cause:

```text
Missing Credit
```

---

Detected:

```text
Actual Balance

<

Calculated Balance
```

Possible cause:

```text
Missing Debit
```

---

System may suggest:

```text
Add Adjustment Transaction
```

---

# Adjustment Transaction Model

Instead of directly modifying balances:

Create:

```text
Adjustment Transaction
```

Examples:

```text
BALANCE_ADJUSTMENT_CREDIT

BALANCE_ADJUSTMENT_DEBIT
```

Benefits:

```text
Full Audit Trail

Full Accounting History
```

---

# Balance Update Rule

Balances shall never be edited manually.

Forbidden:

```text
UPDATE accounts
SET balance = ...
```

---

Approved:

```text
Transaction
↓
Balance Recalculation
```

or

```text
Adjustment Transaction
↓
Balance Recalculation
```

---

# Historical Import Workflow

User imports:

```text
Last 6 Months SMS
```

Balance still differs.

User enters:

```text
Current Bank Balance
```

System:

```text
Creates Reconciliation Event
```

No history lost.

---

# Account Aggregator Integration

Future:

```text
Account Aggregator
↓
Actual Balance
```

Comparison:

```text
Actual Balance

vs

Calculated Balance
```

Automatic reconciliation possible.

---

# Credit Card Reconciliation

Credit cards track:

```text
Outstanding Balance
```

instead of:

```text
Cash Balance
```

Example:

```text
Calculated Outstanding:
₹15,000

Actual Outstanding:
₹14,500
```

Difference:

```text
₹500
```

Reconciliation required.

---

# Cash Wallet Reconciliation

Cash is difficult to track.

Support:

```text
Manual Reconciliation
```

Example:

```text
Expected Cash:
₹2,000

Actual Cash:
₹1,700
```

Difference:

```text
₹300
```

Adjustment transaction recommended.

---

# Reconciliation Frequency

Recommended:

## Bank Accounts

```text
Monthly
```

---

## Credit Cards

```text
Per Statement Cycle
```

---

## Cash Wallets

```text
Weekly
```

---

# Reporting Rules

Reports must show:

```text
Calculated Balance

Actual Balance

Difference

Confidence Score
```

---

# Audit Requirements

Every reconciliation creates:

```text
RECONCILIATION_CREATED
```

Audit event.

---

Every adjustment creates:

```text
BALANCE_ADJUSTMENT_CREATED
```

Audit event.

---

# Net Worth Rules

Preferred:

```text
Actual Balance
```

when available.

Fallback:

```text
Calculated Balance
```

---

# Financial Integrity Rule

Balances are:

```text
Derived Data
```

not source data.

Source of truth:

```text
Transactions
```

Balances must always be recalculable.

---

# Balance Snapshot Strategy

The platform shall periodically store:

balance_snapshots

Fields:

- account_id
- snapshot_date
- balance
- source
- created_at

Sources:

- CALCULATED
- RECONCILED
- ACCOUNT_AGGREGATOR
- USER_VERIFIED

Benefits:

- Historical balance charts
- Net worth timelines
- Faster reporting
- Easier investigations
- Future AI insights

Snapshots are reporting artifacts only.

They are not the source of truth.

---

# Balance Rebuild Capability

System shall support:

```text
Rebuild Balance
```

Workflow:

```text
Opening Balance
↓
Replay Transactions
↓
Recalculate Balance
```

Result:

```text
New Calculated Balance
```

---

# Operational Benefits

Advantages:

```text
Detect Missing Transactions

Improve Trust

Support Corrections
```

---

# Financial Benefits

Advantages:

```text
Accurate Balances

Accurate Net Worth

Better Reporting
```

---

# Consequences

## Positive Consequences

### Higher Accuracy

Balances remain trustworthy.

---

### Missing Transaction Detection

Problems become visible.

---

### Better User Trust

Confidence scores explain reliability.

---

### Future AA Compatibility

Supports bank reconciliation.

---

## Negative Consequences

### Additional Complexity

More tables and workflows.

---

### User Participation

Occasional reconciliation required.

---

# Ledger First Principle

The platform follows:

```text
Transactions
↓
Balance Calculation
↓
Reconciliation
↓
Actual Balance
```

Never:

```text
Manual Balance Editing
↓
Unknown State
```

---

# Reconciliation Before Adjustment Rule

When drift is detected:

```text
Difference Found
↓
Investigate
↓
Create Adjustment Transaction
↓
Recalculate
```

Never:

```text
Difference Found
↓
Direct Balance Update
```

---

# Future Real-Time Reconciliation

Future integrations:

```text
Account Aggregator

Bank APIs

Open Banking APIs
```

may automatically trigger:

```text
Daily Reconciliation
```

without user intervention.

---

# Rejected Alternatives

## Ledger Only Model

Rejected because:

```text
Cannot Detect Drift

Cannot Detect Missing Transactions
```

---

## Manual Balance Editing

Rejected because:

```text
Breaks Auditability

Breaks Financial Integrity
```

---

# Review Criteria

This ADR should be revisited if:

```text
Double Entry Accounting Introduced

Multi-Currency Support Added

Real-Time Bank Feeds Become Primary
```

---

# Related Documents

```text
03-domain_model.md

04-database_schema.md

05-data_dictionary.md

18-database_erd.md

ADR-011-use-decimal-for-financial-calculations.md

ADR-014-use-credit-card-payments-as-transfers.md
```

---

# Reconciliation First Principle

The platform follows:

```text
Ledger
↓
Calculated Balance
↓
Actual Balance
↓
Reconciliation
↓
Adjustment Transaction
```

This ensures all balance corrections remain auditable, traceable, and financially consistent.

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall implement an Account Balance Reconciliation Model that separates calculated balances from actual balances, detects balance drift, supports adjustment transactions, and maintains complete financial auditability.

Balances are derived values, transactions are the source of truth, and reconciliation is the mechanism that keeps the system aligned with real-world financial accounts.
