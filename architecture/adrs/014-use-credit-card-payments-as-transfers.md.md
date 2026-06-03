# ADR-014: Use Credit Card Payments as Transfers

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Financial Domain Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform tracks:

```text
Bank Accounts

Savings Accounts

Salary Accounts

Credit Cards

Cash Wallets

Future Investment Accounts
```

Users perform transactions between these accounts.

Examples:

```text
Salary Credited To Bank

UPI Payment From Bank

Credit Card Purchase

Credit Card Bill Payment

Cash Withdrawal

Bank To Bank Transfer
```

The platform must determine how credit card bill payments should be represented.

---

# Problem Statement

Example:

```text
ICICI Credit Card

Outstanding:
₹15,000
```

User pays:

```text
₹15,000

From:
HDFC Salary Account

To:
ICICI Credit Card
```

A naive implementation may classify this as:

```text
Expense
```

However:

```text
The expense already occurred
when the credit card was used.
```

Treating the payment as another expense causes:

```text
Double Counting

Incorrect Reports

Incorrect Savings

Incorrect Budgets
```

The platform must correctly model these financial flows.

---

# Decision Drivers

## Financial Accuracy

Requirements:

```text
No Double Counting

Accurate Cash Flow

Correct Expense Tracking
```

---

## Reporting Accuracy

Requirements:

```text
Correct Monthly Expenses

Correct Net Worth

Correct Savings
```

---

## Accounting Consistency

Requirements:

```text
Match Real Financial Behavior

Match Banking Principles
```

---

## Future Growth

Requirements:

```text
Multi Account Support

Credit Card Support

Investment Account Support
```

---

# Alternatives Considered

## Option 1 — Treat As Expense

Example:

```text
Credit Card Purchase
↓
Expense

Credit Card Payment
↓
Expense
```

Advantages:

```text
Simple
```

Disadvantages:

```text
Double Counts Spending

Incorrect Reports

Incorrect Savings
```

---

## Option 2 — Treat As Transfer

Example:

```text
Bank Account
↓
Credit Card Account
```

Advantages:

```text
Financially Correct

No Double Counting

Accurate Reports
```

Disadvantages:

```text
Requires Transfer Logic
```

---

# Decision

The platform shall classify:

```text
Credit Card Bill Payments
```

as:

```text
TRANSFER
```

not:

```text
EXPENSE
```

---

# Financial Model

## Credit Card Purchase

Example:

```text
Swiggy
₹500
```

Classification:

```text
Expense
```

Category:

```text
Food
```

Account:

```text
ICICI Credit Card
```

Result:

```text
Expense Increased

Credit Card Outstanding Increased
```

---

## Credit Card Bill Payment

Example:

```text
HDFC Salary Account
↓
ICICI Credit Card
₹500
```

Classification:

```text
Transfer
```

Result:

```text
Bank Balance Reduced

Credit Card Outstanding Reduced
```

No expense created.

---

# Transfer Transaction Model

Transfer consists of:

```text
Source Account

Destination Account

Amount
```

Example:

```text
Source:
HDFC Salary

Destination:
ICICI Credit Card

Amount:
₹500
```

---

# Transaction Types

Approved transaction types:

```text
INCOME

EXPENSE

TRANSFER
```

---

# Credit Card Payment Example

Incorrect:

```text
Expense
₹500
```

Correct:

```text
Transfer
₹500
```

---

# Double Counting Example

Incorrect Model:

```text
Swiggy Expense
₹500

Credit Card Payment
₹500

Total Expenses
₹1000
```

Actual Spending:

```text
₹500
```

---

Correct Model:

```text
Swiggy Expense
₹500

Credit Card Payment
Transfer

Total Expenses
₹500
```

---

# Reporting Rules

Reports must exclude:

```text
TRANSFER
```

from:

```text
Expense Totals

Income Totals

Budget Calculations
```

---

# Net Worth Calculation

Transfer impact:

```text
No Net Worth Change
```

Example:

```text
Bank
₹20,000

Credit Card Liability
₹5,000
```

Net Worth:

```text
₹15,000
```

After Payment:

```text
Bank
₹15,000

Credit Card Liability
₹0
```

Net Worth:

```text
₹15,000
```

No change.

---

# Supported Transfer Types

## Bank To Bank

```text
HDFC
↓
ICICI
```

Transfer.

---

## Bank To Credit Card

```text
Salary Account
↓
Credit Card
```

Transfer.

---

## Credit Card To Bank

Future support.

Transfer.

---

## Cash Withdrawal

```text
Bank
↓
Cash Wallet
```

Transfer.

---

## Wallet To Bank

Transfer.

---

# SMS Detection Rules

Examples:

```text
Credit Card Payment Received

Card Payment Successful

Bill Payment Successful
```

Parser may classify as:

```text
TRANSFER
```

instead of:

```text
EXPENSE
```

---

# Internal Transfer Detection Rule

A transaction shall be automatically classified as a transfer when:

1. Source account belongs to the user.
2. Destination account belongs to the same user.
3. Money ownership does not change.

Examples:

HDFC Salary
↓
ICICI Savings

HDFC Salary
↓
ICICI Credit Card

ICICI Savings
↓
Cash Wallet

This rule has higher priority than:

- Merchant Rules
- Category Rules
- AI Suggestions

Reason:

Ownership-based transfer detection is deterministic and should never rely on AI.

---

# Transfer Identification Logic

Priority:

```text
Explicit Rules
↓
Merchant Rules
↓
AI Suggestions
↓
User Confirmation
```

---

# Account Ownership Requirement

Transfers require:

```text
Source Account

Destination Account
```

owned by the same user.

---

# Unknown Destination Handling

Example:

```text
Payment To Card Ending 3456
```

Card exists.

Result:

```text
Transfer
```

---

Card missing.

Result:

```text
Pending Classification
```

---

# Database Model

Recommended fields:

```text
transaction_type

source_account_id

destination_account_id

linked_transaction_id
```

---

# Balance Update Rules

Transfer:

```text
Source Account
↓
Debit

Destination Account
↓
Credit
```

within one database transaction.

---

# Financial Consistency Rule

Transfer processing must:

```text
Update Source Account
↓
Update Destination Account
↓
Create Audit Log
↓
Commit
```

Atomically.

---

# Reporting Benefits

Advantages:

```text
Correct Expenses

Correct Savings

Correct Cash Flow

Correct Net Worth
```

---

# Credit Card Outstanding Rules

Purchase:

```text
Outstanding + Amount
```

---

Payment:

```text
Outstanding - Amount
```

---

# AI Classification Rule

AI may suggest:

```text
TRANSFER
```

However:

```text
Account Ownership Validation
```

must verify the transfer before creation.

---

# User Override Support

Users may change:

```text
Expense
↓
Transfer
```

or

```text
Transfer
↓
Expense
```

if classification is incorrect.

Audit logging required.

---

# Operational Benefits

Advantages:

```text
Cleaner Financial Model

Simpler Reporting

Accurate Analytics
```

---

# Financial Benefits

Advantages:

```text
No Double Counting

Accurate Net Worth

Accurate Budgeting
```

---

# Consequences

## Positive Consequences

### Correct Accounting

Matches real-world financial systems.

---

### Accurate Reports

Expenses are not inflated.

---

### Better Insights

Spending reflects actual consumption.

---

### Better Future Expansion

Supports multiple account types.

---

## Negative Consequences

### More Complex Modeling

Requires transfer logic.

---

### Account Discovery Needed

Must identify destination accounts.

---

# Transfer First Principle

Money moving between owned accounts is:

```text
TRANSFER
```

not:

```text
INCOME
```

and not:

```text
EXPENSE
```

Examples:

```text
Bank → Bank

Bank → Credit Card

Bank → Cash

Cash → Bank

Wallet → Bank
```

All are transfers.

---

# Credit Card Domain Rule

Credit card spending creates:

```text
Expense
+
Liability
```

Credit card payment creates:

```text
Transfer
-
Liability
```

This mirrors real-world accounting behavior.

---

# Rejected Alternatives

## Credit Card Payment As Expense

Rejected because:

```text
Double Counts Spending

Incorrect Savings

Incorrect Reports
```

---

# Review Criteria

This ADR should be revisited if:

```text
Investment Accounts Added

Loan Accounts Added

Advanced Accounting Features Added
```

---

# Related Documents

```text
03-domain_model.md

04-database_schema.md

05-data_dictionary.md

18-database_erd.md

ADR-011-use-decimal-for-financial-calculations.md

ADR-012-use-soft-delete-for-financial-records.md
```

---

# Future Liability Account Rule

The following account types shall behave similarly:

```text
Credit Cards

Personal Loans

Home Loans

Vehicle Loans

Lines Of Credit
```

Payments to these accounts are generally:

```text
TRANSFER
```

and liability reduction, not expenses.

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall classify credit card bill payments as TRANSFER transactions rather than EXPENSE transactions.

This prevents double counting, preserves accurate financial reporting, maintains correct net worth calculations, and aligns the platform with real-world accounting and banking principles.
