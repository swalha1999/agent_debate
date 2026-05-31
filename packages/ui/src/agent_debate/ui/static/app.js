// Topic-input page + live transcript (tasks 11.1/11.2, issues #73/#74).
//
// 11.1: on submit, POST the topic to the API's POST /debates and show the
// returned run_id. 11.2: then open a Server-Sent-Events stream to the API's
// GET /debates/{id}/stream and render the Pro vs Con MESSAGE transcript LIVE
// as events arrive, closing on the `done` sentinel.
//
// 11.3: lay the stream out across THREE SEPARATE panels (don't overload one
// view, PRD §6). Each SSE event's name IS its LogEvent.event_type, so we route
// by event_type: `message` → debate transcript, `nudge` → controller actions,
// and the technical events (`system`/`tool_call`/`timeout`/`retry`) → system
// log. The verdict view is task 11.4 and is intentionally left out here.
//
// The API base URL is config-driven, NOT hard-coded: the server injects it into
// the <meta name="api-base-url"> tag (and also exposes GET /config). Both the
// POST and the EventSource URL are built from apiBaseUrl().

"use strict";

const META_NAME = "api-base-url";

// Side identifiers (match the engine's DebateSide values "pro"/"con") used to
// route a message into the correct column. Single source of truth, no inline
// literals scattered through the render code.
const SIDES = { pro: "pro", con: "con" };

// SSE event_type names routed to the SYSTEM LOG panel (single source of truth):
// the technical/system event feed, kept out of the transcript + controller view.
const SYSTEM_EVENT_TYPES = ["system", "tool_call", "timeout", "retry"];

function apiBaseUrl() {
  const meta = document.querySelector(`meta[name="${META_NAME}"]`);
  return ((meta && meta.content) || "").replace(/\/+$/, "");
}

function streamUrl(runId) {
  return `${apiBaseUrl()}/debates/${encodeURIComponent(runId)}/stream`;
}

// The final result endpoint (no `/stream` suffix): GET /debates/{id} returns the
// DebateState whose `result` is the completed DebateResult — verdict + token/cost
// totals together (11.4). The verdict view reads it once on the `done` sentinel.
function resultUrl(runId) {
  return `${apiBaseUrl()}/debates/${encodeURIComponent(runId)}`;
}

function setResult(el, message, isError) {
  el.textContent = message;
  el.classList.toggle("error", Boolean(isError));
}

async function startDebate(topic) {
  const response = await fetch(`${apiBaseUrl()}/debates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
  if (!response.ok) {
    throw new Error(`API responded ${response.status}`);
  }
  return response.json();
}

// --- Live transcript rendering (11.2) ------------------------------------

// Ids of every panel list, cleared together when a new debate starts.
const PANEL_LIST_IDS = [
  "transcript-pro",
  "transcript-con",
  "controller-actions",
  "system-log-list",
];

function clearPanels() {
  for (const id of PANEL_LIST_IDS) {
    const list = document.getElementById(id);
    if (list) {
      list.replaceChildren();
    }
  }
}

// Build one <li> turn for a message event, styled by side (Pro vs Con distinct).
function renderTurn(event) {
  const side = SIDES[event.agent] || "unknown";
  const payload = event.payload || {};
  const item = document.createElement("li");
  item.className = `turn turn--${side}`;

  const meta = document.createElement("p");
  meta.className = "turn__meta";
  meta.textContent = `Round ${event.round} — ${side.toUpperCase()}`;

  const body = document.createElement("p");
  body.className = "turn__body";
  body.textContent = String(payload.content || "");

  item.append(meta, body);
  return item;
}

// Append a streamed message event into its side column, in arrival order.
function appendMessage(event) {
  const side = SIDES[event.agent];
  const list = document.getElementById(`transcript-${side}`);
  if (list) {
    list.append(renderTurn(event));
  }
}

// --- Controller actions + system log rendering (11.3) --------------------

// Build one <li> for a non-message event: a meta line (round/agent/type) plus
// the event body. Reused by the controller-actions and system-log panels.
function renderEvent(event, kind) {
  const payload = event.payload || {};
  const item = document.createElement("li");
  item.className = `event event--${kind}`;

  const meta = document.createElement("p");
  meta.className = "event__meta";
  meta.textContent = `Round ${event.round} — ${event.event_type} — ${event.agent}`;

  const body = document.createElement("p");
  body.className = "event__body";
  body.textContent = String(payload.content || payload.reason || payload.message || "");

  item.append(meta, body);
  return item;
}

// Route a `nudge` (controller action) into the controller panel — the
// moderator's private corrections, kept OUT of the transcript.
function appendControllerAction(event) {
  const list = document.getElementById("controller-actions");
  if (list) {
    list.append(renderEvent(event, "controller"));
  }
}

// Route a technical event (system/tool_call/timeout/retry) into the system log.
function appendSystemEvent(event) {
  const list = document.getElementById("system-log-list");
  if (list) {
    list.append(renderEvent(event, "system"));
  }
}

// --- Verdict view rendering (11.4) ---------------------------------------

// Human labels for the winner side. The engine emits "pro"/"con"/"tie"; we map
// to clear Pro / Con / Tie copy here (single source of truth, no scattered
// inline strings). Anything unexpected falls back to the raw value.
const WINNER_LABELS = { pro: "Pro", con: "Con", tie: "Tie" };

function winnerLabel(winner) {
  return WINNER_LABELS[winner] || String(winner || "—");
}

// Render the token totals as labelled rows into a <dl>. Cost is Epic 15 — until
// the price table lands cost_usd is 0.0, so we surface TOKENS now.
function renderTokens(container, totals) {
  container.replaceChildren();
  const rows = [
    ["Total tokens", String(totals.total_tokens)],
    ["Input tokens", String(totals.input_tokens)],
    ["Output tokens", String(totals.output_tokens)],
  ];
  for (const [label, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    container.append(dt, dd);
  }
}

// Fill the verdict view from a completed DebateResult: who won (Pro/Con/Tie),
// whether the agents agreed/converged, the debate summary, and token totals.
function renderVerdict(result) {
  const view = document.getElementById("verdict");
  const verdict = (result && result.verdict) || {};
  const totals = (result && result.totals) || {};

  document.getElementById("verdict-winner").textContent = `Winner: ${winnerLabel(
    verdict.winner,
  )}`;
  document.getElementById("verdict-converged").textContent = verdict.converged
    ? "The agents converged / agreed."
    : "The agents did not converge.";
  document.getElementById("verdict-summary").textContent =
    verdict.summary || verdict.rationale || "";
  renderTokens(document.getElementById("verdict-tokens"), {
    total_tokens: totals.total_tokens || 0,
    input_tokens: totals.input_tokens || 0,
    output_tokens: totals.output_tokens || 0,
  });

  if (view) {
    view.hidden = false;
  }
}

// On the `done` sentinel, GET /debates/{id} once and render the verdict view
// from the final DebateResult (verdict + totals in one place). Failures leave
// the view hidden rather than throwing.
async function showVerdict(runId) {
  try {
    const response = await fetch(resultUrl(runId));
    if (!response.ok) {
      return;
    }
    const state = await response.json();
    renderVerdict(state.result || {});
  } catch (err) {
    /* Leave the verdict view hidden on fetch/parse failure. */
  }
}

// Open an EventSource to the API SSE endpoint and render messages live. The
// stream ends with a `done` sentinel event, on which we close the connection.
function streamTranscript(runId) {
  const panels = document.getElementById("panels");
  if (panels) {
    panels.hidden = false;
  }
  const verdictView = document.getElementById("verdict");
  if (verdictView) {
    verdictView.hidden = true;
  }
  clearPanels();

  const source = new EventSource(streamUrl(runId));

  // PANEL 1 — debate transcript: Pro/Con message events.
  source.addEventListener("message", (sseEvent) => {
    appendMessage(JSON.parse(sseEvent.data));
  });

  // PANEL 2 — controller actions / nudges.
  source.addEventListener("nudge", (sseEvent) => {
    appendControllerAction(JSON.parse(sseEvent.data));
  });

  // PANEL 3 — system log: technical/system events.
  for (const eventType of SYSTEM_EVENT_TYPES) {
    source.addEventListener(eventType, (sseEvent) => {
      appendSystemEvent(JSON.parse(sseEvent.data));
    });
  }

  // On the `done` sentinel, close the stream then fetch the final result and
  // render the verdict view (verdict + token totals — task 11.4).
  source.addEventListener("done", () => {
    source.close();
    showVerdict(runId);
  });

  source.addEventListener("error", () => {
    source.close();
  });

  return source;
}

function init() {
  const form = document.getElementById("debate-form");
  const input = document.getElementById("topic");
  const button = document.getElementById("start");
  const result = document.getElementById("result");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const topic = input.value.trim();
    if (!topic) {
      setResult(result, "Please enter a topic.", true);
      return;
    }
    button.disabled = true;
    setResult(result, "Starting debate…", false);
    try {
      const data = await startDebate(topic);
      setResult(result, `Debate started — run id: ${data.run_id}`, false);
      streamTranscript(data.run_id);
    } catch (err) {
      setResult(result, `Could not start debate: ${err.message}`, true);
    } finally {
      button.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", init);
