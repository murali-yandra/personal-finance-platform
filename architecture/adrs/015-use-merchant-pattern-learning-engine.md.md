# ADR-015: Use Merchant Pattern Learning Engine

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* AI Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform receives financial transaction data from:

```text
SMS Messages

Future Account Aggregator

Future CSV Imports

Future Bank APIs
```

Many transactions contain merchant identifiers that are difficult to interpret.

Examples:

```text
UPISWIGGY@ICICI

UPIZOMATO@HDFC

KA51AJ7604@CNRB

AMAZONPAY

SMARTQ

PAYTM_MALL
```

The platform must transform these raw merchant identifiers into meaningful business entities.

---

# Problem Statement

Raw transaction messages are inconsistent.

Example:

```text
UPISWIGGY@ICICI
```

Desired result:

```text
Merchant:
Swiggy

Category:
Food

Confidence:
100%
```

---

Example:

```text
UPISWIGGY@HDFC
```

Desired result:

```text
Merchant:
Swiggy

Category:
Food
```

---

Without learning:

```text
Every Transaction
↓
Ask User
```

Result:

```text
Poor User Experience

Notification Fatigue

Low Automation
```

The platform requires a self-improving merchant recognition system.

---

# Decision Drivers

## User Experience

Requirements:

```text
Reduce User Input

Reduce Repetitive Questions

Improve Automation
```

---

## Accuracy

Requirements:

```text
Consistent Categorization

Consistent Merchant Naming

Deterministic Results
```

---

## Scalability

Requirements:

```text
Support Thousands Of Merchants

Support Millions Of Transactions

Improve Over Time
```

---

## Explainability

Requirements:

```text
Auditable Decisions

Deterministic Rules

User Overrides
```

---

# Alternatives Considered

## Option 1 — Ask User Every Time

Advantages:

```text
Always Accurate
```

Disadvantages:

```text
Poor UX

Too Much Manual Work
```

---

## Option 2 — AI Only

Advantages:

```text
Highly Automated
```

Disadvantages:

```text
Expensive

Inconsistent

Not Deterministic
```

---

## Option 3 — Merchant Pattern Learning Engine

Advantages:

```text
Deterministic

Self Improving

Explainable

Low Cost
```

Disadvantages:

```text
Requires Learning Logic
```

---

# Decision

The platform shall implement a:

```text
Merchant Pattern Learning Engine
```

which continuously learns merchant mappings from user feedback.

The learning engine shall be prioritized before AI classification.

---

# Deterministic First Principle

Classification priority:

```text
User Override Rules
↓
Merchant Pattern Engine
↓
Regex Rules
↓
AI Classification
↓
Unknown
```

AI is the final fallback.

---

# Merchant Pattern Concept

Raw Merchant:

```text
UPISWIGGY@ICICI
```

Normalized Pattern:

```text
SWIGGY
```

Result:

```text
Merchant:
Swiggy

Category:
Food
```

---

# Pattern Normalization Rules

Remove:

```text
Bank Suffixes

UPI Prefixes

Special Characters

Case Differences
```

---

Examples:

```text
UPISWIGGY@ICICI
↓
SWIGGY

UPISWIGGY@HDFC
↓
SWIGGY

SWIGGY123
↓
SWIGGY
```

---

# Learning Workflow

## First Transaction

Input:

```text
UPISWIGGY@ICICI
```

Unknown merchant.

System asks user:

```text
Merchant?
Category?
```

User responds:

```text
Swiggy

Food
```

Store pattern.

---

## Second Transaction

Input:

```text
UPISWIGGY@HDFC
```

Pattern match found.

Result:

```text
Merchant:
Swiggy

Category:
Food

Confidence:
100%
```

No user interaction.

---

# Merchant Pattern Table

Table:

```text
merchant_patterns
```

Columns:

```text
id

user_id

pattern

normalized_pattern

merchant_name

category_id

confidence_score

created_at

updated_at

is_active
```

---

# User Scoped Learning

Patterns belong to:

```text
User
```

Not global system.

Example:

```text
User A
↓
SMARTQ
↓
Food
```

User B:

```text
SMARTQ
↓
Office Meals
```

Allowed.

---

# Pattern Matching Strategy

Priority:

## Exact Match

```text
SWIGGY
=
SWIGGY
```

---

## Normalized Match

```text
UPISWIGGY@ICICI
=
SWIGGY
```

---

## Regex Match

Example:

```text
KA\d+.*@CNRB
```

May map to:

```text
BMTC
```

---

## AI Fallback

If no rule exists.

---

# Similar Pattern Learning Rule

The engine shall support pattern families.

Example:

KA51AJ7604@CNRB
KA43HJ2938@CNRB
KA01XY8891@CNRB

User labels first transaction:

Merchant: BMTC
Category: Transport

System may suggest creating:

Pattern Family:
KA*@CNRB

Future matches receive:

Merchant: BMTC
Category: Transport

Confidence: 80%

User confirmation required before promotion to trusted pattern.

Reason:

Allows learning from structural similarities while preventing overly aggressive auto-classification.

---

# Merchant Alias Support

One merchant may have many aliases.

Example:

```text
SWIGGY

UPISWIGGY

SWIGGYINSTAMART

SWIGGYMONEY
```

All map to:

```text
Swiggy
```

---

# Confidence Model

Pattern Match:

```text
100%
```

---

Regex Match:

```text
90%
```

---

AI Suggestion:

```text
50%-90%
```

---

Unknown:

```text
0%
```

---

# Telegram Learning Workflow

Unknown Merchant:

```text
KA51AJ7604@CNRB

Suggested:
Transport

Reply:

MERCHANT BMTC

CATEGORY Transport
```

System learns.

---

# User Feedback Loop

User correction:

```text
Merchant:
BMTC

Category:
Transport
```

Store:

```text
Pattern

Merchant

Category
```

Future transactions auto-classified.

---

# Pattern Promotion Rule

New patterns start as:

```text
Tentative
```

After:

```text
3 Successful Matches
```

Promote to:

```text
Trusted Pattern
```

---

# Trusted Pattern Benefits

Trusted patterns:

```text
No User Confirmation

No AI Invocation
```

Required.

---

# Pattern Deactivation

Users may disable:

```text
Merchant Pattern
```

without deleting history.

Store:

```text
is_active = FALSE
```

---

# Conflict Resolution

If multiple patterns match:

Priority:

```text
User Override
↓
Exact Match
↓
Regex Match
↓
AI
```

---

# Audit Requirements

Every learning event must create:

```text
Audit Log
```

Examples:

```text
PATTERN_CREATED

PATTERN_UPDATED

PATTERN_DISABLED
```

---

# AI Integration Rule

AI suggestions may create:

```text
Suggested Pattern
```

but AI cannot automatically promote patterns.

Promotion requires:

```text
User Confirmation

or

Rule Threshold
```

---

# SaaS Scalability

Expected future:

```text
Thousands Of Users

Millions Of Transactions

Millions Of Patterns
```

Patterns remain isolated by:

```text
user_id
```

---

# Performance Requirements

Indexes:

```sql
(user_id, normalized_pattern)

(user_id, merchant_name)
```

Required.

---

Target lookup:

```text
< 50ms
```

---

# Reporting Benefits

Improves:

```text
Merchant Reports

Category Reports

Spending Trends

Budget Tracking
```

because merchant names become standardized.

---

# Operational Benefits

Advantages:

```text
Less User Input

Less AI Usage

Lower Cost

Higher Accuracy
```

---

# Financial Benefits

Advantages:

```text
Consistent Categorization

Better Spending Analysis

Cleaner Reporting
```

---

# Consequences

## Positive Consequences

### Self Improving System

Improves over time.

---

### Reduced AI Costs

Many transactions become deterministic.

---

### Better User Experience

Fewer notifications.

---

### Explainable Results

Rules can be inspected.

---

## Negative Consequences

### Additional Storage

Patterns must be stored.

---

### Rule Maintenance

Incorrect rules must be corrected.

---

# Merchant Canonicalization Rule

Every transaction must contain:

```text
raw_merchant

normalized_merchant

canonical_merchant
```

Example:

```text
Raw:
UPISWIGGY@ICICI

Normalized:
SWIGGY

Canonical:
Swiggy
```

This separation is mandatory.

---

# Learning Engine First Principle

The platform follows:

```text
User Knowledge
↓
Merchant Patterns
↓
Rules
↓
AI
↓
Unknown
```

Never:

```text
AI
↓
Everything Else
```

---

# Future Global Learning

Future SaaS capability:

```text
Global Pattern Library
```

Example:

```text
Most Users
↓
SWIGGY
↓
Food
```

Used only as a suggestion source.

User-specific patterns always win.

---

# Rejected Alternatives

## AI Only Classification

Rejected because:

```text
Expensive

Non Deterministic

Hard To Audit
```

---

## Manual Classification Only

Rejected because:

```text
Poor User Experience

Poor Scalability
```

---

# Review Criteria

This ADR should be revisited if:

```text
Pattern Volume Exceeds Tens Of Millions

Advanced ML Classification Is Introduced

Global Merchant Catalog Becomes Required
```

---

# Related Documents

```text
03-domain_model.md

04-database_schema.md

05-data_dictionary.md

13-ai_integration_standards.md

ADR-006-use-ollama-for-local-ai-processing.md
```

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall implement a Merchant Pattern Learning Engine that learns from user feedback and deterministic rules before invoking AI.

Merchant classification shall follow a deterministic-first approach, ensuring high accuracy, low operational cost, explainability, and continuous improvement while minimizing user effort.
