# UI — Interface documentation

> Guideline §10.2 deliverable: this documents the **web UI** so a reader can
> understand the interface **without running it**. Because real browser
> screenshots are not reproducible in this headless/CI environment, the screens
> are shown as **annotated ASCII layout diagrams** (callouts numbered `(1)`,
> `(2)`, …) keyed to the *real* element ids in
> [`index.html`](../packages/ui/src/agent_debate/ui/static/index.html), plus a
> step-by-step **UX walkthrough**. The diagrams are an honest, accurate
> substitute for screenshots: every id below exists in the live DOM, and the
> `test_ui_docs.py` test cross-checks that.

## 1. Overview

The UI is a **thin web client over the API** (PRD §6). It is a single static
page — [`index.html`](../packages/ui/src/agent_debate/ui/static/index.html) +
[`app.js`](../packages/ui/src/agent_debate/ui/static/app.js) +
[`style.css`](../packages/ui/src/agent_debate/ui/static/style.css) — served by a
small FastAPI app
([`app.py`](../packages/ui/src/agent_debate/ui/app.py)). It holds **no
debate logic of its own**; it only:

1. `POST`s the topic to the API's `POST /debates` to start a run, then
2. opens a **Server-Sent-Events** stream (`GET /debates/{id}/stream`) and renders
   each event live, then
3. on the stream's `done` sentinel, `GET`s `/debates/{id}` once for the final
   `DebateResult` and renders the **verdict**.

The API origin is **config-driven** (never hard-coded): the server injects
`API_BASE_URL` into the `<meta name="api-base-url">` tag, and `app.js` reads it
via `apiBaseUrl()`. See [§5 Config](#5-config).

Each streamed SSE event's name **is** its `LogEvent.event_type`, and `app.js`
routes by type into three separate panels (so no single view is overloaded —
PRD §6):

| `event_type`                        | Routed to            | DOM list id          |
| ----------------------------------- | -------------------- | -------------------- |
| `message`                           | Debate transcript    | `transcript-pro` / `transcript-con` |
| `nudge`                             | Moderator actions    | `controller-actions` |
| `system` / `tool_call` / `timeout` / `retry` | System log  | `system-log-list`    |

Usability is assessed against **Nielsen's 10 heuristics** — see
[task 11.6](../.building_tasks_logs/11.6-nielsen-heuristics.json) — and called
out inline below.

## 2. Annotated layout diagrams

### 2a. Topic-input / start screen

The first thing a user sees: a heading, a one-line help hint, the topic field,
and the Start button. Status / panels / verdict are all `hidden` initially.

```
┌──────────────────────────────────────────────────────────────┐
│  agent_debate                                          (h1)   │
│  Enter a topic and start a multi-agent debate.   .lead        │
│                                                               │
│  ┌─ id="help" ──────────────────────────────────────────┐(1) │
│  │ A Pro and a Con agent debate your topic while a        │   │
│  │ Moderator keeps them on track. Type a topic and press  │   │
│  │ Enter (or Start)…                                      │   │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Debate topic                              (label for=topic)  │
│  ┌─ id="topic" ─────────────────────────────────────────┐(2) │
│  │ e.g. Should cities ban private cars?     (placeholder)│   │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌ id="start" ──────┐  ┌ id="new-debate" (hidden) ──────┐     │
│  │  Start debate    │(3)│  New debate  [.secondary]      │(4) │
│  └──────────────────┘  └────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

- **(1) `id="help"`** — minimalist help line (Nielsen #10: help & docs).
- **(2) `id="topic"`** — the topic `<input>` (`required`, autofocus on reset).
- **(3) `id="start"`** — submit button. **Disabled while the topic is empty**
  (Nielsen #5, error prevention) and **while a debate is running**.
- **(4) `id="new-debate"`** — a `.secondary` reset button, `hidden` until a
  debate starts (Nielsen #3, user control & freedom).

### 2b. Live debate view (status + three panels)

Once Start is pressed, the **status line** and the three-panel grid appear.

```
┌─ id="status" role=status aria-live=polite ───────────────────┐(5)
│  ● Debating — round 2          (status__dot pulses while live) │
└───────────────────────────────────────────────────────────────┘
┌─ id="result" ────────────────────────────────────────────────┐(6)
│  Debate started — run id: 7f3a…   (or a friendly error string) │
└───────────────────────────────────────────────────────────────┘
┌─ id="panels" (grid) ─────────────────────────────────────────┐
│ ┌─ id="transcript" PANEL 1 ──────────────────────────────┐(7) │
│ │  Debate transcript                                      │   │
│ │  ┌ Pro ──────────────┐    ┌ Con ──────────────┐          │   │
│ │  │ id="transcript-pro"│    │ id="transcript-con"│         │   │
│ │  │  Round 1 — PRO …   │    │  Round 1 — CON …   │         │   │
│ │  └────────────────────┘    └────────────────────┘        │   │
│ └──────────────────────────────────────────────────────────┘   │
│ ┌─ id="controller-panel" PANEL 2 ─┐ ┌─ id="system-log" PANEL 3 ┐│
│ │ Moderator actions / nudges  (8) │ │ System log           (9) ││
│ │ ┌ id="controller-actions" ────┐ │ │ ┌ id="system-log-list" ┐ ││
│ │ │ Round 2 — nudge — con …      │ │ │ │ Round 1 — tool_call …│ ││
│ │ └──────────────────────────────┘ │ │ └──────────────────────┘ ││
│ └──────────────────────────────────┘ └──────────────────────────┘│
└───────────────────────────────────────────────────────────────┘
```

- **(5) `id="status"`** — always-honest status line (Nielsen #1): cycles
  `Connecting…` → `Debating — round N` → `Complete` / `Error`. The
  `status__dot` pulses while connecting/debating (paused under
  `prefers-reduced-motion`). The **round counter** comes from the latest
  `message` event's `round`.
- **(6) `id="result"`** — the run-id / friendly status or error message.
- **(7) PANEL 1 `id="transcript"`** — Pro vs Con columns (`transcript-pro`,
  `transcript-con`), each `message` event appended as a `.turn` styled by side.
- **(8) PANEL 2 `id="controller-panel"`** — `nudge` events → the moderator's
  private corrections, kept **out** of the transcript (`controller-actions`).
- **(9) PANEL 3 `id="system-log"`** — technical events
  (`system`/`tool_call`/`timeout`/`retry`) → `system-log-list`.

### 2c. Verdict view

On the `done` sentinel, the panel `id="verdict"` (hidden until then) is filled
from the final `DebateResult`.

```
┌─ id="verdict" aria-live=polite ──────────────────────────────┐
│  Verdict                                          (heading)   │
│  id="verdict-winner"     →  Winner: Pro              (10)     │
│  id="verdict-converged"  →  The agents converged / agreed.(11)│
│  id="verdict-summary"    →  <debate summary / rationale>  (12)│
│  ┌ id="verdict-tokens" (dl) ──────────────────────────┐ (13) │
│  │  Total tokens    1234                                │     │
│  │  Input tokens     800                                │     │
│  │  Output tokens    434                                │     │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

- **(10) `verdict-winner`** — `result.verdict.winner` mapped to **Pro / Con /
  Tie**.
- **(11) `verdict-converged`** — whether `result.verdict.converged` is true.
- **(12) `verdict-summary`** — `result.verdict.summary` (or `rationale`).
- **(13) `verdict-tokens`** — `result.totals` token counts (cost is Epic 15;
  **tokens** are shown now).

## 3. UX walkthrough

The step-by-step user journey (no need to run it to follow along):

1. **Land on the start screen.** The `id="help"` hint explains the Pro / Con /
   Moderator model. The `id="start"` button is **disabled** because `id="topic"`
   is empty (Nielsen #5).
2. **Type a topic.** As soon as the topic is non-empty, Start enables
   (`syncStartEnabled` in `app.js`).
3. **Press Enter or click Start.** `app.js` disables Start (so you can't
   double-submit), shows `id="new-debate"`, sets status `Connecting…`, and
   `POST`s the topic to `POST {API_BASE_URL}/debates`.
4. **Watch it run.** The UI opens the SSE stream and:
   - streams Pro/Con turns into the **transcript** panel
     (`transcript-pro` / `transcript-con`);
   - shows **moderator nudges** in the controller panel (`controller-actions`);
   - logs **system events** in the system log (`system-log-list`);
   - keeps the **status** line honest — `Debating — round N` with the live dot.
5. **See the verdict.** On `done`, status flips to `Complete`, the UI fetches
   the final result and reveals the **verdict** panel — **winner**, whether the
   agents **converged**, the **summary**, and **token** totals.
6. **Start over.** Click `id="new-debate"` (`resetDebate`) to clear all panels,
   the verdict, and the status, refocus the topic field, and run another debate
   — without reloading (Nielsen #3).

**Error recovery (Nielsen #9).** If the `POST` fails, or the SSE connection
drops **before** `done`, the UI shows a friendly retry message in `id="result"`
(e.g. *"Lost the live connection. Something went wrong. Please try again."*) and
sets status `Error` — never a raw stack trace.

**RTL support (task 11.5).** The page is authored with CSS **logical
properties** only (`margin/padding-inline`, `inset-inline`, `text-align: start`,
`border-inline-start`) — never `left`/`right`. Flipping `<html dir="rtl">`
mirrors the entire layout (panels, transcript columns, status bar) correctly.

**Nielsen heuristics addressed** (full detail in
[task 11.6](../.building_tasks_logs/11.6-nielsen-heuristics.json)): #1 visible
system status (status line + round + live dot), #3 user control & freedom (New
debate reset), #4 consistency, #5 error prevention (disabled Start), #8
minimalist design, #9 error recovery (friendly messages), #10 help & docs
(the help hint).

## 4. Accessibility notes

- `id="status"` is a `role="status"` `aria-live="polite"` region; the panels and
  `id="result"` are also `aria-live="polite"`, so screen readers announce new
  turns, nudges, and the verdict as they arrive.
- Every section carries an `aria-label` (e.g. *Debate transcript*, *System log*,
  *Debate verdict*).
- Focus styling uses a visible `:focus-visible` outline; the live-dot animation
  is disabled under `prefers-reduced-motion`.

## 5. Config

The UI is fully **config-driven** (no hard-coded values — guideline §7.2). All
values come from
[`config.py`](../packages/ui/src/agent_debate/ui/config.py):

| Env var        | Purpose                                   | Default                 |
| -------------- | ----------------------------------------- | ----------------------- |
| `API_BASE_URL` | Origin the browser JS calls for the API.  | `http://localhost:8000` |
| `UI_HOST`      | Bind host for the UI server.              | `127.0.0.1`             |
| `UI_PORT`      | Bind port for the UI server.              | `5173`                  |

`API_BASE_URL` is injected into the served HTML (the `__API_BASE_URL__`
placeholder in the `<meta name="api-base-url">` tag) and is also exposed at
`GET /config` as JSON.

### Running it (for someone who *does* want to run it)

```bash
# Start the API first (defaults to http://localhost:8000)
uv run agent-debate-api        # or: uv run uvicorn agent_debate.api.app:app

# Then the UI (defaults to http://127.0.0.1:5173)
uv run agent-debate-ui         # console script

# Equivalents:
uv run python -m agent_debate.ui
uv run uvicorn agent_debate.ui.app:app --host 127.0.0.1 --port 5173

# Point the UI at a non-default API origin:
API_BASE_URL=https://api.example.com uv run agent-debate-ui
```

Open the UI host/port in a browser, enter a topic, and press **Start**.
