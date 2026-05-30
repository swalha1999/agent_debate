# PRD — Agent Debate

**Project:** `agent_debate`
**Course context:** Orchestration of AI Agents
**Repository:** https://github.com/swalha1999/agent_debate
**Status:** Draft v0.1
**Last updated:** 2026-05-30
**Owners:** swalha1999, Mhmdabad

Companion docs:
- `Improvements_to_keep_in_mind.md` — standing quality/lessons checklist
- `software_submission_guidelines-V3.en.md` / `.md` — lecturer's required guidelines (authoritative)

---

## 1. Summary

A system in which **two debate agents** argue opposite sides of a topic — one
**for**, one **against** — across a fixed number of back-and-forth rounds, while a
third **controller agent** moderates the debate, keeps each debater on track, and
at the end produces a written summary, the outcome, and a verdict on who won.

The point of interest is **the debate itself** — whether the agents genuinely
engage, rebut each other, and converge or stay opposed — **not** fact-checking.
We do not verify the truth of claims; we care about argument quality and whether
the agents end up agreeing or not.

A core design risk we explicitly engineer against: **LLMs are trained to be
agreeable and tend to drift toward the last speaker's position (sycophancy).** The
architecture must prevent either debater from "controlling" the other, and the
controller must detect and **nudge a captured agent back onto its assigned side.**

## 2. Goals

- Run a structured **Pro vs. Con** debate: **10 rounds each** (10 messages per
  agent, alternating — 10-vs-10 back and forth).
- **Word limit per agent message** (configurable), to bound both verbosity and cost.
- Agents must **answer each other** — rebut the opponent's actual points, not just
  recite prepared bullet points. They may also introduce new arguments and steer
  the discussion in new directions.
- **Web search is mandatory** — every debater must be able to search the web to
  ground/strengthen arguments. (MUST.)
- Each agent has **more than one skill** (e.g. *build an argument* and *analyse the
  opponent's argument*), and the **system prompt explicitly tells the agent which
  skills it has.**
- A **controller agent** that: assigns the topic, never reveals its own opinion or
  which side it favours, nudges drifting agents, and at the end writes the
  **summary + result + who won.**
- After the 10 rounds, a **closing discussion phase** where the agents respond to
  each other more freely before the controller renders judgement.
- **Robustness:** if an agent fails to answer within a **timeout**, kill that call
  and **retry/recall** it.
- **Security gatekeeper** around all trust boundaries; **no secrets in the repo.**
- Full **logging** of everything that happens.
- Ship five surfaces: **UI, CLI, API, SDK, LOG.**
- Follow the lecturer's submission guidelines (the PDF) throughout.

## 3. Non-goals

- **No fact-checking / truth verification.** Claims are not validated.
- No persuasion of a real human; the audience is the controller's evaluation.
- No fine-tuning or training of models — we orchestrate existing LLMs.
- No multi-topic / tournament mode in v1 (single topic per run).

## 4. Tech stack & key decisions

| Concern | Decision | Rationale |
|---|---|---|
| Language | **Python 3.12+** | Required. |
| Package/dep manager | **`uv`** | Required; fast, reproducible, workspace support. |
| LLM abstraction | **Pydantic AI** | Provider-agnostic ("something like Vercel AI SDK" for Python). Swap models by changing a model string — **no ecosystem lock-in.** Typed agents + first-class tool calling for skills. |
| Default provider | **Anthropic Claude** (e.g. `anthropic:claude-sonnet-4-6` for debaters, `anthropic:claude-opus-4-8` for controller) | Strong reasoning. Swappable per role. |
| Web search | **Pluggable `SearchProvider` interface**, default impl = **DuckDuckGo** (`duckduckgo-search`/`ddgs`) | Free, no API key, provider-independent. Search is a **plug-in** behind a stable interface — swap to Tavily/Bing/SerpAPI by changing one config value, no engine changes. |
| API | **FastAPI** + Uvicorn | Standard, async, typed. |
| UI | Lightweight web UI over the API (live transcript) | Renders per-round transcript, controller actions, verdict. |
| CLI | **Typer** | Ergonomic, typed CLI. |
| Logging | **structlog** (structured JSON + pretty console) | Machine- and human-readable logs. |
| Lint/format/types | **ruff** + **mypy/pyright** | Automated quality gate (lesson from feedback). |
| Tests | **pytest** | Edge cases: timeout, drift, failed search, malformed output. |
| Config | **pydantic-settings** + `.env` (with `.env.example`) | Portable, no secrets committed. |

> No-lock-in guarantee: anywhere a model is referenced it is a config string routed
> through Pydantic AI, so Anthropic/OpenAI/Gemini/Groq/Ollama are interchangeable.

## 5. Architecture

### 5.1 Packages (uv workspace)

The repo is a **uv workspace** with these members (the five required surfaces):

```
agent_debate/
├─ packages/
│  ├─ core/        # SDK — the debate engine (agents, skills, controller, orchestration)
│  ├─ log/         # LOG — structured logging setup, log schema, sinks
│  ├─ api/         # API — FastAPI app exposing run/stream/status endpoints
│  ├─ cli/         # CLI — Typer app to launch & watch a debate from the terminal
│  └─ ui/          # UI — web frontend that consumes the API (live transcript + verdict)
├─ docs/           # PRD, guidelines, improvements checklist
├─ tests/
├─ pyproject.toml  # workspace root
└─ .env.example
```

- **SDK (`core`)** is the heart: it can be imported and driven programmatically
  (`from agent_debate import DebateEngine`). API/CLI/UI are thin shells over it.
- **LOG** is a shared dependency used by every other package.

### 5.2 Agents

Three agents, each a Pydantic AI `Agent` with its own **independent conversation
context** (critical — see anti-sycophancy below):

1. **Pro debater** — argues *for* the topic.
2. **Con debater** — argues *against* the topic.
3. **Controller** — moderator/judge. Knows both assigned sides but **never reveals
   its own opinion or which side it leans.**

Each debater is configured with:
- A **system prompt** that states its side, the rules (word limit, must rebut), and
  an **explicit list of the skills it has and when to use them.**
- **Skills (tools):**
  - `web_search(query)` — mandatory capability; calls the configured `SearchProvider` plug-in (DuckDuckGo by default). The skill is provider-agnostic — the agent never talks to a specific search vendor directly.
  - `build_argument(...)` — structure a persuasive argument / rebuttal.
  - `analyze_opponent_argument(...)` — dissect the opponent's last message, find
    weaknesses, and decide what to answer.
  - (Skills are real registered tools; the system prompt names them so the model
    knows it can call them.)

The controller has its own skills: `web_search` (optional context),
`assess_drift(...)` (detect an agent parroting/conceding to the opponent),
`nudge(...)` (craft a private correction), and `render_verdict(...)`.

### 5.3 Anti-sycophancy / "no agent controls the other"

This is a first-class requirement. Mechanisms:

- **Separate contexts, message relay.** The two debaters do **not** share one chat
  thread. The engine relays the opponent's message into each agent framed
  adversarially ("Your opponent argued: «…». Rebut it.") rather than as a peer turn,
  so the model is not nudged into agreeing with "the speaker."
- **Side anchoring every turn.** Each debater's turn re-states its assigned side and
  the instruction *not* to concede merely because the opponent sounds convincing.
- **Drift detection by the controller.** After each message, the controller runs
  `assess_drift`: is the agent still defending its side, or has it started agreeing
  with / restating the opponent? If captured, the controller **privately nudges** it
  back on track (the nudge is logged, shown in UI, but not counted as a debate turn).
- **Cross-provider option.** Roles may be assigned different providers/models to make
  collusion/agreement less likely (config-driven; default same-provider).
- **No shared scratchpad.** Agents cannot read each other's private reasoning.

### 5.4 Orchestration flow

```
1. Setup
   - Controller selects/receives the topic and privately assigns Pro and Con.
   - Controller does NOT disclose its own stance to anyone.
2. Debate loop  (round = 1..10)
   - Pro produces message  (≤ word limit; may web_search, build_argument, analyze)
   - Controller: assess_drift(Pro) → nudge if captured (logged)
   - Con produces message  (must rebut Pro's latest; ≤ word limit; tools available)
   - Controller: assess_drift(Con) → nudge if captured (logged)
   - All messages, tool calls, nudges logged.
3. Closing discussion
   - A freer exchange where each agent responds to the other before judgement.
4. Verdict
   - Controller writes: summary of the debate, whether the agents converged/agreed,
     the result, and WHO WON (with reasoning). No fact-checking — judged on
     argumentation, rebuttal quality, and engagement.
```

Every model call is wrapped with a **timeout**; on timeout the call is **cancelled
and retried** up to N times (then that turn is marked failed and the controller is
informed). This satisfies "add a timeout that kills and recalls the process."

### 5.5 Pluggable search providers (web search is a plug-in)

Web search is a **swappable plug-in**, not hardcoded. The engine and the
`web_search` skill depend only on a stable interface; concrete vendors live behind
it and are selected by config.

```python
# packages/core/.../search/base.py
class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class SearchProvider(Protocol):
    name: str
    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]: ...
```

- **Registry + config selection.** Providers register under a name; the active one is
  chosen via `SEARCH_BACKEND` (e.g. `duckduckgo`, `tavily`, `bing`). Switching
  backends is a **one-line config change** — no engine, agent, or skill edits.
- **Default plug-in:** `DuckDuckGoSearchProvider` (free, no key).
- **Drop-in additions:** a new provider is added by implementing `SearchProvider` and
  registering it; e.g. `TavilySearchProvider`, `SerpApiSearchProvider`. Nothing
  upstream changes.
- **Uniform contract:** every provider returns the same `SearchResult` shape, so the
  `web_search` skill and the gatekeeper sanitisation work identically regardless of
  vendor.
- **Same pattern is reused** for other replaceable bits (the LLM provider is already
  pluggable via Pydantic AI's model strings), keeping the system consistent and
  lock-in-free.

### 5.6 Security gatekeeper

- All external text (user-supplied topic, **web-search results**, model output) passes
  through a **gatekeeper** that sanitises it before it re-enters a prompt — defends
  against prompt-injection via search results and keeps untrusted text from driving
  privileged actions.
- Secrets only via env/`.env`; **never committed**. `.env.example` documents required
  keys. CI check fails if a key-like string is committed.
- Tool inputs validated (Pydantic models); web-search queries length-capped; no
  arbitrary code execution from model output.
- Dependency pinning via `uv.lock`.

### 5.7 Logging

- `structlog`-based, every event carries: `run_id`, `round`, `agent`, `event_type`
  (`message` | `tool_call` | `nudge` | `timeout` | `retry` | `verdict` | `system`),
  `tokens`, `latency_ms`.
- Two sinks: pretty console (dev) + JSONL file per run (`runs/<run_id>.jsonl`).
- The LOG package is the single source of truth used by SDK/API/CLI/UI.

## 6. Surfaces (deliverables)

- **SDK** — `DebateEngine(config).run(topic)` returns a structured `DebateResult`
  (transcript, nudges, verdict). Streams events for live consumers.
- **CLI** — `agent-debate run "<topic>" [--rounds 10] [--max-words 150] [--model …]`;
  prints the live transcript and final verdict; `--json` for machine output.
- **API** — `POST /debates` to start, `GET /debates/{id}` for status/result,
  `GET /debates/{id}/stream` (SSE) for live events.
- **UI** — web page: enter a topic → watch Pro/Con messages stream round by round,
  see controller nudges inline, and read the final verdict; separate panels for
  transcript / controller actions / system log (don't overload one view).
- **LOG** — structured logs as above, queryable per run.

## 7. Configuration (env)

| Var | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Default provider key | — (required) |
| `DEBATER_MODEL` | Model for both debaters | `anthropic:claude-sonnet-4-6` |
| `CONTROLLER_MODEL` | Model for controller | `anthropic:claude-opus-4-8` |
| `PRO_MODEL` / `CON_MODEL` | Optional per-side override (cross-provider) | falls back to `DEBATER_MODEL` |
| `ROUNDS` | Rounds per agent | `10` |
| `MAX_WORDS` | Word limit per message | `150` |
| `TURN_TIMEOUT_S` | Per-turn timeout | `60` |
| `MAX_RETRIES` | Retries on timeout/error | `2` |
| `SEARCH_BACKEND` | Selects the `SearchProvider` plug-in (`duckduckgo`/`tavily`/…) — swap with one value | `duckduckgo` |
| `SEARCH_API_KEY` | Key for backends that need one (ignored by DuckDuckGo) | — |

## 8. Acceptance criteria

- [ ] A debate runs end-to-end: 10 Pro + 10 Con messages, alternating, each within the word limit.
- [ ] Debaters demonstrably **rebut** the opponent's last message (not isolated monologues).
- [ ] Each debater **uses web search** at least when relevant, and has ≥2 skills named in its system prompt.
- [ ] Controller never leaks its stance; detects ≥1 staged drift case and nudges the agent back.
- [ ] A turn that exceeds the timeout is killed and retried automatically.
- [ ] Controller outputs a final **summary + agree/disagree result + who won** (no fact-checking).
- [ ] All five surfaces (UI, CLI, API, SDK, LOG) work; logs capture every event with `run_id`.
- [ ] No secrets in repo; `ruff`, type checks, and tests pass in CI.
- [ ] Per-run cost (tokens) is logged and reported (cost awareness).

## 9. Open questions / future work

- Cross-provider defaults for stronger anti-sycophancy (currently opt-in).
- Tavily as an alternative search backend behind the same interface.
- Multi-topic tournament + Elo scoring of debaters.
- Human-in-the-loop override of the controller's verdict.

## 10. Milestones

1. **M1 — Scaffold:** uv workspace, packages, config, LOG, CI/ruff. 
2. **M2 — SDK core:** agents, skills (web_search/build_argument/analyze), relay-based orchestration, timeout+retry.
3. **M3 — Controller:** drift detection, nudging, verdict.
4. **M4 — Surfaces:** CLI → API → UI.
5. **M5 — Hardening:** gatekeeper, tests (edge cases), cost reporting, docs.
