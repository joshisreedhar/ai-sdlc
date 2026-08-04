# P5-05: Repeatable Environment Provisioning with Terraform/OpenTofu

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** platform operator/DevOps engineer,
- **I want to** provision networking, managed databases, and Kubernetes clusters from version-controlled Terraform/OpenTofu code,
- **So that** I can stand up or reproduce Dev, Staging, and Prod environments on any supported cloud provider quickly, consistently, and without manual console work.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- As the platform grows into automation-driven, higher-traffic usage (bulk creation, public API, webhook fan-out), manual infrastructure setup becomes a scaling and reliability risk; this story front-loads the IaC investment the architecture guidance calls for.
- The architecture guidance is explicit: "Use Terraform or OpenTofu to provision the underlying networking, managed databases, and K8s clusters across any Cloud Service Provider (CSP)." This story implements that as versioned, reviewable code rather than manually clicked-through infrastructure.
- Which specific CSP(s) get a fully validated module first (AWS, GCP, or Azure) is negotiable and can be driven by whichever environment the team needs to stand up next; the module interface itself should be provider-agnostic.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done". Use BDD (Behavior-Driven Development) Given/When/Then format when possible.*

**Scenario 1: Provision a full environment from scratch**
- **Given** an empty target cloud account/subscription and a chosen environment name (e.g., "staging")
- **When** an engineer runs `terraform apply` (or `tofu apply`) against the environment's variable file
- **Then** the networking (VPC/subnets), managed PostgreSQL instance, managed Redis instance, and Kubernetes cluster are created and reachable, matching the architecture guidance's component list

**Scenario 2: Re-running apply is idempotent**
- **Given** an environment that was already successfully provisioned
- **When** `apply` is run again with no code or variable changes
- **Then** Terraform/OpenTofu reports zero resource changes (no drift, no accidental recreation)

**Scenario 3: Same modules target a second CSP**
- **Given** the provider-agnostic module interface (networking, database, cluster)
- **When** a new environment is configured to target a second supported CSP by swapping the provider-specific module implementation and variables only
- **Then** an equivalent environment (same logical topology: network, managed DB, managed Redis, K8s cluster) is provisioned without changes to the calling/root module's interface

**Scenario 4: Safe teardown**
- **Given** a non-production environment provisioned by these modules
- **When** an engineer runs `terraform destroy` (or `tofu destroy`) for that environment
- **Then** all resources created by the modules are removed cleanly, with production environments protected by a documented safeguard (e.g., deletion protection flag or separate state/backend) against accidental destruction

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Terraform/OpenTofu modules for networking, managed PostgreSQL, managed Redis, and a managed Kubernetes cluster; per-environment variable files (Dev/Staging/Prod); remote state backend configuration; module validated end-to-end on at least one CSP.
- **Out of Scope:** CI/CD pipeline wiring and GitOps deployment (ArgoCD) — explicitly deferred to Phase 6 hardening; Helm chart/Kustomize application-layer manifests (tracked separately from infra provisioning); full multi-CSP validation for every provider (only the module interface must be provider-agnostic in this story; additional CSP implementations can follow incrementally).
- **Upstream Dependencies:** None — this is infrastructure work independent of the application-layer stories (P5-01 through P5-04) and can be developed in parallel by a different work stream.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — infrastructure code; deliverable is the module repository structure and README, not a UI.
- **Technical Context:** Follow the "Cloud-Native & Agnostic Infrastructure" section of the architecture guidance: containerized services target Kubernetes (EKS/GKE/AKS or on-prem), so the cluster module must output standard kubeconfig-compatible credentials for later Helm/Kustomize deployment. Structure modules as `modules/network`, `modules/database`, `modules/cache`, `modules/k8s-cluster` with a thin per-CSP root module (e.g., `envs/aws/staging`, `envs/gcp/staging`) so the calling interface (variables/outputs) stays identical across providers. Use a remote backend (e.g., S3+DynamoDB, GCS, or Terraform Cloud) for state locking, and separate state files per environment to reduce blast radius.
