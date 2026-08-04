# PHASE6-02: GitOps Continuous Delivery Across Dev, Staging & Prod

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** platform/DevOps engineer,
- **I want to** promote a single, version-controlled deployment artifact through Dev, Staging, and Prod Kubernetes clusters via an automated GitOps pipeline,
- **So that** every release is consistent, auditable, and reversible, and the team can ship changes to end users quickly without manual, error-prone deployment steps.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Phase 2 established the cloud-native foundation (Docker images, Kubernetes, Helm/Kustomize). Phase 6 closes the loop by automating how changes actually reach each environment, rather than relying on manual `kubectl`/`helm` invocations.
- The architecture guidance calls for GitOps tooling (ArgoCD) driven by CI pipelines (GitHub Actions/GitLab CI) that build and test images before ArgoCD syncs the desired state to each cluster.
- The specific branching/promotion strategy (e.g., environment branches vs. environment directories/overlays, manual approval gates for Prod) is open for team negotiation; this story fixes the outcome (automated, declarative, auditable promotion) not the exact workflow mechanics.
- This is an internal-facing/platform story; the "user" is the engineering team, and the value delivered is delivery speed and safety, which indirectly protects end-user experience (fewer bad deploys, faster fixes).

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: CI builds and publishes a versioned artifact**
- **Given** a merged change to the main branch of a service repository (API, Redirection Engine, or Celery workers),
- **When** the CI pipeline runs,
- **Then** it builds an OCI-compliant Docker image, runs the automated test suite, and, on success, publishes a uniquely tagged image to the container registry and updates the corresponding environment manifest (Helm values/Kustomize overlay) in the GitOps config repository.

**Scenario 2: ArgoCD auto-syncs Dev on manifest change**
- **Given** the Dev environment overlay in the GitOps config repository has been updated with a new image tag,
- **When** ArgoCD detects the drift between the desired state (Git) and the live Dev cluster state,
- **Then** ArgoCD automatically syncs the Dev cluster to match Git within its configured polling/refresh interval, and the ArgoCD UI/API reflects the application as "Synced" and "Healthy".

**Scenario 3: Promotion to Staging and Prod requires an explicit, auditable step**
- **Given** a change has been verified as healthy in Dev,
- **When** an engineer promotes the same image tag to the Staging overlay (and subsequently Prod) via a pull request against the GitOps config repository,
- **Then** the promotion is recorded as a Git commit/PR (providing an audit trail of who promoted what and when), and ArgoCD syncs the target cluster only after that manifest change is merged.

**Scenario 4: Rollback via Git revert**
- **Given** a Prod deployment has been identified as faulty,
- **When** an engineer reverts the corresponding commit in the GitOps config repository,
- **Then** ArgoCD detects the reverted desired state and resyncs Prod back to the previous known-good image tag without requiring manual cluster access.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** CI pipeline updates to build/test/publish images and bump GitOps manifests; ArgoCD installation and Application definitions for Dev, Staging, and Prod for each service; documented promotion workflow (PR-based) between environments.
- **Out of Scope:** Full progressive delivery/canary or blue-green rollout strategies (Argo Rollouts), automated performance/load testing gates, multi-region/multi-cluster failover — these are candidates for future hardening work beyond this roadmap.
- **Upstream Dependencies:** Requires the Kubernetes clusters, Helm/Kustomize manifests, and containerized services already established in Phase 2. Independent of the other Phase 6 stories (Link-in-Bio, dashboards, tracing/logging) and can be delivered on its own.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A (infrastructure/process story).
- **Technical Context:**
  - Per architecture guidance section 3.2, CI/CD pipelines (GitHub Actions/GitLab CI) build images and run tests; ArgoCD performs the actual GitOps-based deployment.
  - Assumes a separate "GitOps config" repository (or a dedicated `deploy/` path) containing per-environment Helm values or Kustomize overlays for API, Redirection Engine, and Celery workers.
  - Dev can be configured for ArgoCD auto-sync; Staging and Prod should require the manifest-bump PR to be merged before ArgoCD syncs, giving a natural manual approval gate without needing a separate approval tool.
  - Reuse existing Terraform/OpenTofu-provisioned clusters from Phase 2; this story only touches the application deployment layer, not cluster provisioning.
