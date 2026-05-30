#!/usr/bin/env python3
"""Create one detailed GitHub issue per task in docs/TASKS.md.

Each issue contains: what to do, a ready-to-run IMPLEMENTATION PROMPT for a coding
agent, acceptance criteria, and a REQUIRED logging block instructing the implementer
to save the prompt + token usage to `.building_tasks_logs/<id>-<slug>.json`.

Idempotent: skips any task whose issue title already exists. Run from the repo root:
    python3 scripts/create_issues.py            # create
    python3 scripts/create_issues.py --dry-run  # print, create nothing
"""
from __future__ import annotations

import json
import subprocess
import sys

DRY = "--dry-run" in sys.argv

# Shared rules appended to every implementation prompt.
RULES = (
    "Follow repo standards: TDD (write the failing test first, then code); "
    "max 150 lines per code file (split, don't compress); ruff = 0 violations + mypy clean; "
    "no hard-coded values (read from config); every external API call goes through the API "
    "gatekeeper (Epic 13); log via the LOG package; keep coverage >= 85%. "
    "Read docs/PRD.md and the relevant docs/prds/*.md before starting."
)


def sh(args: list[str]) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def existing_titles() -> set[str]:
    out = sh(["gh", "issue", "list", "--state", "all", "--limit", "1000", "--json", "title"])
    return {i["title"] for i in json.loads(out)}


def ensure_labels(labels: set[str]) -> None:
    have = set()
    try:
        have = {l["name"] for l in json.loads(sh(["gh", "label", "list", "--limit", "200", "--json", "name"]))}
    except Exception:
        pass
    palette = {"P0": "B60205", "P1": "D93F0B", "P2": "FBCA04", "task": "0E8A16"}
    for lab in sorted(labels):
        if lab in have:
            continue
        color = palette.get(lab, "5319E7" if lab.startswith("epic") else "C5DEF5")
        if DRY:
            print(f"[label] {lab}")
            continue
        subprocess.run(["gh", "label", "create", lab, "--color", color, "--force"],
                       capture_output=True, text=True)


def body(t: dict) -> str:
    refs = "docs/PRD.md · docs/TASKS.md"
    if t.get("prd"):
        refs += " · " + t["prd"]
    return f"""## {t['id']} — {t['title']}

**Epic {t['epic']}** · **Priority {t['prio']}** · **Depends on:** {t.get('deps') or '—'}
**Refs:** {refs}

### What to do
{t['what']}

### Implementation prompt — run this to implement the issue
> Copy this prompt to the coding agent. Save the prompt you actually run (verbatim) in the log file below.

```text
{t['prompt']}

{RULES}
```

### ✅ Acceptance criteria
{t['accept']}

### 📋 Required — record the prompt & tokens (all three, per guideline §8.3 + §11.1)

**a) Per-task build log.** Copy `.building_tasks_logs/_template.json` to
**`.building_tasks_logs/{t['id']}-{t['slug']}.json`** and fill it in:
- `task_id`: `"{t['id']}"`, plus `title`, `date`, `model`
- `prompt`: the implementation prompt you actually ran (verbatim)
- `tokens`: `{{ "input": …, "output": …, "total": … }}` for this task

**b) Prompt Book (guideline §8.3).** If this task involved a *significant* prompt,
add an entry to **`docs/PROMPTS.md`** (context, goal, the prompt, what it produced,
any iteration/lesson).

**c) Token cost table (guideline §11.1).** Add this task's token counts to the
cost-breakdown table (model · input tokens · output tokens · cost) — see Epic 15 /
`docs/PRD.md §10`.

Commit all of the above in the **same PR** and reference this issue in the commit
message (e.g. `closes #<this-issue>`).
"""


def make(epic, prio, id, title, slug, what, prompt, accept, deps="", prd=""):
    return dict(epic=epic, prio=prio, id=id, title=title, slug=slug, what=what,
                prompt=prompt, accept=accept, deps=deps, prd=prd)


TASKS: list[dict] = []
A = TASKS.append

# ───────────────────────── Epic 0 — scaffold & quality gates ─────────────────────────
A(make(0, "P0", "0.1", "Init uv workspace", "init-uv-workspace",
  "Create the root `pyproject.toml` declaring a uv workspace over `packages/*`.",
  "Create a root pyproject.toml that defines a uv workspace with [tool.uv.workspace] members = [\"packages/*\"]. Set the project name, python requirement >=3.12, and shared dev-deps (ruff, mypy, pytest, pytest-cov). Verify `uv sync` resolves.",
  "Root pyproject.toml exists; `uv sync` succeeds; workspace members are discovered."))
A(make(0, "P0", "0.2", "Create the five package skeletons", "package-skeletons",
  "Create `packages/{core,log,api,cli,ui}`, each an importable package with its own pyproject.toml and `__init__.py`.",
  "Create five packages under packages/: core, log, api, cli, ui. Each has a pyproject.toml (name agent_debate_<pkg>), an __init__.py, and a src layout. core is the SDK; log is the logging package; api/cli/ui are surfaces. Keep each file tiny.",
  "All five packages import cleanly; `uv sync` includes them as workspace members.", deps="0.1"))
A(make(0, "P0", "0.3", "Wire intra-workspace dependencies", "wire-deps",
  "Declare workspace deps: core/api/cli/ui depend on log; api/cli/ui depend on core.",
  "In each package pyproject.toml, add the intra-workspace dependencies using uv workspace sources: api/cli/ui/core depend on agent_debate_log; api/cli/ui depend on agent_debate_core. Verify imports resolve across packages.",
  "Cross-package imports work (e.g. api imports core and log).", deps="0.2"))
A(make(0, "P0", "0.4", "Pin Python and lock deps", "pin-python-lock",
  "Pin Python `>=3.12`, generate `uv.lock`, confirm a clean `uv sync`.",
  "Set requires-python >=3.12 across packages. Run uv lock to produce uv.lock and commit it. Verify `uv sync` is clean and reproducible from scratch.",
  "uv.lock committed; `uv sync` reproducible on a fresh clone.", deps="0.1"))
A(make(0, "P0", "0.5", "Add ruff + mypy config (0 violations)", "ruff-mypy",
  "Configure ruff (lint+format) and mypy/pyright in the root pyproject; target 0 violations.",
  "Add [tool.ruff] (enable E,F,I,UP,B etc.) and [tool.mypy] strict-ish config to the root pyproject. Ensure `ruff check .` and `ruff format --check .` and `mypy` all pass on the skeleton.",
  "`ruff check .` = 0 violations; mypy passes on the skeleton.", deps="0.1"))
A(make(0, "P0", "0.6", "Add pytest + a trivial test per package", "pytest-bootstrap",
  "Set up pytest and a passing smoke test in each package so TDD is possible from day one.",
  "Configure pytest (and pytest-cov) at the root. Add tests/ per package with one trivial passing test (e.g. asserts __version__ importable). Ensure `uv run pytest` is green.",
  "`uv run pytest` passes with at least one test per package.", deps="0.2"))
A(make(0, "P0", "0.7", "Add .gitignore and .env.example", "gitignore-envexample",
  "Add `.gitignore` and a complete `.env.example` listing every PRD §7 variable.",
  "Create .gitignore (.venv, __pycache__, *.pyc, .env, .ruff_cache, .mypy_cache, .pytest_cache). Create .env.example with every variable from PRD §7 (ANTHROPIC_API_KEY, DEBATER_MODEL, CONTROLLER_MODEL, PRO_MODEL, CON_MODEL, ROUNDS, MAX_WORDS, TURN_TIMEOUT_S, MAX_RETRIES, SEARCH_BACKEND, SEARCH_API_KEY) with safe placeholder values and comments.",
  ".env.example covers all PRD §7 vars; .env is gitignored; no real secrets committed.", deps="0.1"))
A(make(0, "P0", "0.8", "CI quality gates (set up EARLY)", "ci-quality-gates",
  "GitHub Actions on every push/PR: uv sync → ruff(0) → mypy → pytest --cov(85) → 150-line check → secret scan. Gates before features.",
  "Create .github/workflows/ci.yml that, on push and pull_request, runs (in order, failing the build on any failure): uv sync; ruff check .; ruff format --check .; mypy; pytest --cov with fail_under=85; the 150-line check script (task 0.10); the secret scan (task 0.11). Use the official astral-sh/setup-uv action.",
  "CI runs all gates on every push/PR and fails if any gate fails; pipeline is green on the scaffold.", deps="0.5, 0.6"))
A(make(0, "P0", "0.9", "Coverage gate >= 85%", "coverage-gate",
  "Configure coverage with `fail_under = 85` so the suite fails below threshold (guideline §6.2).",
  "Add [tool.coverage.run] (source = packages) and [tool.coverage.report] fail_under = 85 to pyproject. Wire `pytest --cov --cov-report=term-missing` into CI so it fails under 85%.",
  "Coverage below 85% fails the build locally and in CI.", deps="0.5"))
A(make(0, "P0", "0.10", "150-line-per-file check script", "line-limit-check",
  "A script that fails the build when any code file exceeds 150 code lines (excluding blanks/comments), per guideline §3.2.",
  "Write scripts/check_line_limit.py that walks packages/**/*.py, counts code lines excluding blank and comment-only lines, and exits non-zero listing any file > 150. Wire it into CI (0.8).",
  "A file over 150 code lines fails the check; the script is in CI.", deps="0.5"))
A(make(0, "P0", "0.11", "Secret-scan check in CI", "secret-scan",
  "Fail CI if a key-like secret is committed; ensure `.env.example` present and 0 secrets in source (guideline §7.4).",
  "Add a secret scan to CI (e.g. gitleaks action, or a regex script for sk-…, api keys, tokens). Ensure it scans the diff/tree and fails on a hit. Confirm .env.example exists and contains only placeholders.",
  "Committing a key-like string fails CI; no secrets exist in source.", deps="0.8"))
A(make(0, "P1", "0.12", "Root README (guideline §2.1)", "root-readme",
  "Write the root README: what it is, system requirements, step-by-step install, usage, troubleshooting, doc links.",
  "Write README.md per guideline §2.1: project summary, system requirements, step-by-step install (uv sync + .env setup), quickstart usage for CLI/API/UI/SDK, troubleshooting, and links to docs/ (PRD, TASKS, prds/, guidelines).",
  "A new developer can install and run from the README alone.", deps="0.2"))
A(make(0, "P0", "0.13", "Version module starting at 1.00", "version-module",
  "Add `__version__ = \"1.00\"` in core, re-exported by the SDK (guideline §8.1).",
  "Add a version module in packages/core (e.g. core/_version.py with __version__ = \"1.00\") and re-export it from the SDK package __init__. Add a test asserting the version is importable and starts at 1.00.",
  "`agent_debate.__version__ == \"1.00\"`; covered by a test.", deps="0.2"))
A(make(0, "P0", "0.14", "config/rate_limits.json (versioned 1.00)", "rate-limits-config",
  "Create the rate-limit config file (guideline §5.2) consumed by the API gatekeeper; never hard-code limits.",
  "Create config/rate_limits.json with version \"1.00\" and services (default, anthropic, search) each with requests_per_minute, requests_per_hour, concurrent_max, retry_after_seconds, max_retries (see docs/prds/api-gatekeeper.md). It will be loaded by Epic 13.",
  "config/rate_limits.json exists, versioned 1.00, matches the api-gatekeeper sub-PRD shape.", deps="2.1", prd="docs/prds/api-gatekeeper.md"))
A(make(0, "P1", "0.15", "Branch protection requires CI", "branch-protection",
  "Require the CI check to pass before merging to main.",
  "Configure branch protection on main so the CI workflow must pass before merge (via GitHub settings or `gh api`). Document the rule in the README/CONTRIBUTING.",
  "PRs cannot merge to main unless CI is green.", deps="0.8"))

# ───────────────────────── Epic 1 — LOG ─────────────────────────
A(make(1, "P0", "1.1", "structlog setup factory", "log-setup",
  "Configure structlog with a pretty console sink (dev) and a per-run JSONL sink at `runs/<run_id>.jsonl`.",
  "In packages/log, add a configure() factory that sets up structlog with two sinks: a human-readable console renderer and a JSONL file writer to runs/<run_id>.jsonl. Make it idempotent.",
  "Calling the factory yields a logger writing both console and runs/<run_id>.jsonl.", deps="", prd="docs/PRD.md §5.8"))
A(make(1, "P0", "1.2", "Event schema model", "log-event-schema",
  "Define the typed log event: run_id, ts, round, agent, event_type, payload, tokens, latency_ms.",
  "Add a Pydantic model LogEvent with fields run_id, ts, round, agent, event_type (Literal of message|tool_call|nudge|timeout|retry|verdict|system), payload, tokens, latency_ms. Validate event_type.",
  "LogEvent validates allowed event_types and serialises to JSONL.", deps="1.1"))
A(make(1, "P0", "1.3", "Logger helper API", "log-helpers",
  "Provide `get_logger(run_id)`, `log_event(...)`, and context binding for run_id/round.",
  "Add helpers: get_logger(run_id) returns a bound logger; log_event(**fields) validates via LogEvent and emits; context binding so run_id/round propagate. Keep files <150 lines.",
  "Other packages log structured events with run_id/round bound.", deps="1.2"))
A(make(1, "P1", "1.4", "Redaction filter", "log-redaction",
  "Never log API keys/secrets; truncate oversized payloads.",
  "Add a structlog processor that redacts secret-like values (keys named *key*/*token*/*secret*, sk-… patterns) and truncates payloads over a configurable size. Add tests.",
  "Secrets never appear in console or JSONL output; large payloads truncated.", deps="1.1"))
A(make(1, "P1", "1.5", "LOG unit tests", "log-tests",
  "Test JSONL writing, schema validation, and redaction.",
  "Write pytest tests: an event is written to runs/<run_id>.jsonl and round-trips; invalid event_type rejected; redaction hides a fake key. Keep coverage high.",
  "Tests cover write, schema, redaction; coverage contributes to >=85%.", deps="1.3"))

# ───────────────────────── Epic 2 — Config & providers ─────────────────────────
A(make(2, "P0", "2.1", "Settings model", "settings-model",
  "pydantic-settings `Settings` loading all PRD §7 vars from env/.env with defaults.",
  "In packages/core, add a pydantic-settings Settings class with every PRD §7 field and sane defaults (ROUNDS=10, MAX_WORDS=150, TURN_TIMEOUT_S=60, MAX_RETRIES=2, SEARCH_BACKEND=duckduckgo). Load from environment and .env.",
  "Settings loads from env/.env; defaults match PRD §7.", deps=""))
A(make(2, "P0", "2.2", "Model resolver", "model-resolver",
  "Map model strings to Pydantic AI models so providers are swappable with no code change.",
  "Add a resolver mapping DEBATER_MODEL/CONTROLLER_MODEL/PRO_MODEL/CON_MODEL strings to Pydantic AI model instances. PRO/CON fall back to DEBATER_MODEL. Anthropic default; any provider via model string.",
  "Changing a model env var swaps providers with zero code changes.", deps="2.1"))
A(make(2, "P1", "2.3", "Validate required keys", "validate-keys",
  "Fail fast with a clear message when a required provider key is missing.",
  "On startup, validate that the active provider's key (e.g. ANTHROPIC_API_KEY) is present; raise a clear, actionable error if not.",
  "Missing key produces a helpful error, not a stack trace deep in the SDK.", deps="2.1"))
A(make(2, "P0", "2.4", "Confirm Anthropic model IDs", "confirm-model-ids",
  "Pin the exact current Anthropic model IDs and document them in .env.example.",
  "Determine the exact available Anthropic model IDs for debaters and controller, set them as defaults, and document in .env.example with comments.",
  "Defaults use valid, current model IDs; documented in .env.example.", deps="2.2"))
A(make(2, "P1", "2.5", "Config tests", "config-tests",
  "Test env loading, per-side fallback, and bad model strings failing loudly.",
  "Write tests: Settings loads from env; PRO/CON fall back to DEBATER_MODEL; an invalid model string raises clearly.",
  "Config behaviour covered by tests.", deps="2.2"))

# ───────────────────────── Epic 3 — Search plug-in ─────────────────────────
A(make(3, "P0", "3.1", "SearchProvider interface", "search-interface",
  "Define `SearchResult` model and the `SearchProvider` protocol.",
  "In packages/core search/base.py, define SearchResult (title,url,snippet) and a SearchProvider Protocol with name and search(query,*,max_results=5)->list[SearchResult]. Per docs/prds/search-plugin.md.",
  "Interface matches the search-plugin sub-PRD.", deps="", prd="docs/prds/search-plugin.md"))
A(make(3, "P0", "3.2", "Provider registry + factory", "search-registry",
  "Register providers by name; select the active one via `SEARCH_BACKEND`.",
  "Add a registry mapping names to SearchProvider classes and a factory that returns the provider for SEARCH_BACKEND. Swapping backends must be a one-line config change.",
  "Active provider is chosen from config; new providers register by name.", deps="3.1, 2.1"))
A(make(3, "P0", "3.3", "DuckDuckGoSearchProvider", "ddg-provider",
  "Default provider using `ddgs`/duckduckgo-search mapping to `SearchResult`.",
  "Implement DuckDuckGoSearchProvider using ddgs. Map raw results to SearchResult. No API key needed.",
  "Returns clean SearchResult list for a query.", deps="3.1"))
A(make(3, "P1", "3.4", "Search resilience", "search-resilience",
  "Timeout, retry/backoff, graceful empty-result handling (search is flaky).",
  "Wrap provider calls with a timeout and retry/backoff; return an empty list (not an exception) on persistent failure, logged.",
  "Flaky/failed search degrades gracefully without crashing a debate.", deps="3.3"))
A(make(3, "P2", "3.5", "Stub second provider", "stub-provider",
  "Prove swap-ability with a second provider (e.g. Tavily) behind the same interface.",
  "Add a TavilySearchProvider stub (key via SEARCH_API_KEY) implementing SearchProvider, registered under 'tavily', to prove a one-line swap with no engine changes.",
  "Switching SEARCH_BACKEND=tavily uses the stub with no engine edits.", deps="3.2"))
A(make(3, "P1", "3.6", "Search tests", "search-tests",
  "Test registry selection, DDG mapping, empty/error path, provider swap.",
  "Write tests: registry returns the configured provider; DDG mapping shape; empty/error path returns []; swapping to the stub needs no engine change (mock network).",
  "Search layer covered including failure and swap paths.", deps="3.3"))

# ───────────────────────── Epic 4 — Skills ─────────────────────────
A(make(4, "P0", "4.1", "web_search skill", "skill-web-search",
  "The mandatory `web_search` skill: call active provider via API gatekeeper, sanitise results via security gatekeeper.",
  "Implement a web_search(query) tool that calls the active SearchProvider THROUGH the API gatekeeper (Epic 13) and passes results THROUGH the security gatekeeper (Epic 7) before returning to the model. Provider-agnostic.",
  "Agents can search; calls are rate-limited and results sanitised.", deps="3.3, 7.1, 13.6", prd="docs/prds/search-plugin.md"))
A(make(4, "P0", "4.2", "build_argument skill", "skill-build-argument",
  "Skill to structure a persuasive argument/rebuttal for the agent's side.",
  "Implement build_argument(...) that helps a debater structure a persuasive argument or rebuttal for its assigned side (claim, support, link to opponent's point). Register as a Pydantic AI tool with validated inputs.",
  "Debaters can produce structured arguments via the skill.", deps=""))
A(make(4, "P0", "4.3", "analyze_opponent_argument skill", "skill-analyze",
  "Skill to dissect the opponent's last message and decide what to rebut.",
  "Implement analyze_opponent_argument(...) that takes the opponent's last message, surfaces weaknesses/assumptions, and returns what to rebut. Validated inputs.",
  "Debaters can analyse and target the opponent's points.", deps="4.2"))
A(make(4, "P0", "4.4", "Controller skills", "skill-controller",
  "Controller-only skills: assess_drift, nudge, render_verdict.",
  "Implement controller skills: assess_drift(message, side) -> {captured, reason, confidence}; nudge(agent, reason) -> private correction; render_verdict(transcript) -> structured verdict. See docs/prds/anti-sycophancy.md.",
  "Controller has working drift/nudge/verdict skills.", deps="4.3", prd="docs/prds/anti-sycophancy.md"))
A(make(4, "P0", "4.5", "Register skills as tools", "skill-register",
  "Register all skills as real Pydantic AI tools with validated inputs.",
  "Register every skill as a Pydantic AI tool with Pydantic input models. Ensure validation rejects malformed payloads. Group debater vs controller skill sets.",
  "Skills are callable tools; inputs validated.", deps="4.1, 4.2, 4.3, 4.4"))
A(make(4, "P1", "4.6", "Skill tests", "skill-tests",
  "Test each tool is callable, validates inputs, and web_search output is sanitised.",
  "Write tests for each skill: callable, input validation rejects bad payloads, web_search output passes through sanitisation (mock provider + gatekeepers).",
  "Skills covered including validation and sanitisation.", deps="4.5"))

# ───────────────────────── Epic 5 — Agents & prompts ─────────────────────────
A(make(5, "P0", "5.1", "Pro debater agent", "agent-pro",
  "Pro agent: system prompt = side FOR, rules (word limit, MUST rebut, don't concede), and its named skills.",
  "Create the Pro debater as a Pydantic AI Agent. System prompt states side=FOR, the rules (<=MAX_WORDS, must rebut the opponent, do not concede merely because the opponent sounds convincing), and EXPLICITLY lists its skills (web_search, build_argument, analyze_opponent_argument) and when to use them. See docs/prds/anti-sycophancy.md.",
  "Pro agent instantiates with the correct side, rules, and skill list in its prompt.", deps="", prd="docs/prds/anti-sycophancy.md"))
A(make(5, "P0", "5.2", "Con debater agent", "agent-con",
  "Con agent: mirror of Pro with side AGAINST.",
  "Create the Con debater mirroring Pro (task 5.1) with side=AGAINST and the same skill list and rules.",
  "Con agent instantiates with side AGAINST and the skill list.", deps="5.1"))
A(make(5, "P0", "5.3", "Controller agent", "agent-controller",
  "Controller agent: knows both sides, never reveals its own stance, instructed to detect drift and nudge.",
  "Create the Controller as a Pydantic AI Agent. Prompt: it moderates/judges, knows both assigned sides, must NEVER reveal its own opinion or which side it leans, detects drift and nudges, and at the end renders a verdict. Give it the controller skills.",
  "Controller prompt never leaks stance; has drift/nudge/verdict skills.", deps="5.1", prd="docs/prds/anti-sycophancy.md"))
A(make(5, "P0", "5.4", "Independent agent contexts", "agent-contexts",
  "Each agent has its own conversation context; debaters never share a thread.",
  "Ensure each agent keeps its own message history. The two debaters must NOT share a conversation thread (anti-sycophancy). Wire separate context objects per agent.",
  "Debaters have isolated contexts; no shared thread.", deps="5.1, 5.2", prd="docs/prds/anti-sycophancy.md"))
A(make(5, "P0", "5.5", "Per-turn side anchoring", "side-anchoring",
  "Re-inject the agent's side + anti-concession reminder on every turn.",
  "Before each debater turn, re-inject its assigned side (FOR/AGAINST) and an explicit 'do not concede merely because the opponent is convincing' instruction.",
  "Every turn re-anchors the agent's side.", deps="5.4", prd="docs/prds/anti-sycophancy.md"))
A(make(5, "P0", "5.6", "Adversarial relay", "adversarial-relay",
  "Inject the opponent's message framed as 'Your opponent argued: «…». Rebut it.'",
  "Implement the relay that passes the opponent's last message into an agent framed adversarially ('Your opponent argued: «…». Rebut it.'), NOT as an agreeable peer turn.",
  "Opponent messages arrive framed adversarially.", deps="5.4", prd="docs/prds/anti-sycophancy.md"))
A(make(5, "P0", "5.7", "Word-limit enforcement", "word-limit",
  "Enforce MAX_WORDS in prompt and verify/trim post-generation; log violations.",
  "Instruct the word limit in the prompt AND verify after generation: if over MAX_WORDS, trim and log a violation event. Keep messages within the limit.",
  "Messages never exceed MAX_WORDS; violations logged.", deps="5.5"))
A(make(5, "P1", "5.8", "Agent/prompt tests", "agent-tests",
  "Test prompts include skills, controller hides stance, relay framing present, word limit enforced.",
  "Write tests asserting: debater prompts list their skills; controller prompt contains no stance leak; relay framing is adversarial; over-limit output is trimmed.",
  "Anti-sycophancy + prompt invariants covered by tests.", deps="5.6"))

# ───────────────────────── Epic 6 — Engine / SDK ─────────────────────────
A(make(6, "P0", "6.1", "DebateConfig + DebateResult", "engine-models",
  "Typed config and result models (transcript, tool calls, nudges, verdict, token/cost totals).",
  "Define DebateConfig (rounds, max_words, models, timeout, retries) and DebateResult (transcript, tool_calls, nudges, closing_discussion, verdict, token/cost totals). See docs/prds/debate-orchestration.md.",
  "Config/result models match the orchestration sub-PRD.", deps="", prd="docs/prds/debate-orchestration.md"))
A(make(6, "P0", "6.2", "Topic setup & private assignment", "engine-setup",
  "Controller sets topic, privately assigns Pro/Con, hides its own stance.",
  "Implement setup: controller receives/sets the topic, privately assigns Pro=FOR and Con=AGAINST, and keeps its own stance hidden from everyone.",
  "Topic assigned; controller stance hidden.", deps="5.3", prd="docs/prds/debate-orchestration.md"))
A(make(6, "P0", "6.3", "Main 10v10 loop", "engine-loop",
  "10 rounds alternating Pro → drift check → Con → drift check; 10 messages each.",
  "Implement the debate loop for ROUNDS rounds: Pro turn, controller drift-check (+nudge), Con turn (must rebut), controller drift-check (+nudge). Exactly 10 Pro + 10 Con messages. Log every message/tool_call/nudge.",
  "Produces 10 Pro + 10 Con alternating messages with drift checks.", deps="5.6, 6.2", prd="docs/prds/debate-orchestration.md"))
A(make(6, "P0", "6.4", "Timeout + retry wrapper", "engine-timeout",
  "Wrap every model call: cancel on TURN_TIMEOUT_S, retry up to MAX_RETRIES, then fail the turn + inform controller.",
  "Implement a wrapper around every model call: enforce TURN_TIMEOUT_S, cancel on timeout, retry up to MAX_RETRIES with backoff; after exhaustion mark the turn failed and inform the controller. Log timeout/retry events.",
  "A hung turn is cancelled and retried; exhausted retries handled gracefully.", deps="6.3", prd="docs/prds/debate-orchestration.md"))
A(make(6, "P0", "6.5", "Closing discussion phase", "engine-closing",
  "A freer exchange after the 10 rounds, before the verdict.",
  "After the main loop, run a closing discussion phase where each agent responds more freely to the other before judgement. Log it.",
  "A closing discussion runs before the verdict.", deps="6.3"))
A(make(6, "P0", "6.6", "Event streaming", "engine-streaming",
  "Yield ordered events (message/tool_call/nudge/verdict) for live consumers.",
  "Make the engine yield/stream events as they happen so CLI/API/UI can render live. Events are ordered and typed.",
  "Consumers receive ordered live events.", deps="6.3"))
A(make(6, "P1", "6.7", "Token/cost accounting", "engine-cost",
  "Accumulate per-turn token usage into DebateResult totals.",
  "Capture token usage per model call and aggregate into DebateResult (per agent, per round, totals). Feed the LOG package. This supports Epic 15 cost reporting.",
  "DebateResult includes token totals per agent and overall.", deps="6.3, 1.2"))
A(make(6, "P0", "6.8", "Public SDK entrypoint", "engine-sdk",
  "`from agent_debate import DebateEngine; DebateEngine(config).run(topic)`.",
  "Expose the public SDK: DebateEngine(config).run(topic) -> DebateResult, plus a streaming variant. This is THE library surface other packages use.",
  "SDK runs a full debate and returns DebateResult.", deps="6.1, 6.2, 6.3, 6.4, 6.5, 6.6"))
A(make(6, "P1", "6.9", "Engine tests (mocked LLM)", "engine-tests",
  "Full 10v10 run; timeout→retry; failed turn; ordered streaming — all with a mocked LLM.",
  "Write tests with a mocked LLM: a full debate yields 10+10 messages; a simulated timeout triggers cancel+retry; an exhausted-retry turn is handled; streamed events are ordered. No network.",
  "Engine behaviour covered without real API calls.", deps="6.8"))

# ───────────────────────── Epic 7 — Security gatekeeper ─────────────────────────
A(make(7, "P0", "7.1", "Sanitisation gatekeeper", "secgate-sanitise",
  "Sanitise untrusted text (topic, search results, model output) before it re-enters a prompt.",
  "Implement the security gatekeeper: sanitise/normalise untrusted text (user topic, web-search results, model output) to defend against prompt-injection before it re-enters any prompt. Distinct from the API gatekeeper (Epic 13). See PRD §5.7.",
  "Untrusted text is sanitised before reaching a model.", deps="", prd="docs/PRD.md §5.7"))
A(make(7, "P1", "7.2", "Input validation", "secgate-validation",
  "Topic length/charset caps; search-query caps; reject control sequences.",
  "Add input validation: cap topic length/charset, cap search query length, reject control/escape sequences. Clear errors on rejection.",
  "Abusive/oversized inputs are rejected with clear errors.", deps="7.1"))
A(make(7, "P0", "7.3", "No code execution from output", "secgate-noexec",
  "No arbitrary code execution from model/tool output; tool args strictly typed.",
  "Audit that no model/tool output is ever eval'd/exec'd or used to build shell/SQL. Ensure all tool args are strictly typed Pydantic models.",
  "No path executes model-produced code; tool args strictly typed.", deps="4.5"))
A(make(7, "P1", "7.4", "Secret hygiene check", "secgate-secrets",
  "CI fails if a key-like string is committed (coordinated with 0.11).",
  "Ensure the secret hygiene check (see task 0.11) covers source and logs; add a test that the LOG redaction + scan catch a planted fake key.",
  "Planted secret is caught by CI and never logged.", deps="0.8"))
A(make(7, "P1", "7.5", "Security tests", "secgate-tests",
  "Injection payload in a search result is neutralised; oversized input rejected.",
  "Write tests: a prompt-injection payload embedded in a search result does not change agent behaviour; oversized/abusive input is rejected.",
  "Injection + abuse paths covered by tests.", deps="7.1"))

# ───────────────────────── Epic 8 — Controller intelligence ─────────────────────────
A(make(8, "P0", "8.1", "assess_drift logic", "ctrl-drift",
  "After each message decide if the agent still defends its side or has been captured.",
  "Implement assess_drift: classify whether a debater still defends its assigned side or has started agreeing with/restating the opponent. Return {captured, reason, confidence}. See docs/prds/anti-sycophancy.md.",
  "Drift is detected with reason + confidence.", deps="4.4, 6.3", prd="docs/prds/anti-sycophancy.md"))
A(make(8, "P0", "8.2", "nudge logic", "ctrl-nudge",
  "Private correction when captured; logged + shown in UI; not a debate turn.",
  "Implement nudge: when assess_drift reports capture, the controller sends a private correction to that agent. Log it and surface in the UI, but DO NOT count it as a debate turn.",
  "Captured agents are nudged back; nudges logged, not counted as turns.", deps="8.1"))
A(make(8, "P0", "8.3", "Verdict", "ctrl-verdict",
  "Summary + whether agents agreed + result + who won (+ reasoning). No fact-checking.",
  "Implement render_verdict: the controller writes a summary of the debate, whether the agents converged/agreed, the result, and WHO WON with reasoning — judged on argumentation/rebuttal/engagement, NOT factual correctness (no fact-checking).",
  "Structured verdict with a winner and reasoning; no fact-checking.", deps="6.5"))
A(make(8, "P1", "8.4", "Staged-drift test fixture", "ctrl-drift-test",
  "Force an agent to parrot the opponent; assert the controller nudges it back.",
  "Add a test fixture that forces a debater to parrot/concede to the opponent and assert assess_drift flags it and nudge corrects it at least once.",
  "Staged drift is detected and nudged in a test.", deps="8.2"))

# ───────────────────────── Epic 9 — CLI ─────────────────────────
A(make(9, "P0", "9.1", "Typer CLI app", "cli-app",
  "`agent-debate run \"<topic>\" [--rounds --max-words --model --search-backend]`.",
  "Build a Typer CLI with a run command taking a topic and options (--rounds, --max-words, --model, --search-backend). It drives the SDK (DebateEngine).",
  "`agent-debate run \"...\"` starts a debate via the SDK.", deps=""))
A(make(9, "P1", "9.2", "Live transcript rendering", "cli-render",
  "Render Pro/Con per round + inline controller nudges (Rich).",
  "Use Rich to render the live transcript: Pro and Con messages per round with inline controller nudges, and the final verdict.",
  "Terminal shows a readable live transcript + verdict.", deps="6.6"))
A(make(9, "P1", "9.3", "--json output", "cli-json",
  "Machine-readable DebateResult; non-zero exit on failure.",
  "Add --json to print the DebateResult as JSON; exit non-zero on failure.",
  "`--json` emits the full result; failures exit non-zero.", deps="6.8"))
A(make(9, "P1", "9.4", "CLI tests", "cli-tests",
  "CLI runs a mocked debate and prints transcript + verdict.",
  "Write tests running the CLI against a mocked engine, asserting transcript + verdict are printed and exit codes are correct.",
  "CLI covered with a mocked engine.", deps="9.1"))

# ───────────────────────── Epic 10 — API ─────────────────────────
A(make(10, "P0", "10.1", "FastAPI app", "api-app",
  "FastAPI + Uvicorn entrypoint.",
  "Create a FastAPI app with a Uvicorn entrypoint in packages/api, wired to the SDK.",
  "API server starts and is healthy.", deps=""))
A(make(10, "P0", "10.2", "Debate endpoints", "api-endpoints",
  "`POST /debates` (start, returns run_id), `GET /debates/{id}` (status/result).",
  "Implement POST /debates (start a debate, return run_id) and GET /debates/{id} (status + result). Validate requests.",
  "Debates can be started and fetched over HTTP.", deps="6.8"))
A(make(10, "P1", "10.3", "SSE stream endpoint", "api-stream",
  "`GET /debates/{id}/stream` streams live events (SSE).",
  "Add GET /debates/{id}/stream that streams engine events via Server-Sent Events for live consumers.",
  "Clients receive live events over SSE.", deps="6.6"))
A(make(10, "P1", "10.4", "Validation, errors, CORS", "api-hardening",
  "Request validation, error handling, CORS for the UI.",
  "Add request validation, consistent error responses, and CORS configured for the UI origin.",
  "API validates input, handles errors, and allows the UI origin.", deps="10.2"))
A(make(10, "P1", "10.5", "API tests", "api-tests",
  "start → poll → result; stream emits events (mocked engine).",
  "Write tests (mocked engine): POST then GET returns status/result; the stream endpoint emits events.",
  "API endpoints covered with a mocked engine.", deps="10.3"))

# ───────────────────────── Epic 11 — UI ─────────────────────────
A(make(11, "P1", "11.1", "Topic input page", "ui-input",
  "Web page to enter a topic and start a debate via the API.",
  "Build a web page with a topic input that starts a debate via the API. Keep it simple and clean.",
  "User can start a debate from the UI.", deps=""))
A(make(11, "P1", "11.2", "Live streaming transcript", "ui-stream",
  "Consume the SSE endpoint and render Pro vs Con live.",
  "Consume GET /debates/{id}/stream and render the Pro vs Con transcript live as it streams.",
  "Transcript streams live in the UI.", deps="10.3"))
A(make(11, "P1", "11.3", "Separate panels", "ui-panels",
  "Distinct panels: debate transcript · controller actions/nudges · system log.",
  "Lay out three separate panels (don't overload one view): debate transcript, controller actions/nudges, and system log.",
  "Three clearly separated panels render their own streams.", deps="11.2"))
A(make(11, "P1", "11.4", "Verdict view", "ui-verdict",
  "Show summary, agree/disagree, who won, token cost.",
  "Add a verdict view showing the summary, whether agents agreed, who won, and token/cost totals.",
  "Final verdict + cost displayed clearly.", deps="11.2"))
A(make(11, "P2", "11.5", "RTL-safe styling", "ui-rtl",
  "Logical properties (start/end) per house CSS rules.",
  "Style the UI using CSS logical properties (text-start/end, ps-/pe-, ms-/me-, items-start/end) for RTL support; never left/right.",
  "UI works correctly in RTL.", deps="11.1"))
A(make(11, "P1", "11.6", "Nielsen heuristics", "ui-nielsen",
  "Apply Nielsen's 10 usability heuristics (guideline §10.1).",
  "Apply Nielsen's heuristics: visible system status (round/streaming indicator), error prevention/recovery, consistency, minimalist design, recognition over recall.",
  "UI satisfies the key Nielsen heuristics.", deps="11.4"))
A(make(11, "P1", "11.7", "Interface documentation", "ui-docs",
  "Annotated screenshots + UX walkthrough so the UI is understandable without running it (§10.2).",
  "Document the UI in docs/: annotated screenshots and a short UX walkthrough so a reader understands it without running it.",
  "UI documented with screenshots + walkthrough.", deps="11.4"))
A(make(11, "P2", "11.8", "UI smoke test", "ui-smoke",
  "Smoke test / screenshot of a completed debate.",
  "Add a smoke test or capture a screenshot of a completed debate for the docs/submission.",
  "A completed-debate screenshot/smoke test exists.", deps="11.4"))

# ───────────────────────── Epic 12 — Quality, docs & submission ─────────────────────────
A(make(12, "P1", "12.1", "Acceptance-criteria tests", "sub-acceptance-tests",
  "Tests covering every PRD §11 acceptance criterion; coverage on engine + both gatekeepers.",
  "Write/aggregate tests covering each PRD §11 acceptance criterion. Ensure coverage on the engine and both gatekeepers keeps total >=85%.",
  "Every PRD §11 criterion has a test; coverage >=85%.", deps=""))
A(make(12, "P1", "12.2", "Per-package + root READMEs", "sub-readmes",
  "READMEs for each package and a root quickstart for all five surfaces.",
  "Write a README per package and ensure the root README quickstart covers SDK, CLI, API, UI, LOG.",
  "Each surface is documented for a new developer.", deps="9, 10, 11"))
A(make(12, "P1", "12.4", "Architecture/decisions doc", "sub-architecture",
  "An architecture doc (or expanded PRD §5) for a new team member.",
  "Write an architecture/decisions doc (or expand PRD §5) explaining the system, packages, and key decisions for a new team member.",
  "A new team member can understand the design from the doc.", deps=""))
A(make(12, "P1", "12.4a", "Docstrings & comments", "sub-docstrings",
  "Docstrings on public modules/classes/functions; comments where logic is non-obvious (§3.3).",
  "Add docstrings to all public modules/classes/functions and meaningful comments where logic is non-obvious. Optionally enforce with ruff pydocstyle rules.",
  "Public API documented; non-obvious logic commented.", deps=""))
A(make(12, "P2", "12.4b", "ISO/IEC 25010 mapping", "sub-iso25010",
  "Map the system to ISO 25010 product-quality characteristics (§13).",
  "Add a short table mapping the system to ISO/IEC 25010 characteristics: functional suitability, reliability, performance efficiency, security, maintainability, portability — with how each is addressed.",
  "ISO 25010 mapping table exists in docs.", deps=""))
A(make(12, "P0", "12.5", "Generate & commit sample runs", "sub-sample-runs",
  "Run several debates and commit transcript + verdict + token/cost under runs/ for the teacher.",
  "Run several debates on varied topics and commit each run under runs/ as <run_id>.jsonl plus a readable <run_id>.md (transcript, verdict, token/cost). This is the evidence the teacher reviews.",
  "Multiple sample runs are committed under runs/.", deps="6.8, 8.3"))
A(make(12, "P1", "12.6", "runs/ index", "sub-runs-index",
  "Index of saved debates (topic, who won, link), linked from the root README.",
  "Create runs/README.md indexing each saved debate (topic, who won, link) and link it from the root README.",
  "runs/ has an index linked from the README.", deps="12.5"))
A(make(12, "P0", "12.7", "Final pass vs Improvements checklist", "sub-final-improvements",
  "Tick every box in docs/Improvements_to_keep_in_mind.md.",
  "Go through docs/Improvements_to_keep_in_mind.md and verify/tick every item; fix any gaps.",
  "Every Improvements item is satisfied.", deps=""))
A(make(12, "P0", "12.8", "Final pass vs lecturer guidelines", "sub-final-guidelines",
  "Verify against the software_submission_guidelines PDF; complete the §17 final checklist.",
  "Go through the lecturer's software_submission_guidelines-V3 and the §17 final checklist; verify each requirement is met and fix gaps.",
  "The guideline final checklist is fully satisfied.", deps=""))

# ───────────────────────── Epic 13 — API Gatekeeper ─────────────────────────
A(make(13, "P0", "13.1", "RateLimitConfig loader", "gate-config",
  "Load `config/rate_limits.json` (versioned 1.00); 0 hard-coded limits.",
  "Implement RateLimitConfig that loads config/rate_limits.json (per-service limits). No limit is hard-coded. See docs/prds/api-gatekeeper.md.",
  "Limits load from config; none hard-coded.", deps="0.14, 2.1", prd="docs/prds/api-gatekeeper.md"))
A(make(13, "P0", "13.2", "ApiGatekeeper.execute", "gate-execute",
  "Check limits → run → log every external call.",
  "Implement ApiGatekeeper.execute(api_call, *args, **kwargs): check rate limits before running, execute, and log every call (service, latency, outcome).",
  "All calls run through execute and are logged.", deps="13.1", prd="docs/prds/api-gatekeeper.md"))
A(make(13, "P0", "13.3", "FIFO overflow queue", "gate-queue",
  "Queue overflow (FIFO, max depth) with backpressure + drain — never drop/crash.",
  "Add a FIFO overflow queue with max depth from config: when a limit is hit, enqueue instead of dropping; signal backpressure when full; drain as rate windows reset.",
  "Overflow is queued and drained; never dropped/crashed.", deps="13.2", prd="docs/prds/api-gatekeeper.md"))
A(make(13, "P0", "13.4", "Retry + concurrency", "gate-retry",
  "Retry transient failures with backoff; enforce concurrent_max.",
  "Add retry-with-backoff on transient failures per config (max_retries, retry_after_seconds) and enforce concurrent_max.",
  "Transient failures retried; concurrency capped.", deps="13.2"))
A(make(13, "P1", "13.5", "get_queue_status", "gate-status",
  "Expose queue depth + stats to logs/UI.",
  "Implement get_queue_status() returning queue depth and stats; surface to logs and the UI.",
  "Queue status is observable.", deps="13.3"))
A(make(13, "P0", "13.6", "Route ALL calls through the gatekeeper", "gate-route-all",
  "Every LLM + search call goes through the gatekeeper; a test asserts no bypass.",
  "Route every external call (Pydantic AI model calls and SearchProvider calls) through ApiGatekeeper. Add a test asserting there is no bypass path.",
  "No external call bypasses the gatekeeper (test-enforced).", deps="13.2, 6.4, 3.3", prd="docs/prds/api-gatekeeper.md"))
A(make(13, "P1", "13.7", "Gatekeeper tests", "gate-tests",
  "limit→queue (no drop), drain, retries to max, backpressure, concurrency saturation.",
  "Write tests: exceeding a limit queues (no drop); the queue drains; retries stop at max_retries; backpressure when full; concurrent_max saturation behaves.",
  "Gatekeeper behaviour fully covered by tests.", deps="13.3"))

# ───────────────────────── Epic 14 — Research ─────────────────────────
A(make(14, "P1", "14.1", "Aggregate runs dataset", "research-dataset",
  "Aggregate saved runs into a dataset (outcomes, drift/nudge counts, tokens, latency).",
  "Write a script that reads runs/*.jsonl and aggregates per-topic outcomes, drift/nudge counts per side, tokens, and latency into a tidy dataset (CSV/parquet).",
  "A dataset summarising all runs exists.", deps="12.5"))
A(make(14, "P1", "14.2", "Analysis notebook", "research-notebook",
  "notebooks/: who-wins, agree-vs-disagree, drift frequency, tokens/latency per round.",
  "Create a notebook in notebooks/ analysing: who-wins distribution, agree-vs-disagree rate, drift/nudge frequency per side (evidence anti-sycophancy works), tokens/latency per round.",
  "Notebook presents the key analyses.", deps="14.1", prd="docs/PRD.md §9"))
A(make(14, "P1", "14.3", "Visualizations", "research-viz",
  "Charts saved to runs/ or notebooks/, interpreted in prose (not just metrics).",
  "Produce charts for the analyses and save them; interpret each in prose connecting observations to the design (§9 wants interpretation, not just numbers).",
  "Interpreted visualizations are saved and explained.", deps="14.2"))
A(make(14, "P2", "14.4", "Parameter exploration", "research-params",
  "Effect of MAX_WORDS/ROUNDS/model on quality + cost.",
  "Run a small parameter sweep over MAX_WORDS/ROUNDS/model and report the effect on debate quality and cost.",
  "A parameter-exploration section exists.", deps="14.2"))

# ───────────────────────── Epic 15 — Costs ─────────────────────────
A(make(15, "P1", "15.1", "Per-model price table", "cost-prices",
  "Price table (input/output $ per 1M tokens) in config.",
  "Add a config table of per-model prices (input/output $ per 1M tokens). Used to convert token counts to cost.",
  "Prices are config-driven and used for costing.", deps="6.7"))
A(make(15, "P1", "15.2", "Cost-breakdown table", "cost-table",
  "Per-run + aggregate table: tokens × price → total, per model + overall (§11).",
  "Generate a cost-breakdown table per run and aggregate: input/output tokens × price → total, per model and overall (guideline §11). Surface in the result and docs.",
  "Each debate reports a cost breakdown table.", deps="15.1", prd="docs/PRD.md §10"))
A(make(15, "P1", "15.3", "Budget cap + alert", "cost-budget",
  "Configurable budget cap with over-budget alert; document cost vs scale.",
  "Add a configurable budget cap and an over-budget alert (during/after a run). Document how cost scales with rounds × word-limit.",
  "A budget cap triggers an alert; cost scaling documented.", deps="15.1"))

# ───────────────────────── Epic D — planning docs upkeep ─────────────────────────
A(make("D", "P1", "D.6", "Keep planning docs updated", "docs-upkeep",
  "Keep PRD, sub-PRDs, TASKS, PROMPTS, and the improvements checklist current as the build proceeds.",
  "As implementation progresses, keep docs/PRD.md, docs/prds/*, docs/TASKS.md, docs/PROMPTS.md, and docs/Improvements_to_keep_in_mind.md in sync with reality. Update the Prompt Book with significant prompts.",
  "Docs stay consistent with the implemented system.", deps=""))


def main() -> None:
    titles = set() if DRY else existing_titles()
    labels = {"task"}
    for t in TASKS:
        labels.add(f"epic-{t['epic']}")
        labels.add(t["prio"])
    ensure_labels(labels)

    created = skipped = 0
    for t in TASKS:
        title = f"[{t['id']}] {t['title']}"
        if title in titles:
            print(f"skip (exists): {title}")
            skipped += 1
            continue
        lbls = ["task", f"epic-{t['epic']}", t["prio"]]
        if DRY:
            print(f"\n=== {title}  labels={lbls} ===\n{body(t)[:400]}…")
            created += 1
            continue
        try:
            url = sh(["gh", "issue", "create", "--title", title,
                      "--body", body(t), "--label", ",".join(lbls)])
            print(f"created: {title} -> {url}")
            created += 1
        except subprocess.CalledProcessError as e:
            print(f"ERROR creating {title}: {e.stderr}", file=sys.stderr)
    print(f"\nDone. created/printed={created} skipped={skipped} total={len(TASKS)}")


if __name__ == "__main__":
    main()
