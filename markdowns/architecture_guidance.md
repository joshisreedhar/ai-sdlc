# System Architecture Context: URL Shortener & Analytics Platform

## 1. System Overview
**Project Goal:** Build a scalable, low-latency URL redirection service with advanced tracking, customizable QR codes, and routing rules.
**Target Stack:** Python (FastAPI, Celery), PostgreSQL, Redis.

## 2. Architecture Components
### 2.1. API & Management Service
- **Framework:** FastAPI (Async REST API).
- **Responsibilities:**
  - Link creation (shortening, custom aliases/domains).
  - QR Code Generation (via `segno` or `qrcode`, stored in S3/Object Storage).
  - Link-in-Bio page serving (Jinja2 templates or JSON API for frontend).
  - Bulk operations and Zapier/API integrations.
  - User management and security controls (passwords, expiration dates).

### 2.2. Redirection Engine
- **Framework:** FastAPI (Optimized for low latency).
- **Responsibilities:**
  - Receive short URL requests.
  - Lookup destination in Redis (Cache-first approach). Fallback to PostgreSQL.
  - Evaluate Routing Rules (Geo-targeting, Device-based, Expiration, Password-gate).
  - Execute HTTP 301/302 Redirect.
  - Publish click event to Message Broker (non-blocking).
  - **Agent Instruction:** Do not block the redirect response to process analytics.

### 2.3. Analytics Async Pipeline
- **Framework:** Celery workers + Redis/RabbitMQ Broker.
- **Responsibilities:**
  - Ingest click events from the Message Broker.
  - Parse `User-Agent` (Device, Browser, OS).
  - Resolve IP to Location (GeoIP integration).
  - Write processed metrics to Analytics Database.

## 4. Data Storage Strategy
- **Primary Relational DB:** PostgreSQL.
  - Stores Users, Links (long, short, aliases), Link Metadata, Routing Rules.
- **Cache & Message Broker:** Redis.
  - Caches `short_hash -> long_url` mappings.
  - Handles API Rate Limiting.
  - Acts as a message broker for Celery.
- **Analytics Data Store:** PostgreSQL (Partitioned) OR ClickHouse (Preferred for high volume).
  - Stores raw click events and aggregated time-series metrics.

## 5. Agent Implementation Rules & Constraints
- **API Design:** Adhere to OpenAPI standards. Use Pydantic models for strict validation.
- **Performance:** Redirection endpoint must strictly separate read logic from write logic.
- **Security Constraint 1:** Implement IP and bot filtering middleware.
- **Security Constraint 2:** Ensure password-protected links redirect to an intermediary auth page, not the destination.
- **Conversion Tracking Workflow:** If tracking pixels (Meta, Google Ads) are attached, serve an intermediary HTML page to fire pixels before triggering a JavaScript-based redirection.

content = """# System Architecture Context: URL Shortener & Analytics Platform

## 3. Cloud-Native & Agnostic Infrastructure
### 3.1. Compute & Orchestration
- **Containerization:** All services (API, Redirection Engine, Celery Workers) must be packaged as OCI-compliant Docker images.
- **Orchestration:** Kubernetes (K8s) is the target deployment environment. The system must be deployable to any managed service (AWS EKS, GCP GKE, Azure AKS) or on-premises cluster.
- **Configuration Management:** Utilize Helm charts or Kustomize for defining deployment states across environments (Dev, Staging, Prod).

### 3.2. Infrastructure as Code (IaC) & CI/CD
- **IaC:** Use Terraform or OpenTofu to provision the underlying networking, managed databases, and K8s clusters across any Cloud Service Provider (CSP).
- **CI/CD:** Automated pipelines (e.g., GitHub Actions, GitLab CI) to build Docker images, run automated tests, and deploy via GitOps tools (e.g., ArgoCD).

### 3.3. Observability & Telemetry
- **Metrics & Monitoring:** Expose `/metrics` endpoints for Prometheus scraping. Use Grafana for visualization.
- **Distributed Tracing:** Integrate OpenTelemetry (OTel) into FastAPI and Celery to trace request paths and latency bottlenecks without vendor lock-in.
- **Logging:** Output centralized, structured JSON logging to `stdout`/`stderr` (collected by Fluentd/Logstash).

