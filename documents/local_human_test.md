# Local Manual Test Guide

Quick reference for running the stack locally and poking at the data it
produces. See `documents/developer_human_contex.md` for the "why."

## 1. Start the stack

Full stack (Postgres, Redis, Management API, Redirection Engine, Click
Consumer) — matches CI/prod images:

```bash
podman compose up -d --build
podman compose ps
```

Faster inner loop (Postgres + Redis in containers, API/Redirection run
directly via uvicorn, no Click Consumer):

```bash
scripts/run_local.sh
# scripts/run_local.sh stop   # to tear down
```

If you used `run_local.sh` and also want the Click Consumer running:

```bash
python -m urlshortener.apps.click_consumer.main
```

## 2. Smoke test

```bash
curl -X POST http://localhost:8001/links -H 'Content-Type: application/json' \
  -d '{"long_url": "https://www.anthropic.com/"}'
# => {"short_code":"P1SjNLb","short_url":"http://localhost:8001/P1SjNLb"}

curl -i http://localhost:8002/P1SjNLb        # 302 Found, Location: https://www.anthropic.com/
curl -i http://localhost:8002/doesnotexist   # 404 Not Found
```

## 3. PostgreSQL — the system of record

Log in:

```bash
# via podman compose
podman compose exec postgres psql -U urlshortener -d urlshortener

# via run_local.sh
podman exec -it us-pg psql -U urlshortener -d urlshortener
```

Useful queries once inside `psql`:

```sql
\dt                                        -- list tables
SELECT * FROM links ORDER BY created_at DESC LIMIT 10;
SELECT * FROM links WHERE short_code = 'P1SjNLb';
SELECT count(*) FROM links;
```

One-liner without an interactive session:

```bash
podman compose exec postgres psql -U urlshortener -d urlshortener \
  -c "SELECT short_code, long_url, created_at FROM links ORDER BY created_at DESC LIMIT 10;"
```

## 4. Redis — cache + click-event stream

Log in:

```bash
# via podman compose
podman compose exec redis redis-cli

# via run_local.sh
podman exec -it us-redis redis-cli
```

**Link cache** (key format `link:v1:{short_code}`, JSON value, TTL applied on
first redirect after a cache miss — not on link creation):

```
KEYS link:v1:*
GET link:v1:P1SjNLb
TTL link:v1:P1SjNLb
```

**Click event stream** (`clicks.v1`, consumer group `analytics`):

```
XLEN clicks.v1                       -- how many events are buffered
XRANGE clicks.v1 - +                 -- view every event on the stream
XINFO GROUPS clicks.v1               -- consumer group + last-delivered-id
XINFO CONSUMERS clicks.v1 analytics  -- individual consumer processes
```

Each entry's `payload` field is the JSON-encoded `ClickEvent` (short_code,
occurred_at, client_ip, user_agent, referrer).

## 5. Click Consumer — confirm it processed an event

The consumer only logs (Phase 1 has no analytics persistence yet). Tail its
output:

```bash
# via podman compose
podman compose logs -f click_consumer

# via run_local.sh (consumer run manually per step 1)
# it logs to stdout in whatever terminal you started it in
```

Look for a `click_event_received` line with the `short_code` you just hit.

## 6. Tear down

```bash
podman compose down -v      # full stack, including the Postgres volume
# or
scripts/run_local.sh stop   # run_local.sh path
```
