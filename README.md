# ai-sdlc — URL Shortener & Analytics Platform

An agentic SDLC example. The `.claude/agents/` directory holds the Technical Manager, Architect,
Developer, and QA agents; `artifacts/` holds what they produce; `src/` holds the product they build.

## Where things live

| Path | Contents |
| --- | --- |
| `markdowns/` | Human inputs: requirements, architecture guidance, developer notes |
| `artifacts/development_plan/<phase>/` | Phase summaries and user stories (Technical Manager) |
| `artifacts/architecture/` | `overall_architecture.md` plus per-phase C4, diagrams, and ArchUnit specs (Architect) |
| `src/urlshortener/` | The application package |
| `tests/architecture/` | Executable structural rules — the ArchUnit equivalent |
| `deploy/docker/` | Per-service Dockerfiles |
| `docker-compose.yml` | Local multi-service stack (Postgres, Redis, all three app processes) |
| `.github/workflows/ci.yml` | Lint, type-check, test and image-build CI pipeline |
| `migrations/` | Alembic migration history |

**Start here if you are implementing a phase:** read
`artifacts/architecture/<phase>/c4_architecture.md`, honour the
`<!-- PHASE: ... START/END -->` markers, and keep `pytest tests/architecture` green.

## Application structure

A modular monolith of bounded contexts, deployed as three processes:

```
src/urlshortener/
├── shared_kernel/      settings, structured logging, Clock, base errors
├── contracts/          versioned cross-process schemas (ClickEvent)
├── link_management/    write side  -> Management API
├── redirection/        read/hot path -> Redirection Engine
├── analytics/          click ingestion -> Click Consumer
└── apps/               composition roots (management_api, redirection_engine, click_consumer)
```

Each context is layered `api -> application -> domain`, with `infrastructure` depending inward on
`domain` only. Those boundaries are enforced by tests, not by convention — see
`artifacts/architecture/phase_1_mvp/archunit_specs.md`.

## Development

Local orchestration uses **Podman** (see `markdowns/developer_notes.md` section 4).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install && pre-commit install --hook-type commit-msg
cp .env.example .env

pytest tests/architecture      # structural rules
pytest                         # unit + architecture + integration (excludes e2e)
pytest -m e2e tests/e2e        # full docker/podman-compose round trip (needs a container runtime)
black . && isort . && ruff check . && mypy
```

### Running the app locally

Two ways to run the full stack (Management API, Redirection Engine, Click Consumer,
PostgreSQL, Redis):

**Containers (recommended - matches CI and the production images):**

```bash
podman compose up -d --build     # or: docker compose up -d --build
podman compose down -v           # tear down, including the Postgres volume
```

**Manual dev script** (`scripts/run_local.sh`) - starts Postgres + Redis via Podman and
runs the Management API and Redirection Engine directly with `uvicorn` (no Click
Consumer; useful for fast local iteration without a container rebuild each time):

```bash
scripts/run_local.sh           # starts Postgres + Redis (Podman), runs migrations,
                                # and starts the Management API (:8001) and
                                # Redirection Engine (:8002)
scripts/run_local.sh stop      # stops the app processes and the containers
```

Either way:

```bash
curl -X POST http://localhost:8001/links -H 'Content-Type: application/json' \
  -d '{"long_url": "https://www.anthropic.com/"}'
# => {"short_code":"...","short_url":"..."}

curl -i http://localhost:8002/<short_code>
# => 302 Found, Location: https://www.anthropic.com/
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).
