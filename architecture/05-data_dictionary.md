# 05-data_dictionary.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Data Dictionary

Database: PostgreSQL

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines every table, column, datatype, business meaning, ownership rule, validation rule, and example value used by the Personal Finance Tracking Platform.

This document is the authoritative source for:

* SQLModel Models
* Alembic Migrations
* API DTOs
* Validation Rules
* Reporting Logic
* AI Context

---

# 2. Naming Standards

## Table Naming

All tables must use:

```text
snake_case
plural nouns
```

Example:

```text
users
accounts
transactions
```

---

## Column Naming

All columns must use:

```text
snake_case
```

Example:

```text
created_at
updated_at
user_id
```

---

## ID Fields

All primary keys:

```text
id UUID
```

All foreign keys:

```text
<entity>_id UUID
```

Examples:

```text
user_id
account_id
merchant_id
```

---

# 3. USERS

Purpose:

Stores platform users.

---

## id

Type:

```text
UUID
```

Required:

```text
Yes
```

Description:

Unique user identifier.

Example:

```text
550e8400-e29b-41d4-a716-446655440000
```

---

## email

Type:

```text
VARCHAR(255)
```

Required:

```text
Yes
```

Description:

Login email.

Example:

```text
murali@example.com
```

Unique:

```text
Yes
```

---

## password_hash

Type:

```text
TEXT
```

Required:

```text
Yes
```

Description:

Argon2 password hash.

Never store passwords.

---

## display_name

Type:

```text
VARCHAR(255)
```

Required:

```text
Yes
```

Example:

```text
Murali Yandra
```

---

## telegram_chat_id

Type:

```text
VARCHAR(100)
```

Required:

```text
No
```

Description:

Telegram Bot identifier.

---

## timezone

Type:

```text
VARCHAR(100)
```

Default:

```text
Asia/Kolkata
```

---

## default_currency

Type:

```text
VARCHAR(3)
```

Default:

```text
INR
```

---

## is_active

Type:

```text
BOOLEAN
```

Default:

```text
TRUE
```

---

## created_at

Type:

```text
TIMESTAMP
```

Description:

Creation timestamp.

---

## updated_at

Type:

```text
TIMESTAMP
```

Description:

Last modification timestamp.

---

# 4. USER_SETTINGS

Purpose:

Stores user preferences.

---

## id

UUID

Primary Key

---

## user_id

UUID

Foreign Key:

```text
users.id
```

Unique:

```text
Yes
```

One settings record per user.

---

## notification_mode

Type:

```text
VARCHAR(50)
```

Allowed Values:

```text
ALWAYS
LOW_CONFIDENCE_ONLY
DAILY_SUMMARY
WEEKLY_SUMMARY
DISABLED
```

---

## ai_suggestions_enabled

Type:

```text
BOOLEAN
```

Default:

```text
FALSE
```

---

## historical_import_mode

Type:

```text
VARCHAR(50)
```

Example:

```text
FULL
LAST_6_MONTHS
LAST_12_MONTHS
```

---

## preferred_language

Type:

```text
VARCHAR(20)
```

Default:

```text
en
```

---

# 5. ACCOUNTS

Purpose:

Stores all financial accounts.

---

## id

UUID

Primary Key

---

## user_id

UUID

Owner of account.

---

## account_name

Type:

```text
VARCHAR(255)
```

Examples:

```text
Salary Account
Emergency Fund
ICICI Credit Card
```

---

## account_type

Type:

```text
VARCHAR(50)
```

Allowed Values:

```text
BANK
CREDIT_CARD
CASH
INVESTMENT
LOAN
```

---

## bank_name

Type:

```text
VARCHAR(100)
```

Examples:

```text
ICICI
HDFC
SBI
CANARA
```

---

## last_four_digits

Type:

```text
VARCHAR(10)
```

Examples:

```text
0452
1234
```

---

## currency

Type:

```text
VARCHAR(3)
```

Examples:

```text
INR
USD
EUR
```

---

## opening_balance

Type:

```text
NUMERIC(18,2)
```

Purpose:

Initial balance.

---

## estimated_balance

Type:

```text
NUMERIC(18,2)
```

Purpose:

Current calculated balance.

---

## status

Type:

```text
VARCHAR(50)
```

Allowed Values:

```text
PENDING
ACTIVE
ARCHIVED
DISABLED
```

---

# 6. RAW_EVENTS

Purpose:

Store all incoming messages.

Never deleted.

---

## id

UUID

Primary Key

---

## user_id

UUID

Owner of event.

---

## source_type

Allowed Values:

```text
SMS
EMAIL
CSV
AA
API
TELEGRAM
```

---

## sender

Examples:

```text
VK-HDFCBK

AD-ICICIB
```

---

## message_text

Type:

```text
TEXT
```

Stores original message.

---

## received_at

Type:

```text
TIMESTAMP
```

Time event entered system.

---

## message_hash

Type:

```text
VARCHAR(255)
```

Purpose:

Duplicate detection.

---

## processing_status

Allowed Values:

```text
RECEIVED
PARSED
PROCESSED
FAILED
DUPLICATE
IGNORED
UNKNOWN_FORMAT
NEEDS_REVIEW
```

---

## processing_error

Type:

```text
TEXT
```

Stores parsing errors.

---

## correlation_id

UUID

Links processing workflow.

---

## request_id

UUID

Request trace identifier.

---

# 7. CATEGORIES

Purpose:

Transaction classification.

---

## id

UUID

---

## user_id

NULL

System category.

NOT NULL

User category.

---

## name

Examples:

```text
Food
Transport
Shopping
Salary
```

---

## parent_category_id

Supports hierarchy.

Example:

```text
Food
  ↓
Dining Out
```

---

## is_system

BOOLEAN

True:

System category.

False:

User category.

---

# 8. MERCHANTS

Purpose:

Normalized merchant catalog.

---

## merchant_name

Examples:

```text
Swiggy
Amazon
BMTC
SmartQ
```

---

## merchant_group

Examples:

```text
Food Delivery
E-Commerce
Public Transport
```

---

## default_category_id

Default categorization.

---

## is_global

Boolean.

Shared merchant.

---

# 9. MERCHANT_PATTERNS

Purpose:

Map raw merchant strings.

---

## pattern

Examples:

```text
upiswiggy@%

swiggyupi%

KA51AJ%
```

---

## pattern_type

Allowed Values:

```text
EXACT
LIKE
REGEX
AI_SUGGESTED
```

---

## confidence

Type:

```text
NUMERIC(5,2)
```

Examples:

```text
1.00
0.95
0.80
```

---

## created_by

Examples:

```text
SYSTEM
USER
AI
```

---

# 10. TRANSACTIONS

Purpose:

Core financial ledger.

Most important table.

---

## id

UUID

Primary Key.

---

## user_id

Owner.

---

## account_id

Account impacted.

---

## raw_event_id

Origin event.

Required for traceability.

---

## merchant_id

Resolved merchant.

Nullable.

---

## category_id

Resolved category.

Nullable.

---

## amount

Type:

```text
NUMERIC(18,2)
```

Examples:

```text
70.00
1250.50
```

Constraint:

Must be >= 0

---

## currency

Examples:

```text
INR
USD
EUR
```

---

## exchange_rate

Future use.

---

## base_currency

Future use.

---

## base_currency_amount

Future use.

---

## direction

Allowed Values:

```text
DEBIT
CREDIT
```

---

## business_type

Allowed Values:

```text
EXPENSE
INCOME
TRANSFER
REFUND
INVESTMENT
LOAN
EMI
FEE
INTEREST
CASHBACK
UNKNOWN
```

---

## merchant_raw

Raw merchant string.

Example:

```text
upiswiggy@icici
```

---

## description

User-entered notes.

Example:

```text
Lunch with team
```

---

## reference_number

Bank reference.

---

## upi_id

UPI handle.

Example:

```text
upiswiggy@icici
```

---

## transaction_timestamp

Actual financial event time.

---

## sms_received_timestamp

When SMS arrived.

---

## transaction_fingerprint

Duplicate detection key.

---

## confidence_score

Parser confidence.

Examples:

```text
0.95
0.75
```

---

## is_reviewed

Boolean.

User reviewed transaction.

---

## status

Examples:

```text
ACTIVE
REVERSED
IGNORED
```

---

# 11. TRANSFERS

Purpose:

Link money movement.

---

## source_transaction_id

Debit transaction.

---

## destination_transaction_id

Credit transaction.

---

## transfer_type

Allowed Values:

```text
INTERNAL
ACCOUNT_TRANSFER
CREDIT_CARD_PAYMENT
LOAN_PAYMENT
CASH_WITHDRAWAL
```

---

## confidence_score

Transfer matching confidence.

---

## is_confirmed

User confirmed transfer.

---

# 12. USER_FEEDBACK

Purpose:

Learning history.

---

## feedback_type

Allowed Values:

```text
CATEGORY_CHANGE
MERCHANT_CHANGE
DESCRIPTION_UPDATE
ACCOUNT_UPDATE
TRANSFER_LINK
BALANCE_RECONCILIATION
```

---

## old_value

Previous value.

---

## new_value

Updated value.

---

## source

Examples:

```text
USER
TELEGRAM
AI
```

---

# 13. BALANCE_SNAPSHOTS

Purpose:

Historical balances.

---

## snapshot_date

Date balance recorded.

---

## balance

Account balance.

---

## currency

Balance currency.

---

# 14. AUDIT_LOG

Purpose:

Immutable audit history.

Never updated.

Never deleted.

---

## entity_type

Examples:

```text
transaction
account
category
merchant
```

---

## entity_id

Affected record.

---

## action

Examples:

```text
CREATE
UPDATE
CATEGORY_CHANGE
DESCRIPTION_UPDATE
```

---

## field_name

Changed field.

Example:

```text
category_id
```

---

## old_value

Value before change.

---

## new_value

Value after change.

---

## source

Examples:

```text
USER
SYSTEM
TELEGRAM
AI
```

---

## correlation_id

Workflow trace.

---

## request_id

Request trace.

---

## session_id

Session trace.

---

## created_at

Audit timestamp.

---

# 15. System Seed Data

Default Categories:

```text
Food
Transport
Shopping
Bills
Health
Travel
Entertainment
Salary
Investment
Transfer
Loan
EMI
Refund
Miscellaneous
```

These categories must be seeded during initial deployment.

---

# 16. Data Ownership Rules

Every business record must belong to:

```text
user_id
```

Exceptions:

```text
Global Merchants
System Categories
```

---

# 17. AI Rules

AI may:

* Suggest Categories
* Suggest Merchants
* Suggest Descriptions

AI may not:

* Modify Transactions
* Delete Transactions
* Modify Balances

without user approval.

---

# 18. Approval

Status: Approved

This document is the authoritative definition of all database entities, attributes, ownership rules, validation rules, and business meanings within the Personal Finance Tracking Platform.
