# `agent_debate.api` — the HTTP API

A thin [FastAPI](https://fastapi.tiangolo.com/) shell over the
[`core`](../core/README.md) SDK (PRD §6): start a debate, poll its status/result,
and stream live events over [Server-Sent Events](https://developer.mozilla.org/docs/Web/API/Server-sent_events).
The [UI](../ui/README.md) is a browser frontend over this API.

> Distribution `agent_debate_api` · importable module `agent_debate.api` ·
> console script **`agent-debate-api`**. Depends on
> [`agent_debate.core`](../core/README.md) and
> [`agent_debate.log`](../log/README.md).

## Install / run

```bash
uv sync                          # from the repo root
uv run agent-debate-api          # serves Uvicorn on the config-driven host/port
# equivalent:
uv run python -m agent_debate.api
# or point Uvicorn at the app factory directly:
uv run uvicorn agent_debate.api.app:app
```

The bind address is config-driven (`API_HOST` / `API_PORT`, defaults
`127.0.0.1:8000`); the entrypoint lives in
[`__main__.py`](src/agent_debate/api/__main__.py). A real run needs
`ANTHROPIC_API_KEY` (a synchronous preflight rejects a misconfigured request with
a clear error before scheduling a doomed run).

## Endpoints

Defined in [`debate_routes.py`](src/agent_debate/api/debate_routes.py); interactive
docs at `GET /docs` once running.

| Method & path | Purpose |
| --- | --- |
| `POST /debates` | Start a debate. Body `{ "topic": "...", ...overrides }`. Returns `{run_id, status}` (HTTP 201) immediately; the run proceeds in the background. |
| `GET /debates/{run_id}` | Return the run's `status` and, once complete, the full `DebateResult` (or `error`). Unknown id → 404. |
| `GET /debates/{run_id}/stream` | Stream the run's ordered, typed events as SSE (`text/event-stream`): one `event:`/`data:` record per `LogEvent`, live for a running debate and a faithful replay for a finished one, terminated by a `done` sentinel. Unknown id → 404. |

The app factory `create_app()` and module-level `app` are re-exported from
[`__init__.py`](src/agent_debate/api/__init__.py); `set_stream_runner` /
`set_debate_runner` / `set_preflight` are the seams tests use to inject a stub
runner (no key, no network).

## Minimal example

```bash
# 1. Start a debate; capture the run_id.
curl -s -X POST http://localhost:8000/debates \
  -H 'content-type: application/json' \
  -d '{"topic": "Should cities ban cars downtown?"}'
# -> {"run_id": "ab12...", "status": "running"}

# 2. Watch it live (SSE), or poll the final result.
curl -N http://localhost:8000/debates/ab12.../stream
curl -s http://localhost:8000/debates/ab12...
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `API_HOST` | Uvicorn bind host. | `127.0.0.1` |
| `API_PORT` | Uvicorn bind port. | `8000` |
| `ANTHROPIC_API_KEY` | Provider key (preflight-validated). | — |

Debate behaviour (rounds, models, …) comes from the same SDK
[`Settings`](../core/src/agent_debate/core/settings.py); CORS/validation is wired
in [`app.py`](src/agent_debate/api/app.py) / [`errors.py`](src/agent_debate/api/errors.py).

## Develop & test

```bash
uv run pytest packages/api --cov
```

## See also

- [Root README](../../README.md) · [SDK](../core/README.md) ·
  [CLI](../cli/README.md) · [UI](../ui/README.md) · [LOG](../log/README.md)
- [`docs/PRD.md`](../../docs/PRD.md) §6 — surfaces.
