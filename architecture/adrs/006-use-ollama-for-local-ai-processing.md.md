# ADR-006: Use Ollama for Local AI Processing

Status: Accepted

Date: 2026-06-02

Decision Makers:

* Product Owner
* Solution Architect
* Technical Lead

---

# Context

The Personal Finance Tracking Platform will eventually use Artificial Intelligence to improve:

* Merchant recognition
* Category classification
* Transaction descriptions
* Financial insights
* User feedback processing
* Spending pattern analysis
* Future natural language queries

Examples:

```text id="kh5m4n"
KA51AJ7604@CNRB
```

AI may infer:

```text id="9uk7j5"
BMTC
Transport
```

---

Example:

```text id="e5xkz4"
UPISWIGGY@ICICI
```

AI may infer:

```text id="2hqq8m"
Swiggy
Food
```

The AI solution must support:

```text id="f10ztw"
Low Cost

Privacy

Future Growth

Local Processing

Vendor Independence
```

---

# Problem Statement

Financial transaction data is highly sensitive.

Examples:

```text id="nlhnf7"
Bank Accounts

Balances

Income

Expenses

Merchants

Transaction History
```

Sending all financial data to external AI providers creates concerns:

```text id="kikzgg"
Privacy

Cost

Compliance

Vendor Lock-In
```

The platform requires an AI architecture that:

```text id="gh9w4v"
Protects User Data

Minimizes Cost

Supports Offline Usage

Allows Future Expansion
```

---

# Decision Drivers

The AI solution must provide:

## Privacy

Requirements:

```text id="s4bznr"
Local Processing

No External Data Sharing

User Control
```

---

## Cost

Requirements:

```text id="2vh9t0"
Free For MVP

Predictable Cost

No Per-Request Billing
```

---

## Flexibility

Requirements:

```text id="lffwly"
Multiple Models

Provider Abstraction

Future Cloud Support
```

---

## Performance

Requirements:

```text id="v8grxq"
Low Latency

Local Inference

Simple Deployment
```

---

## Scalability

Requirements:

```text id="hl93ii"
Future SaaS Support

Future Cloud Models

Model Switching
```

---

# Alternatives Considered

## Option 1 — Ollama

Advantages:

```text id="fgaxnr"
Runs Locally

Open Source

Free

Supports Multiple Models

Simple API

Privacy Friendly
```

Disadvantages:

```text id="a0m88k"
Requires Local Resources

Slower Than Large Cloud Models
```

---

## Option 2 — OpenAI

Advantages:

```text id="6wz0tf"
Excellent Quality

Managed Infrastructure

Large Ecosystem
```

Disadvantages:

```text id="oz1o9d"
Recurring Cost

External Data Processing

Vendor Dependency
```

---

## Option 3 — Anthropic

Advantages:

```text id="1mkkl0"
High Quality Responses

Strong Reasoning
```

Disadvantages:

```text id="r0vob5"
Usage Costs

External Data Transfer
```

---

## Option 4 — Gemini

Advantages:

```text id="bix4tb"
Strong Multimodal Support
```

Disadvantages:

```text id="v7zwx7"
Vendor Dependency

Usage Costs
```

---

## Option 5 — No AI

Advantages:

```text id="2o8zw4"
Simpler System

No Cost
```

Disadvantages:

```text id="zhq7sk"
Poor Merchant Learning

More User Effort

Reduced Automation
```

---

# Decision

The platform shall use:

```text id="n0d39u"
Ollama
```

as the default AI runtime.

AI processing shall occur locally whenever possible.

---

# Architecture

## MVP Architecture

```text id="0s55s4"
FastAPI
     ↓
AI Service
     ↓
Ollama
     ↓
Local Models
```

---

## Future Architecture

```text id="s84n1o"
AI Service
     ↓
Provider Interface
     ↓
Ollama

OpenAI

Anthropic

Gemini
```

The application code must not depend directly on a specific provider.

---

# Provider Abstraction Requirement

Mandatory interface:

```python id="mwqzcv"
BaseAIProvider
```

Implementations:

```text id="0v9wlj"
OllamaProvider

OpenAIProvider

AnthropicProvider

GeminiProvider
```

Business logic must use:

```python id="3m5cgj"
AIService
```

Only.

---

# Approved Models

## Primary Model

```text id="mq78pw"
Qwen
```

Reason:

```text id="p9q56r"
Excellent Cost/Performance Ratio

Strong Structured Output

Good Classification Accuracy
```

---

## Secondary Model

```text id="n4m33i"
Gemma
```

---

## Fallback Model

```text id="8dkwcb"
Llama
```

---

# AI Responsibilities

AI may be used for:

```text id="euk14o"
Merchant Recognition

Category Suggestions

Description Suggestions

Insights

Natural Language Queries
```

---

# AI Is Not Allowed To

AI must never:

```text id="z7kzv4"
Create Transactions

Delete Transactions

Modify Balances

Modify Audit Logs

Modify Ownership
```

AI is advisory only.

---

# Merchant Recognition Example

Input:

```text id="s5q0lb"
KA51AJ7604@CNRB
```

Output:

```json id="lfr89g"
{
  "merchant": "BMTC",
  "category": "Transport",
  "confidence": 0.87
}
```

---

# Category Suggestion Example

Input:

```text id="pndr1g"
UPISWIGGY@ICICI
```

Output:

```json id="8gr1z7"
{
  "merchant": "Swiggy",
  "category": "Food",
  "confidence": 0.94
}
```

---

# Description Suggestion Example

Input:

```text id="jxtjlwm"
Merchant: Starbucks

Amount: 120
```

Output:

```json id="5g70xy"
{
  "description": "Coffee Purchase",
  "confidence": 0.91
}
```

---

# AI Output Requirements

Every response must include:

```json id="pcz98r"
{
  "confidence": 0.91
}
```

---

Required fields:

```text id="4hn47l"
Confidence

Model Name

Prompt Version
```

---

# Structured Output Requirement

AI must return:

```text id="tvj9k8"
JSON Only
```

Example:

```json id="go9jgr"
{
  "merchant": "Swiggy",
  "category": "Food",
  "confidence": 0.95
}
```

---

Forbidden:

```text id="xmbjvt"
This looks like food spending.
```

---

# Prompt Versioning

Every prompt must have:

```text id="4r4mcf"
prompt_version
```

Example:

```text id="eiz67v"
merchant_classifier_v1

merchant_classifier_v2

category_classifier_v1
```

Stored with every AI suggestion.

---

# Suggestion Storage

Store all suggestions in:

```text id="yv1fmr"
ai_suggestions
```

Table.

Required fields:

```text id="n8nps8"
suggestion

confidence

model_name

prompt_version
```

---

# AI Learning Model

The platform uses:

```text id="mp3x7f"
Rules
+
Feedback
+
AI
```

Priority:

```text id="i54b9f"
User Rules
↓
Merchant Patterns
↓
AI Suggestions
↓
Unknown
```

AI never overrides user-defined mappings.

---

# Deterministic-First AI Principle

The platform shall always prefer deterministic logic over AI.

Processing priority:

User Rules
↓
Merchant Pattern Rules
↓
Regex Rules
↓
AI Suggestions
↓
Unknown

AI is the final fallback, not the primary classifier.

Reason:

Deterministic rules are:

- Faster
- Cheaper
- Explainable
- Auditable
- Consistent

This is especially important for financial systems.

---

# User Feedback Loop

Example:

AI Suggests:

```text id="n8o2s6"
Transport
```

User Changes To:

```text id="s8hnnp"
Travel
```

Store:

```text id="2s7jz8"
user_feedback
```

Future suggestions improve.

---

# Telegram Integration

AI suggestions may be sent via Telegram.

Example:

```text id="jgh8kb"
Merchant:
KA51AJ7604@CNRB

Suggested:
Transport

Confidence:
82%
```

User may:

```text id="b2m84y"
Accept

Reject

Change Category
```

---

# User Preference Modes

Supported:

```text id="r0bq0z"
Ask Every Time

Ask Low Confidence Only

Never Ask
```

Stored in:

```text id="r5clwk"
user_settings
```

---

# Privacy Requirements

AI processing must never expose:

```text id="n7k9g4"
Passwords

API Keys

JWT Tokens

Secrets
```

---

Sensitive fields should be masked.

Example:

```text id="wd2uh3"
ICICI XXXX0452
```

---

# Failure Handling

AI failures must not block:

```text id="3r4g79"
SMS Processing

Transaction Creation

Balance Updates

Reporting
```

Fallback:

```text id="9hls2y"
Uncategorized

Unknown Merchant
```

---

# Timeout Standards

Maximum synchronous timeout:

```text id="0dd6i2"
5 Seconds
```

After timeout:

```text id="5o3g1i"
Fallback Logic
```

must execute.

---

# Local Deployment

Current Deployment:

```text id="25yn7t"
Laptop
Docker Compose
PostgreSQL
FastAPI
Ollama
```

---

# VPS Deployment

Future:

```text id="49vvvd"
Ubuntu VPS
Docker Compose
PostgreSQL
FastAPI
Ollama
```

---

# SaaS Deployment

Future:

```text id="84jq6t"
Dedicated AI Service

GPU Inference

Provider Selection
```

---

# Cost Analysis

## Ollama

Cost:

```text id="gg6c3r"
₹0 Per Request
```

Hardware cost only.

---

## Cloud Providers

Cost:

```text id="1alryj"
Per Token

Per Request

Monthly Usage
```

---

# Operational Benefits

Advantages:

```text id="xh7r4q"
Privacy

No Token Cost

Offline Capability

No Vendor Lock-In
```

---

# Financial Benefits

Advantages:

```text id="i6zhd7"
Merchant Recognition

Category Automation

Reduced User Effort

Improved Insights
```

---

# Consequences

## Positive Consequences

### Full Data Privacy

Financial data remains local.

---

### Zero AI Usage Cost

Ideal for MVP.

---

### Provider Independence

Future providers can be added.

---

### Better Learning

AI improves through feedback.

---

## Negative Consequences

### Hardware Requirements

Local inference requires resources.

---

### Variable Performance

Dependent on device capabilities.

---

### Model Quality

May not always match premium cloud models.

---

# Rejected Alternatives

## OpenAI

Rejected because:

```text id="tt2h8v"
Recurring Costs

External Data Processing
```

---

## Anthropic

Rejected because:

```text id="xnnj4y"
Usage Costs

Vendor Dependency
```

---

## Gemini

Rejected because:

```text id="e4qvya"
External Processing

Provider Dependency
```

---

## No AI

Rejected because:

```text id="xph7b5"
Missed Automation Opportunities

Poor User Experience
```

---

# Review Criteria

This ADR should be revisited if:

```text id="w8r71f"
Local Inference Becomes Impractical

AI Usage Grows Significantly

GPU Infrastructure Is Introduced

Cloud Providers Offer Significant Advantages
```

---

# Related Documents

```text id="lhq31g"
13-ai_integration_standards.md

06-high_level_design.md

08-api_contracts.md

17-user_management.md
```

---

# Final Decision

Accepted.

The Personal Finance Tracking Platform shall use Ollama as the default AI runtime.

All AI functionality shall operate through a provider abstraction layer, allowing future integration with OpenAI, Anthropic, Gemini, or other providers while maintaining privacy, minimizing cost, and preserving architectural flexibility.
