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

Local orchestration uses **Podman** (see `markdowns/developer_notes.md` section 4); the compose file
is also compatible with Docker.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install && pre-commit install --hook-type commit-msg
cp .env.example .env

pytest tests/architecture      # structural rules
pytest                         # full suite
black . && isort . && ruff check . && mypy

podman-compose up -d           # local stack (postgres, redis, api, redirect, consumer)
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).
