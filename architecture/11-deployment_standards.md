# 11-deployment_standards.md

# Personal Finance Tracking Platform

Version: 1.0

Status: Approved

Document Type: Deployment Standards

Architecture Style: Modular Monolith

Framework: FastAPI

Database: PostgreSQL

Container Platform: Docker

Orchestration: Docker Compose

Last Updated: 2026-06-02

---

# 1. Purpose

This document defines the deployment standards for the Personal Finance Tracking Platform.

It specifies:

* Deployment environments
* Docker standards
* Docker Compose standards
* Environment configuration
* VPS deployment
* CI/CD requirements
* Backup strategy
* Monitoring strategy
* Future cloud deployment standards

This document is the authoritative source for:

* Local Development
* Testing Environments
* VPS Hosting
* Future Cloud Hosting
* CI/CD Pipelines

---

# 2. Deployment Philosophy

The platform follows:

```text
Local First
↓
Single VPS
↓
Managed Cloud
↓
Kubernetes
```

The architecture must scale naturally through these stages without redesign.

---

# 3. Deployment Environments

The following environments must exist.

---

## Local Development

Purpose:

Developer development environment.

Infrastructure:

```text
Docker Compose
PostgreSQL
FastAPI
```

Expected Users:

```text
1 Developer
```

---

## Local Production

Purpose:

Personal finance tracking system.

Infrastructure:

```text
Laptop
Docker Compose
PostgreSQL
FastAPI
Telegram Bot
```

Expected Users:

```text
1 User
```

---

## VPS Production

Purpose:

Always-on deployment.

Infrastructure:

```text
Ubuntu VPS
Docker Compose
PostgreSQL
Nginx
Let's Encrypt
FastAPI
```

Expected Users:

```text
1-100 Users
```

---

## Future SaaS Production

Infrastructure:

```text
Managed PostgreSQL
Redis
Load Balancer
Multiple App Instances
Monitoring Stack
```

Expected Users:

```text
1000+
```

---

# 4. Deployment Architecture

## MVP Local Deployment

```text
+----------------------+
| Android Phone        |
+----------+-----------+
           |
           v
+----------------------+
| MacroDroid           |
+----------+-----------+
           |
           v
+----------------------+
| FastAPI Backend      |
+----------+-----------+
           |
           v
+----------------------+
| PostgreSQL           |
+----------+-----------+
           |
           v
+----------------------+
| Telegram Bot         |
+----------------------+
```

---

## VPS Deployment

```text
+----------------------+
| Internet             |
+----------+-----------+
           |
           v
+----------------------+
| Nginx Reverse Proxy  |
+----------+-----------+
           |
           v
+----------------------+
| FastAPI Container    |
+----------+-----------+
           |
           v
+----------------------+
| PostgreSQL Container |
+----------------------+
```

---

# 5. Docker Standards

## Required Containers

MVP:

```text
backend
postgres
```

Optional:

```text
telegram-worker
adminer
pgadmin
```

---

## Container Naming

Format:

```text
finance-{service}
```

Examples:

```text
finance-backend
finance-postgres
finance-telegram-worker
```

---

## Container Restart Policy

Required:

```yaml
restart: unless-stopped
```

---

## Container User

Containers must not run as:

```text
root
```

Use dedicated non-root user.

---

# 6. Docker Compose Standards

File:

```text
docker-compose.yml
```

Required Services:

```yaml
services:
  backend:
  postgres:
```

---

## Network

Dedicated network:

```yaml
networks:
  finance-network:
```

---

## Volumes

Persistent volumes required.

```yaml
volumes:
  postgres-data:
```

---

## Environment Files

Use:

```text
.env
```

Never hardcode secrets.

---

# 7. Environment Variables

## Required Variables

Backend:

```env
APP_ENV=production

JWT_SECRET=

DATABASE_URL=

INGEST_API_KEY=

TELEGRAM_BOT_TOKEN=

TELEGRAM_WEBHOOK_SECRET=
```

---

## Database Variables

```env
POSTGRES_DB=finance

POSTGRES_USER=finance_app

POSTGRES_PASSWORD=
```

---

## Optional Variables

```env
LOG_LEVEL=INFO

ENABLE_AI=false

ENABLE_TELEGRAM=true
```

---

# 8. Environment Separation

Each environment must have separate:

```text
Database
Secrets
Configuration
Logs
```

---

## Example

Development:

```env
APP_ENV=development
```

Production:

```env
APP_ENV=production
```

---

# 9. Configuration Management

Configuration must come from:

```text
Environment Variables
```

Only.

Forbidden:

```python
JWT_SECRET = "abc123"
```

---

# 10. Reverse Proxy Standards

Selected:

```text
Nginx
```

---

## Responsibilities

Nginx must handle:

```text
HTTPS
TLS
Compression
Rate Limiting
Request Logging
```

---

## Backend Exposure

FastAPI must not be exposed directly.

Only Nginx should be public.

---

# 11. HTTPS Standards

Production requires:

```text
HTTPS Only
```

---

## Certificate Provider

Selected:

```text
Let's Encrypt
```

---

## Renewal

Automatic renewal required.

---

# 12. Domain Standards

MVP:

```text
Optional
```

Examples:

```text
finance.example.com
api.finance.example.com
```

---

# 13. Database Deployment Standards

Selected:

```text
PostgreSQL
```

---

## PostgreSQL Version

Minimum:

```text
15
```

Recommended:

```text
16+
```

---

## Database Storage

Use persistent volume.

Never store database inside container filesystem.

---

## Production User

Do not use:

```text
postgres
```

Create:

```text
finance_app_user
```

---

# 14. Migration Standards

Tool:

```text
Alembic
```

---

## Rule

All schema changes must use migrations.

Never manually change production schema.

---

## Deployment Order

```text
Start PostgreSQL
↓
Run Alembic Migration
↓
Start FastAPI
```

---

# 15. Backup Standards

Backups are mandatory.

---

## Backup Frequency

Recommended:

```text
Daily
```

---

## Retention

Recommended:

```text
30 Days
```

---

## Backup Types

Required:

```text
Full Backup
```

Future:

```text
Incremental Backup
```

---

## Backup Verification

Backups must be tested.

Rule:

```text
Backup Exists
≠
Backup Works
```

---

# 16. Restore Standards

The platform must support:

```text
Point-in-Time Recovery
```

Future.

---

## Recovery Testing

Recommended:

```text
Monthly
```

---

# 17. Logging Standards

All containers must write logs to:

```text
stdout
stderr
```

---

## Log Format

Structured JSON preferred.

Example:

```json
{
  "timestamp": "",
  "service": "",
  "request_id": "",
  "correlation_id": ""
}
```

---

# 18. Monitoring Standards

MVP:

Basic health checks.

Future:

```text
Prometheus
Grafana
OpenTelemetry
```

---

## Health Endpoint

Required:

```http
GET /api/v1/health
```

---

## Health Requirements

Verify:

```text
API
Database
Telegram Connectivity
```

---

# 19. Alerting Standards

Future SaaS.

Examples:

```text
Database Down
Migration Failed
Backup Failed
High Error Rate
```

---

# 20. CI/CD Standards

Selected:

```text
GitHub Actions
```

Reason:

* Free for MVP
* GitHub Native
* Easy Integration

---

## Pipeline Stages

```text
Lint
↓
Tests
↓
Build
↓
Security Scan
↓
Docker Build
↓
Deploy
```

---

# 21. Git Standards

Repository:

```text
GitHub
```

---

## Branches

Required:

```text
main
develop
```

Feature Branches:

```text
feature/*
```

Bug Fixes:

```text
bugfix/*
```

Hot Fixes:

```text
hotfix/*
```

---

## Protected Branch

```text
main
```

Must require PR.

---

# 22. Release Standards

Versioning:

```text
Semantic Versioning
```

Format:

```text
MAJOR.MINOR.PATCH
```

Example:

```text
1.0.0
```

---

# 23. VPS Standards

Recommended VPS Specs.

---

## MVP

```text
2 vCPU
4 GB RAM
50 GB SSD
```

Examples:

* Hetzner
* DigitalOcean
* Contabo
* Linode

---

## Growth

```text
4 vCPU
8 GB RAM
100 GB SSD
```

---

# 24. Local Laptop Deployment Standards

Supported.

---

## Workflow

```text
Laptop On
↓
Docker Compose Up
↓
System Active
```

---

## Batch Mode Support

If laptop is offline:

```text
SMS Stored On Phone
↓
MacroDroid Batch Export
↓
Backend Processes Missing Messages
```

Supports migration from:

```text
Local
→ VPS
```

without data model changes.

---

# 25. Future Cloud Deployment

Potential Providers:

```text
AWS
GCP
Azure
```

---

## Managed Services

Future:

```text
Cloud SQL
RDS
Azure Database
```

---

# 26. Future Kubernetes Deployment

Not required for MVP.

Future Components:

```text
Ingress
Secrets
Deployments
Services
ConfigMaps
Persistent Volumes
```

---

# 27. Deployment Security Requirements

Production must enforce:

```text
HTTPS
JWT
Secrets in Environment Variables
Ownership Validation
Audit Logging
```

---

## Forbidden

```text
Hardcoded Secrets
Open PostgreSQL Ports
Root Containers
```

---

# 28. Rollback Strategy

Every deployment must support rollback.

---

## Method

```text
Previous Docker Image
↓
Redeploy
```

---

## Database

Use:

```text
Alembic Downgrade
```

Only if safe.

---

# 29. Disaster Recovery

Critical Assets:

```text
Database
Environment Variables
Telegram Bot Configuration
```

---

## Recovery Objectives

Target:

```text
RPO < 24 Hours
RTO < 4 Hours
```

---

# 30. AI Agent Deployment Rules

AI coding agents must:

* Generate Dockerfiles.
* Generate docker-compose.yml.
* Generate Alembic migrations.
* Generate GitHub Actions pipeline.
* Use environment variables.
* Use non-root containers.
* Implement health checks.

AI coding agents must not:

* Hardcode secrets.
* Skip migrations.
* Expose PostgreSQL publicly.
* Require Kubernetes for MVP.
* Use BigQuery as primary transactional database.

---

# 31. Recommended Deployment Path

Phase 1

```text
Laptop
Docker Compose
PostgreSQL
```

Cost:

```text
₹0
```

---

Phase 2

```text
Ubuntu VPS
Docker Compose
Nginx
HTTPS
```

Cost:

```text
₹300-₹800/month
```

---

Phase 3

```text
Multi-User SaaS
Managed PostgreSQL
Redis
Monitoring
```

Cost:

Depends on usage.

---

# 32. Approval

Status: Approved

This document is the authoritative deployment standard for the Personal Finance Tracking Platform.

All Docker configurations, deployment scripts, CI/CD pipelines, VPS infrastructure, cloud deployments, and future scaling strategies must comply with these standards.
