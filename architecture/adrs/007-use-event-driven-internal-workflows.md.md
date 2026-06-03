# ADR-007: Use Event-Driven Internal Workflows

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform contains multiple business domains that must react to the same business events.

Example:

A single SMS may trigger:

```text id="z1k7dv"
Store Raw Event

Create Transaction

Update Balance

Create Audit Log

Generate AI Suggestions

Send Telegram Notification

Update Learning Engine
```

If these modules are tightly coupled, the system becomes:

```text id="l4y0f2"
Difficult To Maintain

Difficult To Test

Difficult To Extend

Difficult To Scale
```

The platform requires a mechanism that allows modules to react to business events without directly depending on each other.

---

# Problem Statement

Without event-driven workflows, business logic becomes tightly coupled.

Example:

```python id="q5y1v7"
transaction_service

    ↓

balance_service

    ↓

telegram_service

    ↓

ai_service

    ↓

audit_service
```

Problems:

```text id="z3f5s9"
High Coupling

Complex Dependencies

Difficult Testing

Difficult Feature Expansion
```

Adding a new feature requires modifying existing services.

This violates maintainability principles.

---

# Decision Drivers

The architecture must support:

## Loose Coupling

Requirements:

```text id="z2m0rw"
Independent Modules

Reduced Dependencies

Clear Boundaries
```

---

## Extensibility

Requirements:

```text id="d7r2mw"
Add New Features

Add New Consumers

Minimal Refactoring
```

---

## Testability

Requirements:

```text id="a6j5vk"
Unit Testing

Event Testing

Independent Validation
```

---

## Future Scalability

Requirements:

```text id="j6g9tb"
Future Service Extraction

Future Message Brokers

Future Async Processing
```

---

# Alternatives Considered

## Option 1 — Direct Service Calls

Example:

```text id="h3u5fr"
Transaction Service
↓
Telegram Service
↓
AI Service
↓
Audit Service
```

Advantages:

```text id="e7h6tw"
Simple
Easy To Understand
```

Disadvantages:

```text id="c8m4zv"
Tight Coupling

Poor Extensibility

Difficult Testing
```

---

## Option 2 — Event-Driven Internal Architecture

Example:

```text id="h5n9pd"
Transaction Created
↓
Publish Event
↓
Consumers React
```

Advantages:

```text id="i8w3qx"
Loose Coupling

Scalable

Extensible

Cleaner Design
```

Disadvantages:

```text id="b4g0sd"
Slightly More Complex
```

---

## Option 3 — External Message Broker

Examples:

```text id="y7s1lr"
Kafka

RabbitMQ

SQS
```

Advantages:

```text id="r8m0cf"
Highly Scalable
```

Disadvantages:

```text id="o7w4hv"
Operational Complexity

Overkill For MVP
```

---

# Decision

The platform shall use:

```text id="x7t8ja"
Internal Domain Events
```

for communication between modules.

Events shall be published inside the monolith.

No external message broker is required for MVP.

---

# Architecture

## Event Flow

```text id="n5u2az"
Business Action
      ↓
Publish Event
      ↓
Event Dispatcher
      ↓
Event Handlers
```

---

## Example

```text id="j2w7hr"
SMS Received
      ↓
RawEventReceived
      ↓
Parser Module
      ↓
TransactionCreated
      ↓
Balance Module

Telegram Module

Audit Module

AI Module
```

---

# Event Design Principles

Events represent:

```text id="s4h8vb"
Business Facts
```

not commands.

Example:

Correct:

```text id="k2w5rh"
TransactionCreated
```

Incorrect:

```text id="d1m6cb"
CreateTransaction
```

Events describe something that already happened.

---

# Event Naming Standard

Format:

```text id="q8v2sx"
PastTenseEvent
```

Examples:

```text id="u4x5jw"
RawEventReceived

TransactionCreated

BalanceUpdated

FeedbackReceived

CategoryChanged

DescriptionUpdated
```

---

# Approved Domain Events

## Ingestion Events

```text id="a6w9ph"
RawEventReceived

RawEventValidated

RawEventRejected
```

---

## Transaction Events

```text id="x1r3ob"
TransactionCreated

TransactionUpdated

TransactionDeleted
```

Note:

```text id="v6d8rn"
Financial Records Are Soft Deleted
```

---

## Account Events

```text id="h4k1zt"
AccountCreated

AccountUpdated

AccountArchived
```

---

## Balance Events

```text id="z8q4vl"
BalanceUpdated

BalanceReconciled
```

---

## Category Events

```text id="j5v7ty"
CategoryAssigned

CategoryChanged
```

---

## Merchant Events

```text id="g2r1wa"
MerchantResolved

MerchantPatternCreated
```

---

## AI Events

```text id="r3q5hu"
AISuggestionGenerated

FeedbackLearned
```

---

## Telegram Events

```text id="p6m4xr"
TelegramNotificationQueued

TelegramMessageReceived
```

---

## Audit Events

```text id="v1w9cf"
AuditLogCreated
```

---

# Event Payload Standards

Events must contain:

```text id="d4u2mn"
event_id

event_type

occurred_at

correlation_id

payload
```

---

## Example

```json id="v7c1xt"
{
  "event_id": "uuid",
  "event_type": "TransactionCreated",
  "occurred_at": "2026-06-01T10:00:00Z",
  "correlation_id": "uuid",
  "payload": {
    "transaction_id": "uuid"
  }
}
```

---

# Correlation IDs

Every workflow must have:

```text id="w9h3tr"
correlation_id
```

Purpose:

```text id="x4m7pz"
Tracing

Debugging

Auditing
```

---

## Example

```text id="f5j8ys"
SMS
↓
Transaction
↓
Balance Update
↓
Telegram Message
```

All share the same:

```text id="z2q4ub"
correlation_id
```

---

# Event Dispatcher

MVP implementation:

```text id="k8v6dy"
In-Memory Event Dispatcher
```

Responsibilities:

```text id="c7n4mb"
Register Handlers

Publish Events

Execute Handlers
```

---

# Event Handler Rules

Handlers must:

```text id="r5w2kg"
Be Idempotent

Handle Failures

Log Processing
```

---

Handlers must not:

```text id="v4h1ty"
Modify Unrelated Domains

Create Circular Dependencies
```

---

# Synchronous vs Asynchronous Events

## MVP

Use:

```text id="y3n8sp"
Synchronous Internal Events
```

Reason:

```text id="d6m7ht"
Simpler

Reliable

Easy Debugging
```

---

## Future

Possible:

```text id="h8j3sv"
Async Workers

Message Brokers
```

without changing business logic.

---

# Event Processing Example

## Transaction Creation

```text id="t4r7wv"
TransactionCreated
```

Consumers:

```text id="s6v9dr"
Balance Module

Telegram Module

Audit Module

AI Module
```

Each reacts independently.

---

# Failure Handling

Example:

```text id="z5m8ph"
Transaction Created
```

Telegram fails.

Result:

```text id="m2k7wv"
Transaction Remains Valid

Balance Updated

Audit Log Created
```

Notification retried later.

---

# Event Reliability Principle

Core financial processing must never depend on:

```text id="k7q2ub"
Telegram

AI

Reporting
```

Only:

```text id="r1t8wm"
Transaction Persistence
Balance Updates
Audit Logging
```

are critical path.

---

# Critical vs Non-Critical Events

## Critical

```text id="a3j9kr"
TransactionCreated

BalanceUpdated

AuditLogCreated
```

Must succeed.

---

## Non-Critical

```text id="d7x1vl"
AISuggestionGenerated

TelegramNotificationQueued

ReportGenerated
```

May fail independently.

---

# Protected Financial Transaction Boundary

The following workflow must remain inside a single database transaction:

Create Transaction
↓
Update Account Balance
↓
Create Audit Log
↓
Commit

These operations shall never be separated into independent asynchronous events.

Reason:

Financial consistency requires atomic execution.

Event-driven workflows may occur only after successful commit.

Examples:

After Commit:
- Telegram Notifications
- AI Suggestions
- Learning Engine Updates
- Reporting Updates

Before Commit:
- Transaction Creation
- Balance Updates
- Audit Logging

---

# Event Logging

Every published event must be logged.

Store:

```text id="f4q8zw"
event_type

correlation_id

timestamp

status
```

Future table:

```text id="y6m3hx"
event_log
```

---

# Event Testing Standards

Each event requires:

```text id="k9t2rs"
Publisher Tests

Handler Tests

Integration Tests
```

---

# Future Message Broker Compatibility

The architecture must allow future migration to:

```text id="n3w5pb"
Kafka

RabbitMQ

SQS

Pub/Sub
```

without changing domain logic.

Only dispatcher implementation changes.

---

# Operational Benefits

Advantages:

```text id="b1h4zr"
Loose Coupling

Cleaner Architecture

Easier Maintenance

Future Scalability
```

---

# Financial Benefits

Advantages:

```text id="j7k8qp"
Reliable Transaction Processing

Independent Notifications

Independent AI Processing
```

---

# Consequences

## Positive Consequences

### Extensibility

New features subscribe to events.

---

### Maintainability

Modules remain independent.

---

### Scalability

Supports future extraction.

---

### Better Testing

Events can be tested independently.

---

### Cleaner Architecture

Reduced module coupling.

---

## Negative Consequences

### More Complexity

Compared to direct service calls.

---

### Event Debugging

Requires tracing through handlers.

---

### Additional Infrastructure Later

Future message brokers may be introduced.

---

# Event-Driven Boundaries Rule

Events shall be used:

```text id="u4h7vb"
Between Modules
```

Events shall not replace:

```text id="m5x9wr"
Simple Internal Method Calls
```

within the same module.

Example:

Good:

```text id="v7k3td"
Transaction Module
↓
TransactionCreated
↓
Telegram Module
```

Bad:

```text id="h1r5zc"
TransactionService
↓
Event
↓
TransactionRepository
```

Use events only for cross-domain communication.

---

# Rejected Alternatives

## Direct Service Chaining

Rejected because:

```text id="e6j8ny"
High Coupling

Harder Maintenance

Harder Scaling
```

---

## Kafka

Rejected because:

```text id="m4v1tb"
Premature Complexity
```

for MVP.

---

## RabbitMQ

Rejected because:

```text id="n9x5pw"
Operational Overhead
```

for current scale.

---

# Review Criteria

This ADR should be revisited if:

```text id="p2m8xk"
User Count > 100,000

Event Volume Becomes Large

Async Processing Required

Multiple Services Introduced
```

---

# Related Documents

```text id="z7q4rd"
06-high_level_design.md

07-sequence_diagrams.md

12-coding_standards.md

13-ai_integration_standards.md

14-sprint_roadmap.md
```

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall use internal domain events as the primary mechanism for communication between modules.

Events will provide loose coupling, extensibility, maintainability, and future scalability while preserving the simplicity of a modular monolith architecture.

External message brokers are explicitly deferred until justified by actual scale or business requirements.
