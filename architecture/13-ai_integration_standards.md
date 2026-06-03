# 13-ai_integration_standards.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: AI Integration Standards

Architecture Style: AI-Assisted Financial System

Primary AI Runtime: Ollama

Preferred Models: Qwen, Gemma, Llama

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines how Artificial Intelligence is integrated into the Personal Finance Tracking Platform.

The primary goal is:

```text
AI-Assisted
NOT
AI-Controlled
```

The system must remain deterministic and auditable.

Financial records must never depend entirely on AI decisions.

AI exists to:

* Reduce manual effort
* Improve categorization
* Improve merchant recognition
* Improve user experience
* Generate insights
* Learn user behavior

without compromising:

* Data integrity
* Auditability
* Security
* Explainability

---

# 2. AI Philosophy

## Core Principle

AI may suggest.

AI may recommend.

AI may explain.

AI may learn.

AI may never directly modify financial records without approval.

---

## Examples

Allowed:

```text
Suggest category
Suggest merchant
Suggest description
Generate reports
Generate insights
```

Not Allowed:

```text
Delete transactions
Modify balances
Create income records
Transfer money
Update audit logs
```

---

# 3. AI Architecture

```text
User
 ↓
AI Service
 ↓
Prompt Builder
 ↓
Ollama
 ↓
Response Validator
 ↓
Suggestion Store
 ↓
User Approval
 ↓
Business Logic
```

---

# 4. AI Module Structure

```text
backend/src/ai/

├── prompts/
│
├── models/
│
├── services/
│
├── validators/
│
├── adapters/
│
├── memory/
│
├── schemas/
│
├── tests/
│
└── README.md
```

---

# 5. AI Deployment Strategy

## MVP

Local AI

Selected:

```text
Ollama
```

Reasons:

* Free
* Local execution
* Privacy
* No token costs
* No vendor lock-in

---

## Future SaaS

Possible:

```text
OpenAI
Anthropic
Gemini
Azure OpenAI
```

Through adapter pattern.

---

# 6. Supported Models

## Primary

```text
Qwen 3
```

---

## Secondary

```text
Gemma
```

---

## Fallback

```text
Llama
```

---

# 7. AI Use Cases

---

## Use Case 1

Merchant Recognition

Example:

```text
KA51AJ7604@CNRB
```

AI Suggestion:

```text
BMTC Bus Travel
```

Confidence:

```text
88%
```

---

## Use Case 2

Category Suggestion

Input:

```text
SmartQ
```

Output:

```text
Food
```

---

## Use Case 3

Description Suggestion

Input:

```text
Rs. 120 debit at Starbucks
```

Output:

```text
Coffee Purchase
```

---

## Use Case 4

Monthly Insights

Example:

```text
Food spending increased 18%
compared to last month.
```

---

## Use Case 5

Budget Recommendations

Example:

```text
Reduce restaurant spending
by ₹2,000/month to reach
your savings goal.
```

---

## Use Case 6

Natural Language Queries

Future.

Example:

```text
How much did I spend on food
last month?
```

---

## Use Case 7

Merchant Pattern Discovery

AI may discover:

```text
KA51AJ*
```

belongs to:

```text
BMTC
```

after repeated user feedback.

---

# 8. AI Prohibited Actions

AI must never:

```text
Create Transactions
Delete Transactions
Modify Transactions
Modify Balances
Modify Audit Logs
Modify Ownership
Modify Accounts
```

---

# 9. AI Approval Model

Three levels exist.

---

## Level 1

Fully Automatic

Allowed:

```text
Suggestions Only
```

---

## Level 2

User Approval Required

Examples:

```text
New Merchant Rule
New Category Rule
```

---

## Level 3

Forbidden

Examples:

```text
Financial Record Mutation
```

---

# 10. AI Confidence Standards

Every AI result must include:

```json
{
  "confidence": 0.91
}
```

---

## Confidence Thresholds

### High

```text
90%+
```

System may auto-suggest.

---

### Medium

```text
70% - 89%
```

User confirmation recommended.

---

### Low

```text
Below 70%
```

No automatic usage.

---

# 11. Merchant Learning Design

User feedback drives learning.

---

## Example

Transaction:

```text
KA51AJ7604@CNRB
```

User says:

```text
Bus Travel
```

Store:

```text
merchant_pattern
```

---

Future:

```text
KA43HJ2938@CNRB
```

AI recognizes similarity.

Suggest:

```text
Bus Travel
```

---

# 12. Hybrid Learning Strategy

The platform uses:

```text
Rule Engine
+
AI
```

---

Priority:

```text
User Rules
↓
Merchant Patterns
↓
AI Suggestions
↓
Unknown
```

AI never overrides user-defined rules.

---

# 13. AI Memory Design

AI memory is not conversational memory.

Store only:

```text
Merchant Patterns
Category Corrections
Description Corrections
Preference Rules
```

---

Never store:

```text
Passwords
Tokens
Secrets
```

---

# 14. AI Suggestion Storage

Create table:

```text
ai_suggestions
```

Purpose:

Store every AI suggestion.

---

Columns:

```text
id

user_id

entity_type

entity_id

suggestion

confidence

model_name

prompt_version

created_at
```

---

# 15. AI Prompt Standards

Every prompt must:

```text
Be deterministic
Be versioned
Be auditable
```

---

Store:

```text
prompt_version
```

with each suggestion.

---

# 16. Prompt Versioning

Example:

```text
merchant_classifier_v1

merchant_classifier_v2

category_classifier_v1
```

---

Never overwrite prompt definitions.

---

# 17. Prompt Template Standards

Template:

```text
SYSTEM

Financial classification assistant.

USER

Transaction:

Merchant:
Amount:
Direction:

TASK

Suggest category.
Return JSON only.
```

---

# 18. Structured Outputs

AI must return JSON only.

Example:

```json
{
  "merchant": "SmartQ",
  "category": "Food",
  "confidence": 0.94
}
```

---

Forbidden:

```text
I think this might be food...
```

---

# 19. Output Validation

All AI outputs must pass validation.

Validate:

```text
JSON Structure
Category Exists
Confidence Exists
```

---

Invalid outputs are discarded.

---

# 20. AI Service Layer

Only:

```text
ai/services/
```

may call AI models.

---

Forbidden:

```python
transaction_service.py

calling ollama directly
```

---

Use:

```python
AIService
```

abstraction.

---

# 21. AI Adapter Pattern

Required.

Interface:

```python
BaseAIProvider
```

---

Implementations:

```python
OllamaProvider

OpenAIProvider

AnthropicProvider
```

---

Allows future migration.

---

# 22. AI Failure Handling

AI failures must never block:

```text
SMS Processing
Transaction Creation
Balance Updates
Reporting
```

---

If AI fails:

```text
Continue Processing
```

---

Example:

```text
Category = Uncategorized
```

---

# 23. AI Timeout Standards

Maximum:

```text
5 Seconds
```

for synchronous requests.

---

After timeout:

```text
Fallback
```

---

# 24. AI Rate Limiting

Future SaaS.

Limits:

```text
Requests Per Minute
Tokens Per Minute
Cost Per User
```

---

# 25. AI Cost Control

Local Ollama:

```text
₹0
```

Runtime Cost.

---

Cloud Models:

Track:

```text
Prompt Tokens
Completion Tokens
Monthly Cost
```

---

# 26. AI Security Rules

Never send:

```text
Passwords
JWT Tokens
API Keys
Secrets
```

to AI.

---

Mask sensitive fields.

Example:

```text
Account: ******0452
```

---

# 27. AI Audit Requirements

Store:

```text
Prompt Version
Model Name
Suggestion
Confidence
Timestamp
```

---

For explainability.

---

# 28. Explainability Standards

User must be able to see:

```text
Why category was suggested
```

Example:

```text
Merchant matched previous
SmartQ transactions.
```

---

# 29. AI Feedback Loop

User accepts suggestion:

```text
Positive Feedback
```

User rejects suggestion:

```text
Negative Feedback
```

Store both.

---

# 30. User Preference Learning

User may choose:

```text
Ask Every Time

Ask Only Low Confidence

Never Ask
```

Stored in:

```text
user_settings
```

---

# 31. Telegram AI Workflow

Transaction Created

↓

AI Suggestion Generated

↓

Telegram Message

```text
₹120 SmartQ

Suggested:
Food

Reply:
1 Accept
2 Change
```

↓

User Response

↓

Learning Engine

---

# 32. AI Insight Engine

Future feature.

Examples:

```text
Top Spending Categories

Monthly Trends

Savings Opportunities

Recurring Expenses

Unusual Transactions
```

---

# 33. Anomaly Detection

Future.

Examples:

```text
Spending 3x normal amount

Unknown Merchant

Unusual Transaction Time
```

---

AI may flag.

Never block.

---

# 34. AI Testing Standards

Test:

```text
Prompt Output
Validation
Confidence Handling
Fallback Logic
```

---

Every prompt version requires tests.

---

# 35. AI Monitoring

Track:

```text
Total Suggestions

Accepted Suggestions

Rejected Suggestions

Accuracy %

Response Time
```

---

# 36. AI Accuracy Metrics

Measure:

```text
Merchant Accuracy

Category Accuracy

Description Accuracy
```

---

Goal:

```text
85%+
```

before enabling broader automation.

---

# 37. AI Database Objects

Required Tables:

```text
ai_suggestions

user_feedback

merchant_patterns
```

---

Future Tables:

```text
ai_models

prompt_versions

ai_metrics
```

---

# 38. OpenClaw Integration Standards

OpenClaw may be used as:

```text
AI Agent Runtime
```

Not:

```text
Source of Truth
```

---

OpenClaw may:

```text
Generate Insights
Run Workflows
Answer Queries
```

---

OpenClaw must not:

```text
Mutate Financial Records Directly
```

---

# 39. Future Agent Architecture

Future:

```text
Finance Agent

Reporting Agent

Budget Agent

Investment Agent
```

All operate through APIs.

Never direct database writes.

---

# 40. AI Agent Implementation Rules

AI coding agents must:

* Use Ollama by default.
* Use provider abstraction.
* Use structured JSON outputs.
* Store suggestions separately.
* Track confidence.
* Log prompt versions.
* Support future providers.

AI coding agents must not:

* Hardcode prompts.
* Skip validation.
* Modify financial records.
* Bypass service layer.
* Store secrets in prompts.

---

# 41. Recommended AI Roadmap

Phase 1

```text
Merchant Recognition
Category Suggestions
Telegram Suggestions
```

Phase 2

```text
Learning Engine
Pattern Discovery
Budget Suggestions
```

Phase 3

```text
Natural Language Queries
Anomaly Detection
Financial Insights
```

Phase 4

```text
Finance Agent
OpenClaw Agent Integration
Multi-Agent System
```

---

# 42. Approval

Status: Approved

This document is the authoritative AI Integration Standard for the Personal Finance Tracking Platform.

All AI modules, Ollama integrations, OpenClaw integrations, prompt systems, learning engines, feedback systems, and future AI agents must comply with this specification.
