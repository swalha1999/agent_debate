# TASKS — Agent Debate

**Status:** Draft v0.1 · **Last updated:** 2026-05-30
**Owners:** `S` = swalha1999, `M` = Mhmdabad (claim items by putting your initial in the `Owner` slot).
**Source of truth:** `PRD.md`. Each task traces back to a PRD requirement.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked.
Priority: **P0** = must-have for a working debate · **P1** = required for submission quality · **P2** = nice-to-have.

---

## Epic 0 — Repo & workspace scaffold (M1)

> Goal: a runnable, lintable, typed empty skeleton before any LLM logic.

- [ ] **0.1** Init `uv` workspace at repo root (`pyproject.toml` with `[tool.uv.workspace] members = ["packages/*"]`). · P0 · Owner: __
- [ ] **0.2** Create the five package skeletons with their own `pyproject.toml`: `packages/core`, `packages/log`, `packages/api`, `packages/cli`, `packages/ui`. · P0 · dep: 0.1
- [ ] **0.3** Wire intra-workspace deps: `api/cli/ui/core` depend on `log`; `api/cli/ui` depend on `core`. · P0 · dep: 0.2
- [ ] **0.4** Pin Python `>=3.12`; generate `uv.lock`; verify `uv sync` works clean. · P0 · dep: 0.1
- [ ] **0.5** Add `ruff` (lint+format) config and `mypy`/`pyright` config in root `pyproject.toml`. · P1 · dep: 0.1
- [ ] **0.6** Add `pytest` + a trivial passing test per package so `uv run pytest` is green. · P1 · dep: 0.2
- [ ] **0.7** Add `.gitignore` (`.venv`, `__pycache__`, `.env`, `runs/`, caches) and `.env.example` with every var from PRD §7. · P0 · dep: 0.1
- [ ] **0.8** GitHub Actions CI: `uv sync` → `ruff check` → `mypy` → `pytest` on push/PR. · P1 · dep: 0.5, 0.6
- [ ] **0.9** Root `README.md`: what it is, install (`uv sync`), quickstart, links to docs. · P1 · dep: 0.2

**Epic 0 acceptance:** fresh clone → `uv sync && uv run pytest && ruff check .` all pass; CI green.

---

## Epic 1 — LOG package (M1)

> Goal: one structured-logging surface used by everything. PRD §5.7.

- [ ] **1.1** `structlog` setup factory: pretty console sink (dev) + JSONL file sink per run (`runs/<run_id>.jsonl`). · P0 · Owner: __
- [ ] **1.2** Define the event schema as a typed model: `run_id, ts, round, agent, event_type, payload, tokens, latency_ms`. `event_type ∈ {message, tool_call, nudge, timeout, retry, verdict, system}`. · P0 · dep: 1.1
- [ ] **1.3** Helper API: `get_logger(run_id)`, `log_event(...)`, context binding for `run_id`/`round`. · P0 · dep: 1.2
- [ ] **1.4** Redaction filter: never log API keys / secrets; truncate huge payloads. · P1 · dep: 1.1
- [ ] **1.5** Unit tests: event written to JSONL, schema validates, redaction works. · P1 · dep: 1.3

**Epic 1 acceptance:** calling the logger produces validated console + JSONL events with `run_id` correlation; secrets never appear.

---

## Epic 2 — Config & provider abstraction (M1→M2)

> Goal: no-lock-in model + config. PRD §4, §7.

- [ ] **2.1** `pydantic-settings` `Settings` model loading from env/`.env`: all PRD §7 vars with defaults. · P0 · Owner: __
- [ ] **2.2** Model resolver: map `DEBATER_MODEL`/`CONTROLLER_MODEL`/`PRO_MODEL`/`CON_MODEL` strings → Pydantic AI models (Anthropic default, others swappable). · P0 · dep: 2.1
- [ ] **2.3** Validate required keys at startup with a clear error (e.g. missing `ANTHROPIC_API_KEY`). · P1 · dep: 2.1
- [ ] **2.4** Confirm exact current Anthropic model IDs at wiring time; document them in `.env.example`. · P0 · dep: 2.2
- [ ] **2.5** Tests: settings load from env, per-side override falls back correctly, bad model string fails loudly. · P1 · dep: 2.2

**Epic 2 acceptance:** changing a model env var swaps the provider with zero code changes; missing key fails fast with a helpful message.

---

## Epic 3 — Pluggable search providers (M2)

> Goal: web search as a swappable plug-in. PRD §5.5. **Web search is a MUST.**

- [ ] **3.1** Define `SearchResult` model + `SearchProvider` Protocol (`search(query, *, max_results) -> list[SearchResult]`). · P0 · Owner: __
- [ ] **3.2** Provider registry + factory selected by `SEARCH_BACKEND`. · P0 · dep: 3.1, 2.1
- [ ] **3.3** `DuckDuckGoSearchProvider` (default, via `ddgs`): map raw results → `SearchResult`. · P0 · dep: 3.1
- [ ] **3.4** Resilience: timeout, retry/backoff, and graceful empty-result handling (search can be flaky). · P1 · dep: 3.3
- [ ] **3.5** Stub second provider (e.g. `TavilySearchProvider`) behind the same interface to prove swap-ability (key via `SEARCH_API_KEY`). · P2 · dep: 3.2
- [ ] **3.6** Tests: registry selection, DDG mapping, empty/error path, swap to stub provider with no engine changes. · P1 · dep: 3.3

**Epic 3 acceptance:** `SEARCH_BACKEND=duckduckgo` returns clean `SearchResult`s; switching backend is a one-line config change.

---

## Epic 4 — Agent skills (tools) (M2)

> Goal: each agent has >1 named skill, advertised in its system prompt. PRD §5.2.

- [ ] **4.1** `web_search(query)` skill wrapping the active `SearchProvider`; results pass through gatekeeper before returning to the model. · P0 · dep: 3.3, 7.1
- [ ] **4.2** `build_argument(...)` skill: structure a persuasive argument/rebuttal for the agent's side. · P0 · Owner: __
- [ ] **4.3** `analyze_opponent_argument(...)` skill: dissect opponent's last message, surface weaknesses, decide what to rebut. · P0 · dep: 4.2
- [ ] **4.4** Controller-only skills: `assess_drift(...)`, `nudge(...)`, `render_verdict(...)`. · P0 · dep: 4.3
- [ ] **4.5** Register skills as real Pydantic AI tools with validated (Pydantic) inputs. · P0 · dep: 4.1–4.4
- [ ] **4.6** Tests: each tool callable, input validation rejects bad payloads, web_search output is sanitised. · P1 · dep: 4.5

**Epic 4 acceptance:** debaters expose ≥2 skills + web_search; controller exposes its moderation skills; all inputs validated.

---

## Epic 5 — Agents & prompts (M2→M3)

> Goal: Pro, Con, Controller agents with anti-sycophancy baked into prompts. PRD §5.2, §5.3.

- [ ] **5.1** Pro debater `Agent`: system prompt states side = FOR, rules (word limit, MUST rebut, don't concede just because opponent is convincing), and an explicit list of its skills + when to use them. · P0 · Owner: __
- [ ] **5.2** Con debater `Agent`: mirror of 5.1, side = AGAINST. · P0 · dep: 5.1
- [ ] **5.3** Controller `Agent`: moderator/judge prompt — knows both sides, **never reveals its own stance**, instructed to detect drift and nudge. · P0 · dep: 5.1
- [ ] **5.4** Each agent gets its **own independent conversation context** (no shared thread). · P0 · dep: 5.1, 5.2
- [ ] **5.5** Per-turn **side anchoring**: re-inject the agent's assigned side + anti-concession reminder every turn. · P0 · dep: 5.4
- [ ] **5.6** Adversarial relay: opponent's message is injected framed as "Your opponent argued: «…». Rebut it." (not as a peer/agreeable turn). · P0 · dep: 5.4
- [ ] **5.7** Word-limit enforcement: instruct in prompt **and** verify/trim post-generation; log violations. · P0 · dep: 5.5
- [ ] **5.8** Tests: prompts include skill list; controller prompt never leaks stance; relay framing present; word limit enforced. · P1 · dep: 5.6

**Epic 5 acceptance:** three agents instantiate with correct prompts/contexts; anti-sycophancy mechanisms present and tested.

---

## Epic 6 — Orchestration engine / SDK (M2→M3)

> Goal: the debate loop with timeout+retry. PRD §5.4, §5.2 (SDK surface).

- [ ] **6.1** `DebateConfig` + `DebateResult` (transcript, tool calls, nudges, verdict, token/cost totals) typed models. · P0 · Owner: __
- [ ] **6.2** Topic setup: controller receives/sets topic, privately assigns Pro/Con, keeps own stance hidden. · P0 · dep: 5.3
- [ ] **6.3** Main loop: 10 rounds, alternating Pro → (drift check) → Con → (drift check); 10 messages each. · P0 · dep: 5.6, 6.2
- [ ] **6.4** **Timeout wrapper** on every model call: cancel on `TURN_TIMEOUT_S`, retry up to `MAX_RETRIES`, then mark turn failed + inform controller. · P0 · dep: 6.3
- [ ] **6.5** Closing discussion phase (freer exchange) after the 10 rounds. · P0 · dep: 6.3
- [ ] **6.6** Event streaming: yield events (messages, tool calls, nudges, verdict) so API/CLI/UI can consume live. · P0 · dep: 6.3
- [ ] **6.7** Token/cost accounting per turn → totals in `DebateResult` (cost awareness). · P1 · dep: 6.3, 1.2
- [ ] **6.8** Public SDK entrypoint: `from agent_debate import DebateEngine; DebateEngine(config).run(topic)`. · P0 · dep: 6.1–6.6
- [ ] **6.9** Tests (mocked LLM): full 10v10 run completes; timeout triggers kill+retry; failed turn handled; streaming emits ordered events. · P1 · dep: 6.8

**Epic 6 acceptance:** a mocked debate runs end-to-end with correct round counts, enforced timeouts/retries, and streamed events.

---

## Epic 7 — Security gatekeeper (M5, but interface early)

> Goal: sanitise everything crossing a trust boundary. PRD §5.6.

- [ ] **7.1** Gatekeeper module: sanitise/normalize untrusted text (topic, **search results**, model output) before it re-enters a prompt — anti prompt-injection. · P0 · Owner: __
- [ ] **7.2** Input validation: topic length/charset caps; search query caps; reject control sequences. · P1 · dep: 7.1
- [ ] **7.3** No arbitrary code execution from model/tool output; tool args strictly typed. · P0 · dep: 4.5
- [ ] **7.4** Secret hygiene check in CI: fail if a key-like string is committed. · P1 · dep: 0.8
- [ ] **7.5** Tests: injection payload in a search result is neutralised; oversized/abusive input rejected. · P1 · dep: 7.1

**Epic 7 acceptance:** crafted prompt-injection via search results does not alter agent behaviour; secrets never enter repo or logs.

---

## Epic 8 — Controller intelligence (M3)

> Goal: real moderation + verdict. PRD §5.3, §5.4.

- [ ] **8.1** `assess_drift`: after each message decide if the agent still defends its side or has been captured/started agreeing. · P0 · dep: 4.4, 6.3
- [ ] **8.2** `nudge`: craft a private correction when captured; logged + shown in UI; **not** counted as a debate turn. · P0 · dep: 8.1
- [ ] **8.3** Verdict: summary of the debate, whether agents converged/agreed, the result, and **who won** + reasoning. **No fact-checking.** · P0 · dep: 6.5
- [ ] **8.4** Staged-drift test fixture: force an agent to parrot the opponent; assert controller nudges it back. · P1 · dep: 8.2

**Epic 8 acceptance:** controller detects ≥1 staged drift and nudges; produces a structured verdict with a winner and no fact-checking.

---

## Epic 9 — CLI (M4)

> PRD §6.

- [ ] **9.1** Typer app: `agent-debate run "<topic>" [--rounds] [--max-words] [--model] [--search-backend]`. · P0 · Owner: __
- [ ] **9.2** Live transcript rendering (Rich): Pro/Con messages per round + inline controller nudges. · P1 · dep: 6.6
- [ ] **9.3** `--json` machine output of `DebateResult`; non-zero exit on failure. · P1 · dep: 6.8
- [ ] **9.4** Tests: CLI runs a mocked debate and prints transcript + verdict. · P1 · dep: 9.1

**Epic 9 acceptance:** `agent-debate run "..."` runs a full debate from the terminal with live output and a final verdict.

---

## Epic 10 — API (M4)

> PRD §6.

- [ ] **10.1** FastAPI app + Uvicorn entrypoint. · P0 · Owner: __
- [ ] **10.2** `POST /debates` (start, returns `run_id`), `GET /debates/{id}` (status/result). · P0 · dep: 6.8
- [ ] **10.3** `GET /debates/{id}/stream` SSE of live events. · P1 · dep: 6.6
- [ ] **10.4** Request validation, error handling, CORS for the UI. · P1 · dep: 10.2
- [ ] **10.5** Tests: start → poll → result; stream emits events (mocked engine). · P1 · dep: 10.3

**Epic 10 acceptance:** a debate can be started, streamed, and fetched over HTTP.

---

## Epic 11 — UI (M4)

> PRD §6. Separate panels — don't overload one view (lesson from feedback).

- [ ] **11.1** Web page: topic input → start debate via API. · P1 · Owner: __
- [ ] **11.2** Live streaming transcript (Pro vs Con) consuming the SSE endpoint. · P1 · dep: 10.3
- [ ] **11.3** Separate panels: debate transcript · controller actions/nudges · system log. · P1 · dep: 11.2
- [ ] **11.4** Final verdict view (summary, agree/disagree, who won, token cost). · P1 · dep: 11.2
- [ ] **11.5** RTL-safe styling (logical properties, `start`/`end`) per house CSS rules. · P2 · dep: 11.1
- [ ] **11.6** Smoke test / screenshot of a completed debate. · P2 · dep: 11.4

**Epic 11 acceptance:** a user enters a topic and watches the debate stream to a final verdict across clearly separated panels.

---

## Epic 12 — Quality, docs & submission (M5)

> Goal: meet the lecturer guidelines + the Improvements checklist.

- [ ] **12.1** Tests for all PRD §8 acceptance criteria; coverage on the engine + gatekeeper. · P1 · Owner: __
- [ ] **12.2** Per-package READMEs + root README quickstart for all five surfaces. · P1 · dep: 9, 10, 11
- [ ] **12.3** Cost report: document typical token usage per debate and how it scales with rounds/word-limit (PRD §8). · P1 · dep: 6.7
- [ ] **12.4** Architecture/decisions doc (or expand PRD §5) for a new team member. · P1
- [ ] **12.5** **Generate sample debate runs and commit them to the repo** so the teacher can see real runs: save each run's transcript + verdict + token/cost totals under `runs/` (e.g. `runs/<run_id>.jsonl` plus a readable `runs/<run_id>.md`). Aim for a few varied topics. · P0 · Owner: __ · dep: 6.8, 8.3
- [ ] **12.6** Add an `examples/` or `runs/README.md` index listing the saved debates (topic, who won, link) and link it from the root README. · P1 · dep: 12.5
- [ ] **12.7** Final pass against `Improvements_to_keep_in_mind.md` — tick every box. · P0 · dep: all
- [ ] **12.8** Final pass against the lecturer's `software_submission_guidelines-V3` PDF. · P0 · dep: all

**Epic 12 acceptance:** every PRD §8 box checked; CI green; both guideline docs satisfied; **sample debate runs are committed to the repo** and indexed.

> 📌 **Reminder:** after the engine works (Epic 6) and the controller renders verdicts (Epic 8), don't forget to **run several debates and commit the saved runs** — this is the evidence the teacher will look at.

---

## Suggested order (critical path)

`Epic 0 → 1 → 2 → 3 → 4 → 7(7.1) → 5 → 6 → 8 → 9 → 10 → 11 → 12`

Parallelizable once Epic 6 exists: CLI (9), API (10), UI (11) can proceed in parallel; LOG (1) and search (3) can start right after the scaffold.
