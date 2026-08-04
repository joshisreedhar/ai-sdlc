# PH2-01: Deploy Core Services to Kubernetes via Helm/Kustomize

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** platform operator,
- **I want to** deploy the API, Redirection Engine, and Celery workers to Kubernetes using a repeatable Helm chart (or Kustomize overlays),
- **So that** the platform can scale each component independently, recover from pod failures automatically, and be promoted consistently across Dev, Staging, and Prod without manual server configuration.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Phase 1 shipped the API and Redirection Engine as runnable services (likely via docker-compose or a single host). Phase 2 needs to prove the architecture guidance's cloud-native mandate: OCI-compliant containers orchestrated by Kubernetes, deployable to any managed CSP (EKS/GKE/AKS) or on-prem cluster.
- The team should decide between a single umbrella Helm chart with sub-charts per service versus separate charts, and between Helm and Kustomize — either satisfies the architecture guidance, so this is open for negotiation.
- This story only covers the K8s workload manifests and environment-specific configuration; it does NOT include Terraform/OpenTofu cluster provisioning or GitOps/ArgoCD pipeline wiring, which are deferred to a later infrastructure-hardening phase.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Fresh install stands up the full stack**
- **Given** a clean Kubernetes namespace and the Phase 2 Helm chart (or Kustomize base),
- **When** an operator runs `helm install` (or `kubectl apply -k`) with the Dev values file,
- **Then** Deployments for the API, Redirection Engine, and Celery workers, plus their Services, ConfigMaps, and Secrets, are created and all pods reach `Ready` status within a defined timeout.

**Scenario 2: Services scale independently**
- **Given** the stack is running,
- **When** an operator scales the Redirection Engine Deployment replica count up (e.g., via `kubectl scale` or a values override) without touching the API or Celery worker Deployments,
- **Then** only the Redirection Engine pod count changes, and traffic continues to be served without downtime.

**Scenario 3: Failed pod self-heals**
- **Given** the stack is running with liveness/readiness probes configured,
- **When** a pod for any of the three services is killed or becomes unresponsive,
- **Then** Kubernetes automatically restarts or reschedules the pod, and the readiness probe gates it from receiving traffic until healthy.

**Scenario 4: Environment promotion via values**
- **Given** the same chart/base,
- **When** it is applied with the Staging values file instead of Dev,
- **Then** environment-specific config (replica counts, resource limits, DB/Redis connection strings, broker URL) is injected via ConfigMaps/Secrets without modifying chart templates.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Dockerfiles (if not already produced in Phase 1) for the three services; Helm chart or Kustomize overlays; Deployment/Service/ConfigMap/Secret manifests; liveness/readiness probes; resource requests/limits; Dev and Staging values files.
- **Out of Scope:** Terraform/OpenTofu provisioning of the underlying K8s cluster or managed databases; CI/CD pipeline automation and ArgoCD GitOps sync (later phase); autoscaling policies (HPA) beyond manual replica configuration; production values/secrets management (e.g., Vault/Sealed Secrets) — a basic Secret resource is sufficient for this story.
- **Upstream Dependencies:** Phase 1 API and Redirection Engine services exist and run as containerizable applications with externalized configuration (env vars for DB/Redis connection).

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — infrastructure story, no UI.
- **Technical Context:** Per `architecture_guidance.md` section 3.1, all services must be packaged as OCI-compliant Docker images and orchestrated via Kubernetes, with Helm or Kustomize defining deployment state across Dev/Staging/Prod. The API and Redirection Engine are both FastAPI apps (can share a base image with different entrypoints); Celery workers need the same application code plus the broker (Redis) connection. Redis itself may be deployed via a lightweight in-cluster chart (e.g., Bitnami Redis) for Dev, with a note that Staging/Prod should point to a managed Redis instance provisioned outside this story's scope.
