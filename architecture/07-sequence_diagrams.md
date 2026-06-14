# 07-sequence_diagrams.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Sequence Diagrams and Workflow Specification

Architecture Style: Modular Monolith

Backend Framework: FastAPI

Database: PostgreSQL

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines the major system workflows and sequence diagrams for the Personal Finance Tracking Platform.

It explains how actors, modules, services, and storage components interact during important business processes.

This document must be used when implementing:

* Ingestion workflows
* Parser workflows
* Transaction creation workflows
* Account discovery workflows
* Telegram feedback workflows
* Transfer detection workflows
* Balance reconciliation workflows
* Future AI workflows
* Future Account Aggregator workflows

---

# 2. Sequence Diagram Principles

## 2.1 Raw Event First

All external input must first be stored as a raw event before any parsing or processing occurs.

Rule:

```text
External Input
↓
Raw Event
↓
Processing
```

---

## 2.2 No Data Loss

If parsing fails, the raw event must remain available for future reprocessing.

---

## 2.3 Domain Events

Important business actions should publish domain events.

Examples:

* TransactionCreated
* TransactionUpdated
* NewAccountDetected
* UserFeedbackReceived
* BalanceReconciled
* AuditEventCreated

---

## 2.4 User Ownership

Every workflow must preserve user ownership through `user_id`.

---

# 3. SMS Ingestion and Transaction Creation Flow

## 3.1 Description

This is the main MVP workflow.

A bank SMS arrives on the Android phone. MacroDroid forwards the SMS to the FastAPI backend. The backend stores the raw message, parses it, resolves the account, merchant, category, creates a transaction, updates balance, and optionally sends a Telegram notification.

---

## 3.2 Text Flow

```text
Bank SMS
    ↓
Android Phone
    ↓
MacroDroid
    ↓
POST /api/v1/ingest/sms
    ↓
Ingestion API
    ↓
Raw Event Service
    ↓
raw_events table
    ↓
Parser Engine
    ↓
Account Resolver
    ↓
Merchant Resolver
    ↓
Category Resolver
    ↓
Transaction Engine
    ↓
transactions table
    ↓
TransactionCreated Event
    ↓
Balance Engine
    ↓
Telegram Notifier
    ↓
Audit Logger
```

---

## 3.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant Bank as Bank / Financial Institution
    participant Phone as Android Phone
    participant MacroDroid as MacroDroid
    participant API as Ingestion API
    participant RawEvent as Raw Event Service
    participant DB as PostgreSQL
    participant Parser as Parser Engine
    participant Account as Account Resolver
    participant Merchant as Merchant Resolver
    participant Category as Category Resolver
    participant Txn as Transaction Engine
    participant Events as Domain Event Bus
    participant Balance as Balance Engine
    participant Telegram as Telegram Bot

    Bank->>Phone: Send transaction SMS
    Phone->>MacroDroid: SMS received trigger
    MacroDroid->>API: POST /api/v1/ingest/sms
    API->>RawEvent: Validate and create raw event
    RawEvent->>DB: Insert raw_events
    RawEvent->>Parser: Trigger parsing
    Parser->>Parser: Extract amount, direction, account, merchant
    Parser->>Account: Resolve account
    Account->>DB: Lookup account by user, bank, last digits
    alt Account Found
        Account-->>Parser: Existing account
    else Account Not Found
        Account->>DB: Create pending account
        Account->>Events: Publish NewAccountDetected
    end
    Parser->>Merchant: Resolve merchant
    Merchant->>DB: Check user and global merchant patterns
    Merchant-->>Parser: Merchant result
    Parser->>Category: Resolve category
    Category-->>Parser: Category result
    Parser->>Txn: Create transaction request
    Txn->>Txn: Generate transaction fingerprint
    Txn->>DB: Check duplicate fingerprint
    alt Duplicate
        Txn->>DB: Mark raw event duplicate
    else New Transaction
        Txn->>DB: Insert transaction
        Txn->>Events: Publish TransactionCreated
        Events->>Balance: Update estimated balance
        Balance->>DB: Update account balance
        Events->>Telegram: Notify user if required
    end
```

---

# 4. Duplicate SMS Flow

## 4.1 Description

Duplicate SMS messages may happen because of SMS retransmission, historical import, or reprocessing. The system must avoid duplicate transaction creation.

---

## 4.2 Text Flow

```text
Incoming SMS
    ↓
Generate message_hash
    ↓
Check raw_events
    ↓
If same hash exists:
        Mark duplicate raw event
        Do not create transaction
    ↓
If hash is new:
        Continue processing
```

---

## 4.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant API as Ingestion API
    participant RawEvent as Raw Event Service
    participant DB as PostgreSQL
    participant Parser as Parser Engine

    API->>RawEvent: Receive SMS payload
    RawEvent->>RawEvent: Generate message_hash
    RawEvent->>DB: Check existing raw_events by hash
    alt Exact duplicate exists
        RawEvent->>DB: Insert or mark duplicate event
        RawEvent-->>API: Return duplicate accepted
    else New message
        RawEvent->>DB: Insert raw event
        RawEvent->>Parser: Continue processing
    end
```

---

# 5. Account Discovery Flow

## 5.1 Description

When a transaction references a bank account or credit card that is not yet known, the system creates a pending account and asks the user to provide a friendly name.

---

## 5.2 Text Flow

```text
Parser detects bank and last digits
    ↓
Account Resolver checks accounts
    ↓
No matching account found
    ↓
Create Pending Account
    ↓
Publish NewAccountDetected
    ↓
Telegram asks user to name account
    ↓
User replies
    ↓
Account updated
    ↓
Audit log created
```

---

## 5.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant Parser as Parser Engine
    participant Account as Account Resolver
    participant DB as PostgreSQL
    participant Events as Domain Event Bus
    participant Telegram as Telegram Bot
    participant User as User
    participant Audit as Audit Logger

    Parser->>Account: Resolve bank + last four digits
    Account->>DB: Search account
    alt Account exists
        Account-->>Parser: Return account
    else Account missing
        Account->>DB: Create account with status PENDING
        Account->>Events: Publish NewAccountDetected
        Events->>Telegram: Send account naming request
        Telegram->>User: "New account detected. Name this account."
        User->>Telegram: "Salary Account"
        Telegram->>Account: Update account name and status
        Account->>DB: Update account
        Account->>Audit: Record ACCOUNT_UPDATE
    end
```

---

# 6. Telegram Description Collection Flow

## 6.1 Description

When a transaction is created, the Telegram bot may ask the user for an optional description. The user can respond immediately or later using the transaction ID.

---

## 6.2 Text Flow

```text
Transaction Created
    ↓
Telegram sends message with transaction ID
    ↓
User replies with transaction ID + description
    ↓
Telegram webhook receives reply
    ↓
Feedback Service parses reply
    ↓
Transaction updated
    ↓
Audit log created
```

---

## 6.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant Events as Domain Event Bus
    participant Telegram as Telegram Bot
    participant User as User
    participant API as Telegram Webhook API
    participant Feedback as Feedback Service
    participant Txn as Transaction Service
    participant DB as PostgreSQL
    participant Audit as Audit Logger

    Events->>Telegram: TransactionCreated
    Telegram->>User: "TXN-123 ₹70 SmartQ. Reply with description."
    User->>Telegram: "TXN-123 Lunch at office"
    Telegram->>API: Webhook update
    API->>Feedback: Parse transaction ID and description
    Feedback->>Txn: Update transaction description
    Txn->>DB: Update transaction.description
    Txn->>Audit: Record DESCRIPTION_UPDATE
```

---

# 7. Category Correction Flow

## 7.1 Description

The user may correct a transaction category through Telegram or future UI. This correction should update the transaction, create feedback history, create audit log, and optionally update merchant patterns.

---

## 7.2 Text Flow

```text
User replies with corrected category
    ↓
Feedback Service validates category
    ↓
Transaction category updated
    ↓
User feedback stored
    ↓
Audit log created
    ↓
Learning Engine evaluates rule creation
```

---

## 7.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant User as User
    participant Telegram as Telegram Bot
    participant API as Telegram Webhook API
    participant Feedback as Feedback Service
    participant Category as Category Service
    participant Txn as Transaction Service
    participant Learning as Learning Engine
    participant Audit as Audit Logger
    participant DB as PostgreSQL

    User->>Telegram: "TXN-123 Food"
    Telegram->>API: Webhook update
    API->>Feedback: Parse feedback
    Feedback->>Category: Resolve category Food
    Category->>DB: Lookup category
    Feedback->>Txn: Update transaction category
    Txn->>DB: Update category_id
    Feedback->>DB: Insert user_feedback
    Txn->>Audit: Record CATEGORY_CHANGE
    Feedback->>Learning: Evaluate merchant pattern learning
```

---

# 8. Merchant Learning Flow

## 8.1 Description

When a user corrects a merchant or category, the system may create a user-specific merchant pattern so future similar transactions are categorized automatically.

---

## 8.2 Text Flow

```text
User corrects transaction
    ↓
Learning Engine checks merchant_raw
    ↓
Creates user merchant pattern
    ↓
Future transactions use this rule
```

---

## 8.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant Feedback as Feedback Service
    participant Learning as Learning Engine
    participant Merchant as Merchant Service
    participant DB as PostgreSQL

    Feedback->>Learning: User corrected merchant/category
    Learning->>Merchant: Analyze merchant_raw pattern
    Merchant->>DB: Check existing user pattern
    alt Pattern exists
        Merchant->>DB: Update confidence or timestamp
    else Pattern missing
        Merchant->>DB: Create user-specific merchant_pattern
    end
```

---

# 9. Transfer Detection Flow

## 9.1 Description

Transfers must be identified so they are not counted as income or expenses. Credit card bill payments, own-account transfers, and cash withdrawals are examples of transfers.

---

## 9.2 Text Flow

```text
Transaction created
    ↓
Transaction Engine checks transfer indicators
    ↓
If likely transfer:
        business_type = TRANSFER
        Create transfer candidate
    ↓
If matching opposite transaction exists:
        Link source and destination
    ↓
If not:
        Store partial transfer
```

---

## 9.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant Txn as Transaction Engine
    participant DB as PostgreSQL
    participant Transfer as Transfer Service
    participant Audit as Audit Logger

    Txn->>Transfer: Evaluate transaction for transfer
    Transfer->>Transfer: Check credit card payment / internal transfer patterns
    alt Transfer detected
        Transfer->>DB: Update transaction business_type = TRANSFER
        Transfer->>DB: Search matching opposite transaction
        alt Matching transaction found
            Transfer->>DB: Create transfer with source and destination
            Transfer->>Audit: Record TRANSFER_LINK
        else No match found
            Transfer->>DB: Create partial transfer record
        end
    else Not a transfer
        Transfer-->>Txn: No action
    end
```

---

# 10. Balance Update Flow

## 10.1 Description

After a transaction is created, the balance engine updates the estimated balance of the affected account.

---

## 10.2 Text Flow

```text
TransactionCreated event
    ↓
Balance Engine receives event
    ↓
Determine account type
    ↓
Apply debit/credit rule
    ↓
Update estimated_balance
    ↓
Optionally create balance snapshot
```

---

## 10.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant Events as Domain Event Bus
    participant Balance as Balance Engine
    participant Account as Account Service
    participant DB as PostgreSQL
    participant Audit as Audit Logger

    Events->>Balance: TransactionCreated
    Balance->>Account: Load account
    Account->>DB: Fetch account
    Balance->>Balance: Apply account-type balance rule
    Balance->>DB: Update estimated_balance
    Balance->>Audit: Record balance update if required
```

---

# 11. Balance Reconciliation Flow

## 11.1 Description

Estimated balances may drift due to missed SMS, cash transactions, or parsing issues. Reconciliation allows the user to enter the actual account balance.

---

## 11.2 Text Flow

```text
User provides actual balance
    ↓
System compares estimated balance
    ↓
Difference calculated
    ↓
Estimated balance updated
    ↓
Balance snapshot created
    ↓
Audit log created
```

---

## 11.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant User as User
    participant API as Accounts API
    participant Account as Account Service
    participant DB as PostgreSQL
    participant Audit as Audit Logger

    User->>API: POST /accounts/{id}/reconcile
    API->>Account: Reconcile actual balance
    Account->>DB: Load estimated balance
    Account->>Account: Calculate difference
    Account->>DB: Update estimated_balance
    Account->>DB: Insert balance_snapshot
    Account->>Audit: Record BALANCE_RECONCILIATION
```

---

# 12. Historical SMS Import Flow

## 12.1 Description

The user may choose to import historical SMS messages from a custom date range or predefined range such as last 3 months, last 6 months, last 1 year, or all available.

---

## 12.2 Text Flow

```text
User selects import range
    ↓
MacroDroid or future Android App exports messages
    ↓
Backend receives batch
    ↓
Each message stored as raw_event
    ↓
Each raw_event processed
    ↓
Duplicates skipped
```

---

## 12.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant User as User
    participant Importer as SMS Import Source
    participant API as Ingestion API
    participant RawEvent as Raw Event Service
    participant Parser as Parser Engine
    participant DB as PostgreSQL

    User->>Importer: Select date range
    Importer->>API: Send SMS batch
    loop For each SMS
        API->>RawEvent: Create raw event
        RawEvent->>DB: Check duplicate hash
        alt Duplicate
            RawEvent->>DB: Mark duplicate
        else New
            RawEvent->>DB: Insert raw event
            RawEvent->>Parser: Process
        end
    end
```

---

# 13. Future AI Suggestion Flow

## 13.1 Description

AI may suggest merchant or category values in future phases. AI must not directly modify financial records.

---

## 13.2 Text Flow

```text
Unknown transaction
    ↓
AI Suggestion Service
    ↓
Local Ollama Model
    ↓
Suggestion generated
    ↓
If confidence high:
        Store suggestion
    ↓
If user approval required:
        Ask via Telegram
    ↓
User accepts or rejects
```

---

## 13.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant Txn as Transaction Service
    participant AI as AI Suggestion Service
    participant Ollama as Local LLM via Ollama
    participant DB as PostgreSQL
    participant Telegram as Telegram Bot
    participant User as User

    Txn->>AI: Request category/merchant suggestion
    AI->>Ollama: Prompt local model
    Ollama-->>AI: Suggestion + confidence
    AI->>DB: Store AI suggestion
    alt Approval required
        AI->>Telegram: Ask user to confirm
        Telegram->>User: "Use Food for this transaction?"
    end
```

---

# 14. Future Account Aggregator Flow

## 14.1 Description

AA integration should be implemented as another ingestion adapter, not as a separate transaction engine.

---

## 14.2 Text Flow

```text
User grants AA consent
    ↓
AA Provider sends financial data
    ↓
AA Adapter receives structured transaction
    ↓
Raw Event stored
    ↓
Normalizer converts to transaction contract
    ↓
Transaction Engine processes normally
```

---

## 14.3 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant User as User
    participant AA as Account Aggregator
    participant Adapter as AA Adapter
    participant RawEvent as Raw Event Service
    participant Normalizer as AA Normalizer
    participant Txn as Transaction Engine
    participant DB as PostgreSQL

    User->>AA: Grant consent
    AA->>Adapter: Send financial data
    Adapter->>RawEvent: Store AA raw event
    RawEvent->>DB: Insert raw_events
    Adapter->>Normalizer: Normalize AA payload
    Normalizer->>Txn: Submit transaction contract
    Txn->>DB: Create transaction
```

---

# 15. Authentication Flows

## 15.1 Description

Users authenticate using email and password. API access requires a JWT access
token. Refresh-token exchange uses a refresh token in the request body and then
validates the current database user before issuing a new access token.

---

## 15.2 Login Text Flow

```text
User Login
    ↓
Auth API
    ↓
Validate Password
    ↓
Generate Access Token
    ↓
Generate Refresh Token
    ↓
Return Tokens
```

---

## 15.3 Login Sequence Diagram

```mermaid
sequenceDiagram
    participant User as User
    participant API as Auth API
    participant Auth as Auth Service
    participant DB as PostgreSQL
    participant JWT as JWT Service

    User->>API: POST /api/v1/auth/login
    API->>Auth: Validate credentials
    Auth->>DB: Load user by email
    Auth->>Auth: Verify Argon2 password hash
    Auth->>JWT: Generate access and refresh tokens
    JWT-->>API: Tokens
    API-->>User: Return tokens
```

---

## 15.4 Protected Request Middleware Flow

```text
Client Request
    ↓
Authentication Middleware
    ↓
Extract Bearer Access Token
    ↓
Validate Signature, Expiry, And Token Type
    ↓
Load Current User
    ↓
Reject Missing, Disabled, Or Soft Deleted User
    ↓
Attach User To Request State
    ↓
Route Handler Uses get_current_user
```

---

## 15.5 Protected Request Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Middleware as Auth Middleware
    participant JWT as JWT Service
    participant DB as PostgreSQL
    participant API as Protected API

    Client->>Middleware: GET /api/v1/users/me + Bearer access token
    Middleware->>JWT: Validate access token
    JWT-->>Middleware: Claims
    Middleware->>DB: Load user by user_id
    DB-->>Middleware: Active user
    Middleware->>API: Attach current_user and continue
    API-->>Client: Current user response
```

---

## 15.6 Refresh Token Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant Auth as Refresh Token Service
    participant JWT as JWT Service
    participant DB as PostgreSQL

    Client->>API: POST /api/v1/auth/refresh
    API->>Auth: Validate refresh token
    Auth->>JWT: Decode refresh token
    JWT-->>Auth: Refresh claims
    API->>DB: Load current user
    DB-->>API: Active user
    API->>JWT: Issue new access token
    JWT-->>API: Access token
    API-->>Client: New access token
```

---

# 16. Error Handling Flow

## 16.1 Parser Failure

```text
Raw Event Stored
    ↓
Parser Fails
    ↓
processing_status = FAILED
    ↓
processing_error stored
    ↓
Transaction not created
    ↓
User may review later
```

---

## 16.2 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant RawEvent as Raw Event Service
    participant Parser as Parser Engine
    participant DB as PostgreSQL
    participant Telegram as Telegram Bot

    RawEvent->>Parser: Process raw event
    Parser->>Parser: Attempt parse
    alt Parse success
        Parser-->>RawEvent: Parsed result
    else Parse failure
        Parser->>DB: Mark raw event FAILED
        Parser->>DB: Store processing_error
        Parser->>Telegram: Optional notify if needed
    end
```

---

# 17. Sequence Diagram Rules for AI Agents

AI coding agents must follow these workflow rules:

* Store raw event before processing.
* Do not create transaction if duplicate.
* Do not skip account resolution.
* Do not skip user ownership validation.
* Do not hard delete transactions.
* Do not let AI directly mutate transactions.
* Do not classify transfers as expenses.
* Do not treat all credits as income.
* Always create audit log for user-driven corrections.
* Use domain events for cross-module side effects.

---

# 18. Approval

Status: Approved

This document is the authoritative workflow and sequence diagram specification for the Personal Finance Tracking Platform.

All workflow implementations must align with this document.
