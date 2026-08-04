# P4-02: Custom Domain Onboarding & Verification

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** brand-conscious customer,
- **I want to** connect my own domain (e.g., `brand.com`) to the platform,
- **So that** my shortened links display my brand's domain instead of the platform's shared default domain.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Custom domains are a top-tier branding differentiator for paid and organic campaigns alike. This story covers domain registration, DNS-based ownership verification, and extending the redirection path to route by `Host` header. The exact verification challenge mechanics (TXT vs. CNAME, polling vs. on-demand check) are open for technical negotiation, provided ownership is provably verified before a domain becomes usable.
- Must remain compatible with the Phase 2 cloud-agnostic, multi-CSP infrastructure — no dependency on a single cloud provider's DNS or certificate service.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Add domain & receive verification instructions**
- **Given** I own a domain and want to use it for branded links
- **When** I submit the domain name via the domain management API
- **Then** the system generates a unique DNS verification token and returns setup instructions (required TXT record and CNAME target)

**Scenario 2: Successful verification**
- **Given** I have added the required DNS TXT record at my DNS provider
- **When** the system's verification check runs (on-demand trigger or scheduled poll)
- **Then** the domain status transitions from `pending` to `verified` and becomes eligible for link creation

**Scenario 3: Redirection via custom domain**
- **Given** a verified custom domain `brand.com` with an active link at alias `promo`
- **When** a visitor requests `https://brand.com/promo`
- **Then** the Redirection Engine resolves the `(domain, alias)` pair and issues the correct 301/302 redirect to the destination URL

**Scenario 4: Unverified domain blocks link creation**
- **Given** a domain is still in `pending` verification status
- **When** a user attempts to create a link on that domain
- **Then** the API rejects the request with a `400` error indicating verification must complete first

**Scenario 5: Verification failure is surfaced**
- **Given** a domain is `pending` and the required DNS record is missing or incorrect
- **When** a verification check runs
- **Then** the domain remains `pending` (or moves to `failed` after repeated attempts) and the API exposes the current status and reason to the user

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Domain registration API, DNS TXT-record verification flow, domain status lifecycle (`pending` / `verified` / `failed`), `Host`-header-based routing in the Redirection Engine, TLS certificate provisioning trigger for verified domains.
- **Out of Scope:** Automatic DNS record creation on the user's behalf, multi-region DNS failover, wildcard subdomain support.
- **Upstream Dependencies:** Phase 2 Kubernetes/cloud-native foundation (ingress controller, cert-manager for TLS) and Phase 1 redirection engine.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** None provided; domain management is an API-first workflow, admin UI screens to be designed in a follow-up.
- **Technical Context:** New `domains` table (`id`, `owner_id`, `hostname`, `verification_token`, `status`, `verified_at`); Redirection Engine reads the `Host` header to scope the alias lookup to `(domain_id, alias) -> destination` in Redis; TLS provisioned via cert-manager HTTP-01/DNS-01 challenge against the Phase 2 Helm/K8s ingress (architecture guidance Section 3.1); verification checks can run as a periodic Celery task reusing the Phase 2 async pipeline infrastructure (Section 2.3).

---
