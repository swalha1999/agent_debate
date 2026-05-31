# `agent_debate.ui` — the web UI

A lightweight web frontend over the [`api`](../api/README.md) surface (PRD §6):
enter a topic, watch the Pro and Con transcripts stream round by round in
separate panels, see the moderator's nudges and the system log, and read the
final verdict. The page is plain HTML/CSS/JS served by a small
[FastAPI](https://fastapi.tiangolo.com/) app — no build step.

> Distribution `agent_debate_ui` · importable module `agent_debate.ui` ·
> console script **`agent-debate-ui`**. Depends on
> [`agent_debate.core`](../core/README.md) and
> [`agent_debate.log`](../log/README.md).

## Install / run

The UI talks to a running [API](../api/README.md), so start both:

```bash
uv sync                          # from the repo root
uv run agent-debate-api          # terminal 1: the API on http://localhost:8000
uv run agent-debate-ui           # terminal 2: the UI on http://localhost:5173
# equivalents for the UI:
uv run python -m agent_debate.ui
uv run uvicorn agent_debate.ui.app:app
```

Open the UI URL, type a topic, press **Start debate**, and watch it stream.

## Routes

Defined in [`app.py`](src/agent_debate/ui/app.py):

| Method & path | Purpose |
| --- | --- |
| `GET /` | The single-page app (topic input + Pro/Con panels + moderator/system-log + verdict). The config-driven API base URL is injected into the served HTML. |
| `GET /config` | JSON `{api_base_url}` — the API origin the page's JS posts the debate to. |
| `GET /static/*` | The static frontend assets (`index.html`, CSS, JS). |

The page's JS calls the API's `POST /debates`, then consumes
`GET /debates/{id}/stream` (SSE) to render events live, and reads the verdict
fields (`winner`, `converged`, `summary`, token totals) from the completed
`DebateResult`.

## Configuration

Config-driven (the UI never hard-codes where the API lives) — see
[`config.py`](src/agent_debate/ui/config.py):

| Variable | Purpose | Default |
| --- | --- | --- |
| `UI_HOST` | Uvicorn bind host. | `127.0.0.1` |
| `UI_PORT` | Uvicorn bind port. | `5173` |
| `API_BASE_URL` | API origin the browser-side JS calls. | `http://localhost:8000` |

## Develop & test

The HTML/CSS/JS are static assets (outside pytest coverage); the serving routes
and the UI↔API contract are tested at the `TestClient` level — no browser or key:

```bash
uv run pytest packages/ui --cov
```

## See also

- [`docs/UI.md`](../../docs/UI.md) — annotated layout diagrams + UX walkthrough
  (understand the interface without running it).
- [Root README](../../README.md) · [SDK](../core/README.md) ·
  [CLI](../cli/README.md) · [API](../api/README.md) · [LOG](../log/README.md)
