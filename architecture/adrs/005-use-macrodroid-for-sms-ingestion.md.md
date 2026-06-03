# ADR-005: Use MacroDroid for SMS Ingestion

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform relies on bank SMS messages as the primary source of financial transaction data.

Examples:

```text id="n2czs7"
Debit Transactions

Credit Transactions

Salary Credits

UPI Payments

ATM Withdrawals

Credit Card Transactions

Refunds
```

The platform requires a mechanism to:

```text id="xj8vhz"
Detect Incoming SMS

Extract SMS Content

Transmit SMS To Backend

Support Real-Time Processing

Support Historical Imports

Minimize Development Effort
```

The system should work initially without building a custom Android application.

---

# Problem Statement

Most Indian banks provide transaction information through SMS.

Example:

```text id="1bqv5r"
Rs. 120.00 debited from A/c XX0452
on 01-Jun-26.

UPI Ref:
123456789.

UPISWIGGY@ICICI
```

The platform must automatically capture these messages and deliver them to the backend.

Requirements:

```text id="s6x7xa"
Near Real-Time

Reliable

Low Cost

Android Compatible

Simple To Configure
```

---

# Decision Drivers

The solution must support:

## SMS Monitoring

Requirements:

```text id="8umvso"
Detect New SMS

Filter Bank SMS

Capture Full Message
```

---

## Real-Time Processing

Requirements:

```text id="qmv3po"
Immediate Delivery

Minimal Latency
```

---

## Historical Imports

Requirements:

```text id="6s2fdm"
Import Existing SMS

Date Range Selection

Backfill Support
```

---

## Cost

Requirements:

```text id="i6h89t"
Free Or Low Cost
```

---

## Development Speed

Requirements:

```text id="1yqdr6"
No Android Development

No App Store Publishing

No Device-Specific Coding
```

---

# Alternatives Considered

## Option 1 — MacroDroid

Advantages:

```text id="wskn3p"
Low Cost

SMS Triggers

HTTP Requests

Android Support

Automation Workflows

Simple Setup
```

Disadvantages:

```text id="gx7lzw"
Android Only

Depends On Third-Party App
```

---

## Option 2 — Custom Android Application

Advantages:

```text id="0gh4oq"
Full Control

Native Experience

Maximum Flexibility
```

Disadvantages:

```text id="9k35sx"
Longer Development

Android Maintenance

Permission Management

Play Store Considerations
```

---

## Option 3 — Tasker

Advantages:

```text id="w0ev5z"
Powerful Automation
```

Disadvantages:

```text id="g3dd2j"
Steeper Learning Curve

More Complex Configuration
```

---

## Option 4 — Bank APIs

Advantages:

```text id="oz0hjg"
Structured Data
```

Disadvantages:

```text id="2wfmcu"
Unavailable For Most Banks

Authentication Complexity

Not Suitable For MVP
```

---

## Option 5 — Account Aggregator

Advantages:

```text id="04n75q"
High Quality Data

Structured Transactions
```

Disadvantages:

```text id="f5z7qj"
Requires User Consent

Additional Integration

Not Suitable For Initial MVP
```

---

# Decision

The platform shall use:

```text id="tnprz7"
MacroDroid
```

as the primary SMS ingestion mechanism.

MacroDroid will:

```text id="0g96f4"
Monitor SMS

Capture Relevant Messages

Call Backend APIs

Transmit Transaction Data
```

---

# Architecture

## Real-Time Flow

```text id="r8mkxr"
Incoming SMS
      ↓
Android Phone
      ↓
MacroDroid
      ↓
FastAPI Endpoint
      ↓
PostgreSQL
      ↓
Parser Engine
      ↓
Transaction Creation
```

---

## Historical Import Flow

```text id="j1x5z9"
Existing SMS
      ↓
MacroDroid Batch Export
      ↓
FastAPI Import API
      ↓
Raw Events
      ↓
Parser Engine
```

---

# SMS Payload Standard

MacroDroid shall send:

```json id="e9j5ra"
{
  "sender": "ICICIB",
  "message_text": "Rs.120 debited...",
  "received_at": "2026-06-01T10:15:00Z"
}
```

Future fields:

```json id="7t4x5j"
{
  "device_id": "",
  "sim_slot": "",
  "message_id": ""
}
```

---

# Backend Endpoint

Primary endpoint:

```http id="uygkho"
POST /api/v1/ingest/sms
```

Authentication:

```text id="7yx8mf"
API Key
```

Header:

```http id="65ofpn"
X-API-KEY
```

---

# Raw Event Storage

Every SMS must be stored.

Table:

```text id="7u0wy7"
raw_events
```

Reason:

```text id="yzrq9m"
Auditability

Parser Improvements

Reprocessing

Debugging
```

---

# Processing Pipeline

```text id="57lbxm"
Receive SMS
↓
Validate API Key
↓
Store Raw Event
↓
Generate Fingerprint
↓
Check Duplicates
↓
Queue Processing
↓
Parse Message
↓
Create Transaction
↓
Update Balances
↓
Trigger Telegram Notification
```

---

# Duplicate Handling

Duplicate SMS messages are expected.

Examples:

```text id="9b3ap9"
Bank Retries

Carrier Retries

Manual Imports

Historical Reprocessing
```

---

## Duplicate Detection Strategy

Use:

```text id="gqg8l4"
Fingerprint Engine
```

Inputs:

```text id="3n5v1f"
Amount

Direction

Merchant

Account Last Four

Timestamp
```

Not:

```text id="8gq5n5"
Raw SMS Text Only
```

---

# Invalid SMS Handling

Some SMS messages will not be financial.

Examples:

```text id="c3z89l"
OTP Messages

Promotional Messages

Spam

Service Notifications
```

---

## Handling Strategy

Store in:

```text id="0m5v9p"
raw_events
```

Mark status:

```text id="k7wd0o"
INVALID

IGNORED

UNSUPPORTED
```

---

## Benefits

```text id="9ul6f7"
Future Parser Improvements

Audit Trail

Machine Learning Opportunities
```

---

# Supported Processing Modes

## Mode 1 — Real-Time

Selected MVP Mode.

Flow:

```text id="v8s24m"
SMS Arrives
↓
Immediate API Call
↓
Immediate Processing
```

Latency Target:

```text id="r4w0nn"
< 5 Seconds
```

---

## Mode 2 — Batch

Future Support.

Flow:

```text id="7kcl0m"
Collect SMS
↓
Send In Batches
↓
Bulk Import
```

---

# Source Agnostic Ingestion Principle

SMS is the current transport mechanism.

SMS is NOT the data model.

All ingestion sources must be normalized into the same internal event format.

Examples:

- SMS
- Account Aggregator
- CSV Import
- Email Statements
- Bank APIs

All sources must eventually produce:

Raw Event
↓
Parser
↓
Transaction

This prevents SMS-specific assumptions from leaking into the core financial engine.

---

# Migration Path

Current:

```text id="bfxi0e"
Laptop Hosting
```

Future:

```text id="m6q0ot"
VPS Hosting
```

MacroDroid configuration remains unchanged.

Only endpoint URL changes.

---

# Offline Support

Scenario:

```text id="m5ct3l"
Laptop Offline
```

Result:

```text id="fhlbvt"
SMS Retained On Device
```

User may later:

```text id="m1i0mt"
Batch Import Missing SMS
```

No data loss.

---

# Security Requirements

MacroDroid must never send:

```text id="y0mrzk"
Passwords

PINs

OTP Codes
```

to transaction processing endpoints.

---

## SMS Filtering

Allowed Senders:

```text id="qg15yk"
Bank Senders

Credit Card Providers

UPI Providers
```

---

Ignored:

```text id="0yr8ee"
Promotions

Marketing

Unknown Sources
```

---

# API Authentication

Authentication Method:

```text id="uzyxpf"
API Key
```

Reason:

```text id="9ccw65"
Simple

Lightweight

Reliable
```

---

# Reliability Strategy

MacroDroid failures shall not impact:

```text id="6n9kj6"
Existing Transactions

Balances

Reports
```

Failures affect only:

```text id="tt4lr8"
New SMS Delivery
```

---

# Retry Strategy

MacroDroid should retry:

```text id="78m7ul"
1 Minute

5 Minutes

15 Minutes
```

for failed API requests.

---

# Future iOS Considerations

MacroDroid is Android-only.

Future iOS support may require:

```text id="y6e93v"
Shortcuts

Dedicated Mobile App

Account Aggregator
```

The backend architecture shall remain unchanged.

---

# Account Aggregator Compatibility

Future Architecture:

```text id="k0hdb4"
SMS
+
Account Aggregator
+
CSV Import
```

All feed into:

```text id="hj5v3f"
Raw Event Pipeline
```

using a unified ingestion model.

---

# Operational Benefits

Advantages:

```text id="udn9lg"
Fast MVP

No Mobile Development

Free Automation

Simple Setup
```

---

# Financial Benefits

Advantages:

```text id="f1u4h0"
Immediate Transaction Capture

Supports Balance Tracking

Supports Spending Analysis

Supports AI Learning
```

---

# Consequences

## Positive Consequences

### Faster Development

No Android application required.

---

### Lower Cost

No Play Store deployment.

---

### Real-Time Processing

Transactions appear immediately.

---

### Supports Historical Imports

Past SMS messages can be imported.

---

### Easy VPS Migration

Only endpoint changes.

---

## Negative Consequences

### Android Dependency

Requires Android device.

---

### Third-Party Dependency

Relies on MacroDroid.

---

### Permission Requirements

SMS access permissions required.

---

# Rejected Alternatives

## Custom Android App

Rejected because:

```text id="zddxqb"
Longer Development

Higher Maintenance

Slower MVP Delivery
```

---

## Tasker

Rejected because:

```text id="4w8r5x"
More Complex Setup

Less Beginner Friendly
```

---

## Account Aggregator

Rejected because:

```text id="24h5a8"
Not Required For MVP

Additional Complexity
```

---

# Future Evolution

Current:

```text id="n1snyg"
MacroDroid
```

Future:

```text id="6uqmvn"
MacroDroid
+
Account Aggregator
+
CSV Import
+
Dedicated Mobile App
```

All sources shall reuse the same ingestion pipeline.

---

# Review Criteria

This ADR should be revisited if:

```text id="j7zqki"
Android Restrictions Change

MacroDroid Becomes Unsupported

iOS Support Becomes Mandatory

Large-Scale SaaS Requires Native Mobile App
```

---

# Related Documents

```text id="z1e6vy"
06-high_level_design.md

07-sequence_diagrams.md

08-api_contracts.md

11-deployment_standards.md

14-sprint_roadmap.md
```

---

# Final Decision

Accepted.

MacroDroid shall serve as the primary SMS ingestion mechanism for the Personal Finance Tracking Platform.

It provides the fastest, lowest-cost, and lowest-complexity path to real-time transaction capture while preserving future migration paths to Account Aggregator, CSV imports, native mobile applications, and SaaS-scale deployments.
