# P1-04: Containerize Services and Establish Basic CI

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** development team delivering this product incrementally,
- **I want to** run the Link Creation API and Redirection Engine as Docker containers and have every change automatically built and tested,
- **So that** the MVP can be reliably deployed to any environment and regressions are caught automatically before they reach users.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Architecture guidance mandates that all services eventually run as OCI-compliant Docker images on Kubernetes. Phase 1 does not build the Kubernetes/Helm/Terraform layer (that is Phase 2's "Cloud-Native Foundation"), but it must produce correctly containerized services now so Phase 2 can deploy them without rework.
- "Basic CI" in this phase means build + automated test execution only — no deployment automation, GitOps, or multi-environment promotion. Those are explicitly Phase 2 concerns.
- The choice of CI provider (e.g., GitHub Actions, GitLab CI) is left to the team; architecture guidance suggests GitHub Actions/GitLab CI as acceptable defaults.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Services build as containers**
- **Given** the source code for the API & Management Service and the Redirection Engine,
- **When** `docker build` is run for each service,
- **Then** each produces a working image that starts and serves requests when run locally with the required PostgreSQL/Redis dependencies available.

**Scenario 2: Local multi-service startup**
- **Given** the Docker images for both services plus PostgreSQL and Redis,
- **When** a developer starts the full stack locally (e.g., via `docker compose up`),
- **Then** a link can be created via the API and successfully resolved/redirected via the Redirection Engine, end-to-end, using only containerized services.

**Scenario 3: CI runs on every change**
- **Given** a pull request or push to the main branch,
- **When** the CI pipeline is triggered,
- **Then** it builds the Docker images for both services and runs the full automated test suite (unit tests from P1-01, P1-02, P1-03), reporting pass/fail status on the change.

**Scenario 4: CI fails the build on test failure**
- **Given** a code change that breaks an existing test,
- **When** the CI pipeline runs,
- **Then** the pipeline reports a failed status and does not mark the build as successful.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Dockerfile per service (API & Management Service, Redirection Engine); a local Docker Compose setup wiring services to PostgreSQL and Redis for development/testing; a CI pipeline configuration that builds images and runs automated tests on push/PR.
- **Out of Scope:** Kubernetes manifests/Helm charts, Terraform/IaC, GitOps deployment (ArgoCD), observability stack (Prometheus/Grafana/OTel), multi-environment (dev/staging/prod) promotion. These are Phase 2 scope.
- **Upstream Dependencies:** Consumes the application code from P1-01, P1-02, and P1-03 to have something to containerize and test, but the Dockerfile/CI scaffolding itself can be authored in parallel against those stories' in-progress code and finalized once they land.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A (infrastructure/tooling story, no UI).
- **Technical Context:**
  - Per `markdowns/architecture_guidance.md` section 3.1, "All services (API, Redirection Engine, Celery Workers) must be packaged as OCI-compliant Docker images" — Phase 1 covers the API and Redirection Engine; Celery worker containerization begins in Phase 2 alongside the real analytics pipeline.
  - Per section 3.2, CI/CD should use "Automated pipelines (e.g., GitHub Actions, GitLab CI) to build Docker images, run automated tests" — Phase 1 implements only the build+test portion; GitOps-based deployment (ArgoCD) is explicitly Phase 2+.
  - Use a `docker-compose.yml` (or equivalent) for local development to wire the two services to PostgreSQL and Redis containers, mirroring what CI will exercise.
  - Keep images lean (multi-stage builds recommended) since these same images will be the basis for the Kubernetes deployment built in Phase 2.
