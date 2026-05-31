// Topic-input page logic (task 11.1, issue #73).
//
// On submit, POST the topic to the API's POST /debates and show the returned
// run_id. The API base URL is config-driven, NOT hard-coded: the server injects
// it into the <meta name="api-base-url"> tag (and also exposes GET /config).

"use strict";

const META_NAME = "api-base-url";

function apiBaseUrl() {
  const meta = document.querySelector(`meta[name="${META_NAME}"]`);
  return (meta && meta.content || "").replace(/\/+$/, "");
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
    } catch (err) {
      setResult(result, `Could not start debate: ${err.message}`, true);
    } finally {
      button.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", init);
