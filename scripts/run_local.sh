#!/usr/bin/env bash
# Run the URL Shortener platform locally with Podman, without building containers.
#
# Starts Postgres + Redis containers, applies the Alembic migration, and runs the
# Management API (:8001) and Redirection Engine (:8002) directly with uvicorn - useful
# for fast local iteration without a container rebuild each time. The Click Consumer
# isn't started by this script; run it separately with
# `python -m urlshortener.apps.click_consumer.main`, or use the full containerized
# stack instead: `podman compose up -d --build` (see docker-compose.yml).
#
# Usage:
#   scripts/run_local.sh          # start everything (safe to re-run)
#   scripts/run_local.sh stop     # stop the app processes and the containers

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

RUN_DIR=".run"
PG_CONTAINER=us-pg
REDIS_CONTAINER=us-redis
MGMT_PORT=8001
REDIRECT_PORT=8002

ensure_container() {
  local name=$1 image=$2
  shift 2
  if podman container exists "$name"; then
    if [ "$(podman inspect -f '{{.State.Running}}' "$name")" != "true" ]; then
      echo "Starting existing container $name..."
      podman start "$name" >/dev/null
    fi
  else
    echo "Creating container $name..."
    podman run -d --name "$name" "$@" "$image" >/dev/null
  fi
}

stop_all() {
  echo "Stopping app processes..."
  for pidfile in "$RUN_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    kill "$(cat "$pidfile")" 2>/dev/null || true
    rm -f "$pidfile"
  done
  echo "Stopping containers..."
  podman stop "$PG_CONTAINER" "$REDIS_CONTAINER" >/dev/null 2>&1 || true
  echo "Done."
}

if [ "${1:-}" = "stop" ]; then
  stop_all
  exit 0
fi

start_service() {
  local name=$1 module=$2 port=$3
  local pidfile="$RUN_DIR/$name.pid"
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name already running on :$port (pid $(cat "$pidfile"))"
    return
  fi
  echo "Starting $name on :$port..."
  nohup uvicorn "$module" --port "$port" > "$RUN_DIR/$name.log" 2>&1 &
  echo $! > "$pidfile"
}

mkdir -p "$RUN_DIR"

ensure_container "$PG_CONTAINER" docker.io/library/postgres:16-alpine \
  -p 5432:5432 \
  -e POSTGRES_USER=urlshortener -e POSTGRES_PASSWORD=urlshortener -e POSTGRES_DB=urlshortener

ensure_container "$REDIS_CONTAINER" docker.io/library/redis:7-alpine \
  -p 6379:6379

if [ ! -d .venv ]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -e ".[dev]"

[ -f .env ] || cp .env.example .env

echo "Waiting for Postgres to accept connections..."
for _ in $(seq 1 30); do
  podman exec "$PG_CONTAINER" pg_isready -U urlshortener >/dev/null 2>&1 && break
  sleep 1
done

echo "Applying migrations..."
alembic upgrade head

start_service management_api urlshortener.apps.management_api.main:app "$MGMT_PORT"
start_service redirection_engine urlshortener.apps.redirection_engine.main:app "$REDIRECT_PORT"

sleep 2
cat <<EOF

Running:
  Management API       http://localhost:$MGMT_PORT   (logs: $RUN_DIR/management_api.log)
  Redirection Engine    http://localhost:$REDIRECT_PORT   (logs: $RUN_DIR/redirection_engine.log)

Try it:
  curl -X POST http://localhost:$MGMT_PORT/links -H 'Content-Type: application/json' \\
    -d '{"long_url": "https://www.anthropic.com/"}'
  curl -i http://localhost:$REDIRECT_PORT/<short_code>

Stop everything:
  scripts/run_local.sh stop
EOF
