# Service Monitor

Monitoring of HTTP services: a FastAPI server probes registered endpoints on a schedule, stores every check in PostgreSQL
and serves an API; a desktop client (Tkinter) shows the state, uptime and history of each target.

## Quick start (Docker)

```bash
cp .env.example .env                     # set POSTGRES_PASSWORD (and API_TOKEN if the API must be closed)
docker compose up -d --build --wait      # db, server :8000, demo services billing :9101 and catalog :9102
python client/monitor_client.py          # desktop client; --server URL, --token TOKEN
```

Register targets from the client form or via API:

```bash
curl -X POST localhost:8000/api/targets -H 'Content-Type: application/json' \
  -d '{"name":"billing","url":"http://billing:9101/","interval_seconds":5}'
curl localhost:9101/toggle               # make a demo service answer 503 and watch it go DOWN
```

## API

| Method | Path | What |
|---|---|---|
| GET | `/api/health` | liveness, no token |
| GET / POST | `/api/targets` | list / register a target (409 on duplicate name, 422 on invalid URL) |
| DELETE | `/api/targets/{id}` | remove a target with its history |
| GET | `/api/status` | state UP/DOWN/PENDING, last latency, uptime % per target |
| GET | `/api/targets/{id}/history?limit=N` | last N checks (1–200) |
| GET | `/api/audit?limit=N` | work log: who created/deleted what |

Interactive docs: `http://localhost:8000/docs`.

## Development

```bash
pip install -r requirements-dev.txt
pytest -q && flake8 --max-line-length=120 server client demo tests
cd server && DATABASE_URL=sqlite+aiosqlite:///./monitor.db uvicorn app.main:app --reload
```

## Security note

The server fetches the URLs users register — that is its job, and also an SSRF vector. Keep the API on a trusted
network or set `API_TOKEN` so that only the client holding the token can add targets.
