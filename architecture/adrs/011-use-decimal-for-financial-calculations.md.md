# ADR-011: Use Decimal for Financial Calculations

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead
* Data Architect

---

# Context

The Personal Finance Tracking Platform processes monetary values for:

```text id="k3r8hd"
Account Balances

Income

Expenses

Transfers

Credit Card Transactions

Refunds

Fees

Interest

Investments
```

Financial systems require exact arithmetic.

The platform must ensure:

```text id="x8j2lm"
Accuracy

Consistency

Auditability

Reproducibility
```

for all monetary calculations.

---

# Problem Statement

Most programming languages provide:

```text id="f1t5wp"
float

double
```

for numeric calculations.

However, floating-point numbers cannot precisely represent many decimal values.

Example:

```python id="a9z5ht"
0.1 + 0.2
```

Result:

```text id="d4w7qv"
0.30000000000000004
```

This behavior is unacceptable for financial systems.

The platform must choose a numeric representation that guarantees exact monetary calculations.

---

# Decision Drivers

## Financial Accuracy

Requirements:

```text id="m5c7kn"
No Rounding Errors

Exact Arithmetic

Predictable Results
```

---

## Auditability

Requirements:

```text id="j4p9tw"
Reproducible Calculations

Consistent Reports

Balance Integrity
```

---

## Regulatory Readiness

Requirements:

```text id="u7f3lb"
Traceable Calculations

Deterministic Results
```

---

## Database Compatibility

Requirements:

```text id="h2q8yv"
PostgreSQL Support

BigQuery Compatibility

ETL Compatibility
```

---

# Alternatives Considered

## Option 1 — Float

Example:

```python id="h6r4ns"
float
```

Advantages:

```text id="s5m8tx"
Fast

Simple
```

Disadvantages:

```text id="p9r3wk"
Precision Errors

Rounding Problems

Financial Risk
```

---

## Option 2 — Double

Advantages:

```text id="g3v7qm"
Higher Precision Than Float
```

Disadvantages:

```text id="v8y2kj"
Still Floating Point

Still Not Exact
```

---

## Option 3 — Integer Cents

Example:

```text id="n5z1gr"
₹10.50
↓
1050
```

Advantages:

```text id="x6c2bh"
Exact Arithmetic
```

Disadvantages:

```text id="a1w8tx"
Poor Readability

Currency Handling Complexity

Extra Conversion Logic
```

---

## Option 4 — Decimal

Advantages:

```text id="e4h9kn"
Exact Arithmetic

Human Readable

Financial Industry Standard

Database Friendly
```

Disadvantages:

```text id="z8q6dm"
Slightly Slower Than Float
```

---

# Decision

The platform shall use:

```text id="n4p8vz"
Decimal
```

for all monetary calculations.

Floating-point arithmetic is prohibited for financial data.

---

# Application Layer Standard

Python monetary values must use:

```python id="p7m3lb"
Decimal
```

from:

```python id="t5r2ck"
decimal
```

module.

Example:

```python id="h3x8wm"
from decimal import Decimal

amount = Decimal("120.50")
```

---

Forbidden:

```python id="x7q9mr"
amount = 120.50
```

---

# Database Standard

PostgreSQL monetary columns must use:

```sql id="m2r5vk"
NUMERIC(18,2)
```

---

Example:

```sql id="u8k4ph"
amount NUMERIC(18,2) NOT NULL
```

---

# Approved Precision

Standard:

```text id="y1v3zc"
NUMERIC(18,2)
```

Meaning:

```text id="v7h8pw"
16 Digits Before Decimal

2 Digits After Decimal
```

Supports:

```text id="e5g2wa"
Very Large Financial Values
```

---

# Tables Requiring Decimal

Mandatory fields:

```text id="g9q4kd"
transactions.amount

accounts.current_balance

accounts.opening_balance

balance_snapshots.balance

credit_card_outstanding

refund_amount

salary_amount
```

---

# Financial Calculation Examples

## Addition

Correct:

```python id="j2r9bw"
Decimal("100.25")
+
Decimal("20.75")

=
Decimal("121.00")
```

---

## Subtraction

Correct:

```python id="r4h7pz"
Decimal("1000.00")
-
Decimal("125.50")

=
Decimal("874.50")
```

---

# Balance Calculation Standard

Balance updates:

```text id="k7v1wm"
Previous Balance
+
Credits
-
Debits
```

must always use Decimal.

---

Example:

```python id="c5r8yt"
new_balance = (
    old_balance
    + credit_amount
    - debit_amount
)
```

---

# Money Calculation Centralization Rule

All financial calculations must occur through:

financial_calculator.py

Examples:

- Balance Updates
- Savings Calculations
- Net Worth Calculations
- Budget Calculations
- Credit Card Outstanding Calculations

Developers must not implement ad-hoc money calculations throughout the codebase.

Reason:

- Consistent Rounding
- Consistent Precision
- Easier Auditing
- Easier Testing

All monetary math should have one authoritative implementation.

---

# Rounding Standard

The platform shall use:

```text id="x1m5bh"
ROUND_HALF_UP
```

for financial rounding.

Example:

```python id="f8z4nh"
Decimal("10.125")
→
10.13
```

---

Reason:

```text id="u2r7cf"
Matches Common Financial Expectations
```

---

# Currency Standard

Current supported currency:

```text id="q4p8mt"
INR
```

---

Future currencies:

```text id="z6v2wn"
USD

EUR

GBP

AED
```

All must use Decimal.

---

# Reporting Standard

Reports must calculate:

```text id="a7r4hd"
Income

Expenses

Savings

Net Cash Flow
```

using Decimal.

---

Never:

```text id="w2h8qb"
float
```

aggregation.

---

# ETL Standard

Data movement:

```text id="r5v3kp"
PostgreSQL
↓
ETL
↓
BigQuery
```

must preserve precision.

---

BigQuery type:

```text id="j8p6wx"
NUMERIC
```

---

Never:

```text id="y4m9zb"
FLOAT64
```

for monetary fields.

---

# API Standards

Amounts must be transmitted as:

```json id="e1q4mb"
{
  "amount": "120.50"
}
```

---

Preferred:

```text id="x8t5kr"
String Representation
```

to avoid precision loss.

---

Forbidden:

```json id="m7r3cv"
{
  "amount": 120.50
}
```

---

# Auditability Benefits

Using Decimal ensures:

```text id="q9v5nk"
Reproducible Calculations

Consistent Reports

Reliable Reconciliation
```

---

# Credit Card Benefits

Credit card calculations:

```text id="d4y2wc"
Outstanding Balance

Available Limit

Payments
```

remain exact.

---

# Investment Benefits

Future:

```text id="g2r8fm"
Mutual Funds

Stocks

Interest Calculations
```

require Decimal precision.

---

# AI Integration Rule

AI may suggest:

```text id="z5k1wh"
Categories

Descriptions

Merchants
```

AI must never calculate:

```text id="u7m4vx"
Balances

Financial Totals

Interest
```

without validation by deterministic Decimal-based logic.

---

# Financial Integrity Rule

All calculations affecting:

```text id="p3r9wh"
Transactions

Balances

Reports

Budgets
```

must be deterministic.

---

# Operational Benefits

Advantages:

```text id="j6v1kd"
Exact Arithmetic

Reliable Reports

Safer Financial Processing
```

---

# Financial Benefits

Advantages:

```text id="k2m5yr"
No Precision Drift

Correct Balances

Accurate Reconciliation
```

---

# Consequences

## Positive Consequences

### Financial Accuracy

Exact calculations.

---

### Regulatory Readiness

Audit-friendly calculations.

---

### Consistent Reports

Same result every time.

---

### Future Investment Support

Supports more advanced financial products.

---

## Negative Consequences

### Slightly Slower Arithmetic

Compared to float.

---

### Additional Developer Discipline

Requires proper Decimal handling.

---

# Forbidden Practices

The following are prohibited:

```python id="h8p2tw"
float

double

FLOAT

REAL
```

for monetary values.

---

Prohibited:

```python id="x4v6kd"
float(transaction.amount)
```

---

Prohibited:

```sql id="q7n5rb"
FLOAT

REAL

DOUBLE PRECISION
```

for financial columns.

---

# Decimal First Principle

All financial processing follows:

```text id="z3m8vk"
Input
↓
Decimal
↓
Business Logic
↓
Decimal
↓
Storage
```

Never:

```text id="t9q4ys"
Input
↓
Float
↓
Business Logic
↓
Storage
```

---

# Rejected Alternatives

## Float

Rejected because:

```text id="v5k1ph"
Precision Errors

Unacceptable For Finance
```

---

## Double

Rejected because:

```text id="n2r8mc"
Still Floating Point
```

---

## Integer Cents

Rejected because:

```text id="e7h3wk"
Adds Complexity

Limited Business Benefit
```

for current requirements.

---

# Review Criteria

This ADR should be revisited if:

```text id="j1r6mp"
Sub-Cent Precision Required

High Frequency Trading Features Added

Cryptocurrency Support Added
```

---

# Related Documents

```text id="r8w4tp"
04-database_schema.md

05-data_dictionary.md

10-security_standards.md

ADR-001-use-postgresql-as-system-of-record.md
```

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall use Decimal in application code and NUMERIC(18,2) in PostgreSQL for all financial values.

Floating-point arithmetic is explicitly prohibited for financial calculations to guarantee accuracy, consistency, auditability, and long-term financial integrity.
