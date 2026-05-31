// Topic-input page + live transcript (tasks 11.1/11.2, issues #73/#74).
//
// 11.1: on submit, POST the topic to the API's POST /debates and show the
// returned run_id. 11.2: then open a Server-Sent-Events stream to the API's
// GET /debates/{id}/stream and render the Pro vs Con MESSAGE transcript LIVE
// as events arrive, closing on the `done` sentinel.
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

function apiBaseUrl() {
  const meta = document.querySelector(`meta[name="${META_NAME}"]`);
  return ((meta && meta.content) || "").replace(/\/+$/, "");
}

function streamUrl(runId) {
  return `${apiBaseUrl()}/debates/${encodeURIComponent(runId)}/stream`;
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

function clearTranscript() {
  for (const side of Object.values(SIDES)) {
    const list = document.getElementById(`transcript-${side}`);
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

// Open an EventSource to the API SSE endpoint and render messages live. The
// stream ends with a `done` sentinel event, on which we close the connection.
function streamTranscript(runId) {
  const transcript = document.getElementById("transcript");
  if (transcript) {
    transcript.hidden = false;
  }
  clearTranscript();

  const source = new EventSource(streamUrl(runId));

  source.addEventListener("message", (sseEvent) => {
    appendMessage(JSON.parse(sseEvent.data));
  });

  source.addEventListener("done", () => {
    source.close();
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
