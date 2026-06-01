# Improvements to Keep in Mind

> Distilled from the Assignment 1 feedback report and the lecturer's software
> guidelines. Only the points that apply to **this** project (`agent_debate`)
> are kept — the ML/signal-specific notes from the previous assignment were
> dropped because they don't apply here.

These are the things we lost points on or that the guidelines emphasise. Treat
them as a standing checklist for the debate system.

## Planning & documentation
- [x] Ship a **PRD up front** (see `PRD.md`): the problem, the goals, the design — written *before* the code, so a new team member understands the vision without asking us. — `docs/PRD.md` (committed before implementation; full goals/design/§8 standards); `docs/ARCHITECTURE.md` + `docs/prds/*.md` per-epic specs.
- [x] Keep docs current as the design evolves; document the *why* behind technical decisions, not just the *what*. — Module docstrings cite the *why* + PRD section (e.g. `core/security/sanitiser.py`, `scripts/secret_scan.py`); `docs/PRD.md`/`TASKS.md`/`PROMPTS.md` kept in sync. (Ongoing upkeep owned by task D.6.)
- [x] README must let any developer install and run the project with zero prior knowledge. — `README.md` Installation + Usage/Quickstart for all five surfaces, prerequisites table, dev-gates section, config table.

## Configuration & security
- [x] Config must be **portable**: it should set up cleanly in a completely different environment by someone who has never seen it. No hardcoded paths or environment assumptions. — All runtime config from env/`.env` via `core/settings.py`; price/rate-limit tables under `config/*.json`; `uv sync` reproduces the env from the lockfile.
- [x] **No secrets in the repo.** API keys (LLM provider keys, etc.) come from environment / `.env`, never committed. Ship a `.env.example`. — `.env` is git-ignored (not tracked); `.env.example` ships safe placeholders; `scripts/secret_scan.py` gate (clean on tracked tree) + runtime LOG redaction (`log/redaction.py`).
- [x] We need a real **gatekeeper / security layer** — validate and sanitise anything that crosses a trust boundary (user input, tool output, web-search results fed back to the model). Don't let untrusted text drive privileged actions. — Security gatekeeper `core/security/sanitiser.py` (normalise + neutralise injection + length-cap; web-search results routed through it) and API/rate-limit gatekeeper `core/gatekeeper/` (Epic 13) through which every external call is routed.

## Costs & resource awareness
- [x] Document and reason about **what the system costs to operate** (LLM token usage per debate, per round) and how that scales. Word limits per agent directly bound this — make the cost model explicit. — `docs/PRD.md` §10 "Costs & pricing" + "Cost vs. scale"; per-run `CostBreakdown`/`format_cost_table` (`core/pricing`, config-driven `config/model_prices.json`); `MAX_WORDS`/`ROUNDS`/`BUDGET_USD` env caps bound it.

## Extensibility
- [x] Design for change: clean separation of concerns so a new provider, a new agent skill, or a new UI can be added without breaking what already works. This is why we use a provider-agnostic LLM layer (no ecosystem lock-in). — Workspace split into `core`/`log`/`cli`/`api`/`ui` packages; provider-agnostic via pydantic-ai `provider:model` strings; pluggable `SearchProvider` backends (`SEARCH_BACKEND`); skills under `core/skills`.

## Quality standards
- [x] Establish **automated quality tooling** beyond manual review: linter + formatter (`ruff`), type checks, and tests wired into CI / pre-commit. — `.github/workflows/ci.yml` runs ruff check + format, mypy, pytest --cov (≥85% gate), line-limit + secret-scan on every push/PR. Verified locally: ruff 0, format clean, mypy clean.
- [x] **Testing**: rigorous tests across meaningful scenarios including edge cases (timeouts, agent going off-track, empty/failed web search, malformed model output). — Suite at 99% coverage; edge-case tests for turn timeouts/retries, anchoring/off-track nudges, empty/failed search, malformed model output, injection sanitisation.

## Output clarity (UI / logs / visualization)
- [x] Make behaviour legible at a glance: the **log system** and **UI/CLI** must clearly show, for each round, who said what, the controller's nudges, and the final verdict — layered so the relationship between arguments is obvious. — Structured LOG events (`log/event.py`) per turn/nudge/verdict; CLI live renderer (`cli/_live.py`, `_render.py`) and UI (`packages/ui`) show per-round speaker, controller actions and final verdict.
- [x] Don't collapse everything into one overloaded view; separate the streams (per-agent transcript, controller actions, system logs). — Streams are distinct: per-agent transcript vs controller nudges vs system logs (JSONL sink per `run_id` + pretty console), rendered as separate layers in CLI/UI.

## Process
- [x] Maintain disciplined **version control** with a visible development history, including the AI-assisted workflow. — 300+ commits with per-task branches/PRs; version module from `1.00` (PRD §8); AI-assisted workflow captured in `.building_tasks_logs/*.json` (102 task logs) and `docs/PROMPTS.md`.
