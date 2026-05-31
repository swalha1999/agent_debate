# `agent_debate.log` — the LOG package

The **shared logging surface** (PRD §5.1, §5.8): structured logging, the typed
event schema, cost/token accounting fields, and secret redaction. Built on
[structlog](https://www.structlog.org/) + [Pydantic v2](https://docs.pydantic.dev/).
Every other package depends on LOG; it depends on nothing in the workspace.

> Distribution `agent_debate_log` · importable module `agent_debate.log`.

## Install / import

```bash
uv sync                          # from the repo root
```

```python
from agent_debate.log import get_logger, log_event, configure, LogEvent
```

## Public API

Re-exported from [`__init__.py`](src/agent_debate/log/__init__.py):

| Symbol | What it is |
| --- | --- |
| `configure(run_id, runs_dir=...)` | The idempotent structlog setup factory. Wires the two PRD §5.8 sinks — a pretty console renderer + a per-run JSONL file at `<runs_dir>/<run_id>.jsonl` — with redaction in the chain. |
| `get_logger(run_id, runs_dir=...)` | Returns a structlog logger pre-bound with `run_id` (calls `configure`); the ergonomic entrypoint. |
| `log_event(*, run_id, agent, event_type, round=None, payload=None, tokens=None, latency_ms=None)` | Build + **validate** a `LogEvent`, then emit it as one JSONL line. An unknown `event_type` or missing field raises before anything is written. |
| `bind_round(n)` / `bind_context(**fields)` / `clear_context()` | Push fields (e.g. the current `round`) into structlog contextvars so they propagate to later emissions. |
| `LogEvent` / `EVENT_TYPES` / `EventType` | The typed event schema and the strict allowed `event_type` set. |
| `redact_event` / `make_redactor` | The redaction processor: redacts secret-like values (by key name and by value pattern, recursively) and truncates oversized strings, so secrets reach neither sink. |
| `emit_event` / `EventSink` / `CollectingSink` | Live event-stream sinks (used by the engine's `.stream()`). |
| `DEFAULT_RUNS_DIR` | Default directory for per-run JSONL files (`"runs"`). |

## Minimal example

```python
from agent_debate.log import get_logger, log_event, bind_round

# A logger bound to a run; the JSONL sink at runs/<run_id>.jsonl is wired.
log = get_logger("demo-run")
log.info("debate_run_started", topic="Should cities ban cars downtown?")

# Validated structured events with run_id/round bound:
bind_round(1)
log_event(
    run_id="demo-run",
    agent="pro",
    event_type="message",
    payload={"content": "Cars dominate scarce public space."},
    tokens=42,
    latency_ms=380.0,
)
```

Each run's events land in one JSONL file (`runs/<run_id>.jsonl`) plus a pretty
console rendering. No external API calls happen here, so the Epic-13 API
gatekeeper does not apply — all I/O flows through LOG's own sinks.

## Develop & test

```bash
uv run pytest packages/log --cov
```

## See also

- [Root README](../../README.md) · [SDK](../core/README.md) ·
  [CLI](../cli/README.md) · [API](../api/README.md) · [UI](../ui/README.md)
- [`docs/PRD.md`](../../docs/PRD.md) §5.8 — logging & observability.
