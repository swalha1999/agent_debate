# PRD — Agent Debate

**Project:** `agent_debate`
**Course context:** Orchestration of AI Agents
**Repository:** https://github.com/swalha1999/agent_debate
**Status:** Draft v0.2
**Last updated:** 2026-05-30
**Owners:** swalha1999, Mhmdabad

Companion docs:
- `Improvements_to_keep_in_mind.md` — standing quality/lessons checklist
- `software_submission_guidelines-V3.en.md` / `.md` — lecturer's required guidelines (authoritative)
- `PROMPTS.md` — the **Prompt Book** (significant prompts that shaped the project; guideline §8.3)
- `prds/` — **dedicated sub-PRDs** for each algorithm/mechanism (guideline §2.3):
  - `prds/debate-orchestration.md` — the 10-vs-10 loop, timeout/retry, phases
  - `prds/anti-sycophancy.md` — drift detection & "no agent controls the other"
  - `prds/api-gatekeeper.md` — centralized rate-limited API gatekeeper
  - `prds/search-plugin.md` — the pluggable `SearchProvider` interface

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

> For a newcomer-oriented walkthrough of the system, the five packages, the key
> mechanisms, and an ADR-style **decisions/rationale** table, see the dedicated
> [`ARCHITECTURE.md`](ARCHITECTURE.md). This section is the canonical spec it
> summarises and links back to.

### 5.1 Packages (uv workspace)

The repo is a **uv workspace** with these members (the five required surfaces):

```
agent_debate/
├─ packages/
│  ├─ core/        # SDK — engine, agents, skills, controller, API gatekeeper, search plug-ins, version (1.00)
│  ├─ log/         # LOG — structured logging, cost accounting, log schema, sinks
│  ├─ api/         # API — FastAPI app exposing run/stream/status endpoints
│  ├─ cli/         # CLI — Typer app to launch & watch a debate from the terminal
│  └─ ui/          # UI — web frontend that consumes the API (live transcript + verdict)
├─ config/         # rate_limits.json (versioned) + other non-secret config
├─ docs/           # PRD, sub-PRDs (prds/), PROMPTS.md, guidelines, improvements checklist
│  └─ prds/        # dedicated per-mechanism PRDs (guideline §2.3)
├─ notebooks/      # results analysis + visualizations (guideline §9)
├─ runs/           # saved debate runs (jsonl + md) committed for review (TASKS §12.5)
├─ tests/          # TDD suite, ≥85% coverage
├─ .building_tasks_logs/  # per-task build log (prompt + tokens)
├─ pyproject.toml  # workspace root — single source of truth for deps
└─ .env.example
```

> Every code file ≤ 150 lines (guideline §3.2): the engine is split into small
> single-responsibility modules (agents, skills, relay, loop, timeout, gatekeeper,
> verdict, models, constants).

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

### 5.6 API Gatekeeper (rate limiting + overflow queue) — guideline §5

A **centralized API gatekeeper** through which **every** external call (LLM provider
*and* search provider) must pass. No code makes a direct API call that bypasses it.
This is separate from the security gatekeeper in §5.7.

```python
# packages/core/.../gatekeeper/api_gatekeeper.py
class ApiGatekeeper:
    def __init__(self, config: RateLimitConfig): ...
    def execute(self, api_call, *args, **kwargs):
        # 1) check rate limits before execution
        # 2) queue (FIFO) if limit reached — never drop/crash
        # 3) retry on transient failures (with backoff)
        # 4) log every call
        ...
    def get_queue_status(self) -> QueueStatus: ...
```

- **No direct calls.** The LLM layer (Pydantic AI) and the `SearchProvider` plug-ins
  are invoked *through* the gatekeeper.
- **Rate limits from config, not code** — read from `config/rate_limits.json`
  (`requests_per_minute`, `requests_per_hour`, `concurrent_max`, `retry_after_seconds`,
  `max_retries`), versioned starting at `1.00`.
- **Overflow → FIFO queue** with a max depth, **backpressure** when full, and a
  **drain** mechanism that processes requests as rate windows reset. Never drop.
- **Retries** on transient failures with backoff; **every call logged** for monitoring.
- Detailed design: `prds/api-gatekeeper.md`.

### 5.7 Security gatekeeper

- All external text (user-supplied topic, **web-search results**, model output) passes
  through a **gatekeeper** that sanitises it before it re-enters a prompt — defends
  against prompt-injection via search results and keeps untrusted text from driving
  privileged actions.
- Secrets only via env/`.env`; **never committed**. `.env.example` documents required
  keys. CI check fails if a key-like string is committed.
- Tool inputs validated (Pydantic models); web-search queries length-capped; no
  arbitrary code execution from model output.
- Dependency pinning via `uv.lock`.

### 5.8 Logging

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
| `BUDGET_USD` | Per-run USD budget cap; over-budget triggers an alert. `0` = unlimited (§10, 15.3) | `0` |

Rate limits are **not** env vars — they live in `config/rate_limits.json` (guideline §5.2).

## 8. Engineering & quality standards (guideline-mandated)

These are hard requirements from the lecturer's guidelines; we adopt them explicitly.

- **TDD — Red→Green→Refactor** (§6.1): write the failing test first, then the code.
- **Test coverage ≥ 85%** (§6.2): `pyproject.toml` sets `fail_under = 85`; the suite
  fails below threshold. Statement + branch + critical-path coverage.
- **Max 150 lines per code file** (§3.2): split (helpers/mixins/constants/models)
  rather than compress. Enforced by an automated check in CI.
- **Ruff = 0 violations** (§7.1) + type checks (mypy/pyright).
- **No hard-coded values** (§7.2): everything via config; constants in `constants.py`.
- **SDK architecture, OOP, no duplication** (§4): all logic lives in the SDK; extract
  on the 2nd copy.
- **Package organization** (§14): `pyproject.toml` as single source of truth (no
  `requirements.txt`), `__init__.py` exports, relative paths.
- **Version control** (§8): a **version module starting at `1.00`**, semantic bumps,
  meaningful commits, and the **Prompt Book** (`PROMPTS.md`).
- **Parallel processing** (§15): debaters/searches run via async concurrency; the
  gatekeeper enforces `concurrent_max`. Thread-safety documented for shared state.
- **Code comments/docstrings** (§3.3): public APIs documented; non-obvious logic commented.
- **UI usability** (§10): assessed against **Nielsen's 10 heuristics**; interface documented.
- **ISO/IEC 25010** (§13): system mapped to the product-quality characteristics —
  functional suitability, performance efficiency, compatibility, usability,
  reliability, security, maintainability, portability — in
  [`ARCHITECTURE.md` §8](ARCHITECTURE.md#8-isoiec-25010-product-quality-mapping).
- **CI gates established first** (§6, §7): tests, ruff (0), coverage (≥85%), 150-line
  check, and secret scan run on every push **before** feature work — see TASKS Epic 0.

## 9. Research & results analysis (guideline §9)

The debate system is also our experiment. We will produce a results notebook +
visualizations (in `notebooks/` and `runs/`) covering:

- **Who-wins distribution** across topics; agree-vs-disagree outcome rates.
- **Drift / capture frequency** — how often the controller had to nudge each side
  (direct evidence the anti-sycophancy design works).
- **Token & latency per round**, per agent, per topic.
- Optional parameter exploration: effect of `MAX_WORDS` / `ROUNDS` / model choice on
  debate quality and cost.

## 10. Costs & pricing (guideline §11)

- **Cost-breakdown table** per run and aggregate: input/output tokens × price per
  model → total cost (per model and overall). Implemented in task 15.2: a completed
  `DebateResult` carries a per-model `cost_breakdown` (`CostBreakdown` / `ModelCostRow`)
  plus the overall total in `totals.cost_usd`, priced from the config-driven price
  table (§15.1, `config/model_prices.json`). `format_cost_table(breakdown)` renders
  the markdown table (model | input tokens | output tokens | $input | $output |
  $total, with an overall row); `aggregate_costs([...])` sums many runs into one
  table. Example (one run, opus debaters):

  | Model | Input tokens | Output tokens | $ Input | $ Output | $ Total |
  | --- | --- | --- | --- | --- | --- |
  | anthropic:claude-opus-4-8 | 1000000 | 200000 | $15.000000 | $15.000000 | $30.000000 |
  | Overall | 1000000 | 200000 | $15.000000 | $15.000000 | $30.000000 |
- **Budget management** (task 15.3): a **configurable budget cap** — `BUDGET_USD`
  (PRD §7, default `0` = unlimited) → `DebateConfig.budget_usd`. After a run is priced
  (15.2) the engine compares the cost-breakdown total against the cap via the pure
  `check_budget(spent_usd, budget_usd) -> BudgetStatus` (in
  `packages/core/.../pricing/budget.py`); on an overrun `alert_over_budget(status, …)`
  emits a structured **over-budget alert** — a `system` event carrying
  `payload.budget_alert = true` plus `spent_usd`/`budget_usd`/`remaining_usd` — into the
  per-run `runs/<run_id>.jsonl` log via the LOG package (no alert when under the cap or
  unlimited, so existing behaviour is unchanged). The alert is greppable/queryable for
  monitoring and surfaced to the UI/CLI alongside the cost table.

- **Cost vs. scale (rounds × word limit).** Cost is driven by tokens, and tokens scale
  with both knobs. Each round adds **one Pro + one Con message**, so output tokens grow
  **linearly in `ROUNDS`**. The per-message `MAX_WORDS` cap bounds each message's output
  tokens (≈ `1.3 × words` for English), so output also grows **linearly in `MAX_WORDS`**.
  Input tokens grow **faster than linearly**: every turn re-sends the side anchor + the
  adversarial relay of the opponent's last message, and the running transcript/context
  lengthens as the debate proceeds — so doubling `ROUNDS` more than doubles total input
  tokens (roughly quadratic in the worst case where full history is replayed). Net rule
  of thumb: **total cost ≈ `k₁ · ROUNDS · MAX_WORDS` (output) + `k₂ · ROUNDS² · MAX_WORDS`
  (input context)**, priced per model from `config/model_prices.json`. Practical levers,
  cheapest first: lower `MAX_WORDS`, lower `ROUNDS`, route debaters to a cheaper model
  (e.g. Haiku via `DEBATER_MODEL`), and set a `BUDGET_USD` cap so a runaway run is flagged
  early rather than discovered on the bill. Example: at the Opus example price ($15/1M in,
  $75/1M out) a 10-round, 150-word debate lands in the low-single-dollar range; halving
  both `ROUNDS` and `MAX_WORDS` cuts that by roughly 4× (output halves twice; input drops
  more).

## 11. Acceptance criteria

- [ ] A debate runs end-to-end: 10 Pro + 10 Con messages, alternating, each within the word limit.
- [ ] Debaters demonstrably **rebut** the opponent's last message (not isolated monologues).
- [ ] Each debater **uses web search** at least when relevant, and has ≥2 skills named in its system prompt.
- [ ] Controller never leaks its stance; detects ≥1 staged drift case and nudges the agent back.
- [ ] A turn that exceeds the timeout is killed and retried automatically.
- [ ] Controller outputs a final **summary + agree/disagree result + who won** (no fact-checking).
- [ ] All five surfaces (UI, CLI, API, SDK, LOG) work; logs capture every event with `run_id`.
- [ ] No secrets in repo; `ruff` = 0 violations, type checks pass, tests pass in CI.
- [ ] **Every external call goes through the API gatekeeper**; rate limits come from `config/rate_limits.json`; overflow is queued (no drops/crash).
- [ ] **Test coverage ≥ 85%** enforced (`fail_under = 85`); TDD followed.
- [ ] **No code file exceeds 150 lines**; no hard-coded values; SDK-centred, no duplication.
- [ ] A **version module starts at `1.00`**; the **Prompt Book** (`PROMPTS.md`) is maintained.
- [ ] Dedicated **sub-PRDs** exist for orchestration, anti-sycophancy, the gatekeeper, and the search plug-in.
- [ ] **Research notebook + visualizations** produced (who-wins, drift frequency, tokens/latency).
- [ ] **Cost-breakdown table** (tokens × price → total) reported; budget cap + alert work.
- [ ] **Sample debate runs are committed to the repo** (`runs/`) so the teacher can review real runs (transcript + verdict + token/cost). See TASKS.md §12.5.

## 12. Open questions / future work

- Cross-provider defaults for stronger anti-sycophancy (currently opt-in).
- Tavily as an alternative search backend behind the same interface.
- Multi-topic tournament + Elo scoring of debaters.
- Human-in-the-loop override of the controller's verdict.

## 13. Milestones

1. **M1 — Scaffold:** uv workspace, packages, config (+ `rate_limits.json`), version module `1.00`, LOG, CI (ruff/mypy/coverage-gate/150-line check).
2. **M2 — SDK core:** API gatekeeper, agents, skills (web_search/build_argument/analyze), relay-based orchestration, timeout+retry.
3. **M3 — Controller:** drift detection, nudging, verdict.
4. **M4 — Surfaces:** CLI → API → UI.
5. **M5 — Hardening & analysis:** security gatekeeper, tests (≥85%, edge cases), research notebook + visualizations, cost-breakdown report, docs, sample runs committed.
