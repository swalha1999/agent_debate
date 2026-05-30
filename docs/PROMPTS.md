# Prompt Book

> Required by guideline §8.3. A log of the **significant** prompts that shaped this
> project — the context they were issued in, and what decision/pattern they set. Not
> every keystroke; just the prompts that moved the design.
>
> Granular per-task build records (prompt + tokens) live in `../.building_tasks_logs/`.
> This file is the human-readable narrative.

## How to use

For each entry: date, the prompt (verbatim or paraphrased), the context, and the
outcome/decision it produced.

---

## Planning phase (2026-05-30)

### Set up the project
- **Prompt:** "make a new folder named agent_debate … make a git repo for it public."
- **Outcome:** Public repo created at github.com/swalha1999/agent_debate.

### Import the lecturer's guidelines
- **Prompt:** "take … only the md file on how to write code … if there is a pdf also take it."
- **Outcome:** Copied `software_submission_guidelines-V3` (en/he + pdf) into `docs/`.

### Capture prior-assignment lessons
- **Prompt:** "take the last pdf … make MD file so we don't do the same mistakes" →
  later: "update … to Improvements_to_keep_in_mind and remove anything not specific to this."
- **Outcome:** `docs/Improvements_to_keep_in_mind.md` (project-relevant lessons only).

### Define the product
- **Prompt:** the debate-system spec (2 debaters + controller, 10v10, word limits,
  mandatory web search, anti-sycophancy, timeout/retry, gatekeeper, UI/CLI/API/SDK/LOG,
  Python + uv).
- **Decisions:** Pydantic AI (no lock-in) · DuckDuckGo search · Anthropic default.
- **Outcome:** `docs/PRD.md`.

### Pluggable search
- **Prompt:** "make sure the search tool is a plug-in we can replace easily."
- **Outcome:** `SearchProvider` interface + registry (PRD §5.5, `prds/search-plugin.md`).
- **Prompt (3.5):** "Add a TavilySearchProvider stub (key via SEARCH_API_KEY) ...
  to prove a one-line swap with no engine changes."
- **Outcome:** `TavilySearchProvider` stub registered under `tavily`; flipping
  `SEARCH_BACKEND=tavily` swaps vendors via the same factory, no engine edits
  (sub-PRD §7 proof).

### Detailed tasks + build logging + sample runs
- **Prompts:** "make GOOD and detailed tasks" · ".building_tasks_logs with prompt +
  tokens per task" · "add a task to generate debates and save them to the repo."
- **Outcome:** `docs/TASKS.md`, `.building_tasks_logs/`, TASKS §12.5.

### Close guideline gaps
- **Prompt:** "what is missing from getting 100?" → "update the plan so we cover what
  he needs."
- **Outcome:** PRD §5.6 API gatekeeper, §8 standards, §9 research, §10 costs; sub-PRDs
  in `prds/`; this Prompt Book.

---

## Implementation phase

### 0.1 — Init uv workspace (2026-05-30)
- **Prompt:** "Create a root pyproject.toml that defines a uv workspace with
  `[tool.uv.workspace] members = ["packages/*"]` … python >=3.12 … shared dev-deps
  (ruff, mypy, pytest, pytest-cov). Verify `uv sync` resolves."
- **Context:** First implementation task; `packages/` is still empty.
- **Decision/outcome:** Root `pyproject.toml` declares the workspace and shared dev
  group. To make `uv sync` resolve cleanly against an empty `packages/*` glob, the
  root is itself a minimal package (`src/agent_debate_workspace`). Added ruff/mypy/
  coverage stubs (fleshed out by tasks 0.5 / 0.9). TDD: `tests/test_workspace.py`
  asserts the workspace contract.

### 0.2 — Create the five package skeletons (2026-05-30)
- **Prompt:** "Create five packages under packages/: core, log, api, cli, ui. Each
  has a pyproject.toml (name agent_debate_<pkg>), an `__init__.py`, and a src
  layout. core is the SDK; log is the logging package; api/cli/ui are surfaces."
- **Context:** First real workspace members on top of the 0.1 root.
- **Decision/outcome:** Five tiny packages under `packages/*`, each `agent_debate_<pkg>`
  with a src layout and hatchling build. The root pyproject now depends on all five
  via `[tool.uv.sources] workspace = true` so one `uv sync` installs every surface
  into the shared venv. Intra-package wiring (core/log deps) is left to task 0.3.
  TDD: `tests/test_packages.py` parametrizes over the five packages (import + name).
  _(Update, task 0.3: the per-package src layout was later moved from the
  underscore form `src/agent_debate_<pkg>/` to a shared namespace package
  `src/agent_debate/<pkg>/`, so surfaces are now imported as `agent_debate.<pkg>`,
  not `agent_debate_<pkg>`. The distribution names stay `agent_debate_<pkg>`.)_

### 0.3 — Wire intra-workspace deps + namespace-package restructure (2026-05-30)
- **Prompt:** "Convert all five packages from the underscore src-layout
  (`src/agent_debate_<pkg>/`) to a shared PEP 420 namespace-package layout
  (`src/agent_debate/<pkg>/`), so surfaces import as `agent_debate.<pkg>`; the
  `agent_debate/` dir has no `__init__.py` so the namespace merges. Wire the 0.3
  deps (issue #3): core → log; api/cli/ui → core + log via `[tool.uv.sources]`
  workspace sources, and prove the edges resolve at runtime by re-exporting
  version constants across each edge."
- **Context:** Builds on the 0.2 skeletons; closes issue #3.
- **Decision/outcome:** Chose **PEP 420 implicit namespace packages** over the
  underscore src-layout. Rationale: clean `agent_debate.<pkg>` imports that match
  the PRD's `from agent_debate import …` convention (PRD §5.1), one shared
  top-level namespace instead of five sibling top-levels, and no `__init__.py` at
  the namespace root so all five distributions merge in one interpreter. Each
  `pyproject.toml` hatchling wheel target is `src/agent_debate`; deps declared via
  `[project].dependencies` + `[tool.uv.sources] workspace = true`. `log` exposes
  `LIBRARY_VERSION`/`log_version`; `core` re-exports `log_version`; api/cli/ui
  re-export `core_version` + `log_version` — a successful import proves each edge.
  Root mypy config gained `namespace_packages` / `explicit_package_bases` /
  `mypy_path` so it resolves the namespace. TDD: updated `tests/test_packages.py`
  to `agent_debate.<pkg>` + added `tests/test_cross_package_imports.py` (edges +
  namespace-merge assertions).

### 0.4 — Pin Python and lock deps (2026-05-30)
- **Prompt:** "Set requires-python >=3.12 across packages. Run uv lock to produce
  uv.lock and commit it. Verify `uv sync` is clean and reproducible from scratch."
- **Context:** Builds on the 0.1–0.3 workspace; closes issue #4. All five
  packages + the root already declared `requires-python = ">=3.12"`, and `uv.lock`
  already pinned the same floor.
- **Decision/outcome:** The metadata floor was already consistent, so the
  reproducibility gap was the **interpreter selection**, not the version
  constraint. Added a top-level **`.python-version` pinning `3.12`** so a fresh
  `uv sync` always selects CPython 3.12 (the host previously resolved to 3.14).
  `uv lock` (CPython 3.12.13) produced no change to `uv.lock` — the committed
  lock already matched — and `uv lock --check` / `uv sync --frozen` confirm
  reproducibility. TDD: `tests/test_python_pin.py` asserts every `pyproject.toml`
  declares `>=3.12`, `.python-version` pins `3.12`, and `uv.lock` exists and
  declares `>=3.12` (watched the `.python-version` assertion fail first).

### 0.5 — Add ruff + mypy config, 0 violations (2026-05-30)
- **Prompt:** "Add [tool.ruff] (enable E,F,I,UP,B etc.) and [tool.mypy]
  strict-ish config to the root pyproject. Ensure `ruff check .` and `ruff format
  --check .` and `mypy` all pass on the skeleton."
- **Context:** Builds on the 0.1–0.4 workspace; closes issue #5. Root already had
  minimal ruff (`E,F,I`) + a working strict mypy namespace config from 0.3.
- **Decision/outcome:** Expanded the lint gate to
  `E,W,F,I,UP,B,SIM,C4,PIE,RET,N` and added `[tool.ruff.format]`
  (`docstring-code-format`). Kept mypy `strict = true` but **spelled out** the
  strict-ish flags (`disallow_untyped_defs`, `disallow_incomplete_defs`,
  `warn_unused_ignores`, `warn_redundant_casts`, `warn_return_any`,
  `no_implicit_optional`) so a later `strict = false` cannot silently relax the
  contract; preserved the 0.3 namespace settings. The skeleton was already typed
  and clean, so no source changes were needed. **`scripts/` stays excluded** from
  ruff: `create_issues.py` is a 592-line one-off generator whose ~125 violations
  are almost all `E501` from embedded prompt-string data tables that can't wrap
  without mangling the data — excluding is the documented low-churn choice.
  TDD: `tests/test_lint_config.py` asserts ruff selects `>= {E,F,I,UP,B}`,
  declares a positive `line-length`, and mypy has the strict-ish + namespace
  flags `True` (watched it fail before the config edit).

### 0.6 — Add pytest + a trivial test per package (2026-05-30)
- **Prompt:** "Configure pytest (and pytest-cov) at the root. Add tests/ per
  package with one trivial passing test (e.g. asserts __version__ importable).
  Ensure `uv run pytest` is green."
- **Context:** Builds on the 0.1–0.5 workspace; closes issue #6. Root already had
  pytest/pytest-cov and a top-level `tests/` dir; this task wants a per-package
  test layout so each surface owns at least one test.
- **Decision/outcome:** Each `packages/<pkg>/` gets a `tests/` dir with one smoke
  test asserting the package imports and exposes a non-empty `LIBRARY_VERSION`
  (a dedicated `__version__` is task 0.13 — not over-built here). Pytest
  `testpaths` now lists the root `tests` plus all five package `tests/` dirs so
  collection is deterministic. **Pattern set:** the five smoke files use unique
  basenames (`test_<pkg>_smoke.py`) rather than a shared `test_smoke.py` — a
  shared basename collides under pytest's default prepend import mode and under
  mypy (duplicate module), and adding `__init__.py` would break the PEP 420
  namespace; unique basenames avoid all three with no extra config. Each package
  `tests/` dir was added to mypy `files` + `mypy_path` so the new tests stay
  type-checked. Gates green: ruff/format/mypy clean, 34 passed, 100% coverage.

### 0.7 — Add .gitignore and .env.example (2026-05-30)
- **Prompt:** "Create .gitignore (.venv, __pycache__, *.pyc, .env, .ruff_cache,
  .mypy_cache, .pytest_cache). Create .env.example with every variable from
  PRD §7 (ANTHROPIC_API_KEY, DEBATER_MODEL, CONTROLLER_MODEL, PRO_MODEL,
  CON_MODEL, ROUNDS, MAX_WORDS, TURN_TIMEOUT_S, MAX_RETRIES, SEARCH_BACKEND,
  SEARCH_API_KEY) with safe placeholder values and comments."
- **Context:** Builds on the 0.1–0.6 workspace; closes issue #7. A minimal
  `.gitignore` already existed from 0.1; this task expands it (adds `.env` and
  the remaining caches) and adds the `.env.example` template.
- **Decision/outcome:** `.env.example` mirrors PRD §7 exactly — all 11 vars,
  each with a one-line comment and the PRD's default as a SAFE placeholder
  (`ANTHROPIC_API_KEY=your-anthropic-api-key-here`, optional `PRO_MODEL`/
  `CON_MODEL`/`SEARCH_API_KEY` left empty). TDD: `tests/test_env_example.py`
  parses `KEY=value` lines and asserts every PRD §7 var is present, that the
  secret keys carry placeholders (rejects a live `sk-ant-…`), and that
  `.gitignore` ignores `.env` (the secret file) but NOT `.env.example` (the
  committed template) — watched it fail (5 red) before adding the files.
  The PRD §7 list is mirrored as a maintained constant in the test; no vars
  beyond the indicative set. Gates green: ruff/format/mypy clean, 39 passed,
  100% coverage.

### 0.8 — CI quality gates, set up EARLY (2026-05-30)
- **Prompt:** "Create .github/workflows/ci.yml that, on push and pull_request,
  runs (in order, failing the build on any failure): uv sync; ruff check .;
  ruff format --check .; mypy; pytest --cov with fail_under=85; the 150-line
  check script (task 0.10); the secret scan (task 0.11). Use the official
  astral-sh/setup-uv action."
- **Context:** Builds on the 0.1–0.7 scaffold; closes issue #8. PRD §9 mandates
  CI gates be established *before* feature work. The 150-line check (0.10), the
  secret scan (0.11), and the `fail_under=85` pyproject config (0.9) are all
  LATER tasks — yet the scaffold pipeline must be GREEN today.
- **Decision/outcome (forward-compatible no-op pattern — significant):** the
  150-line and secret-scan steps are wired as **skip-if-absent shell guards**
  (`if [ -f scripts/check_line_limit.py ]; then uv run …; else echo "pending
  task 0.10"; fi`, same for `scripts/secret_scan.py` / "pending task 0.11").
  This keeps the scaffold green NOW and makes each gate **activate
  automatically** the moment 0.10/0.11 commit their script — no edit to
  `ci.yml`. Coverage's 85% threshold is enforced **now**, directly in the CI
  step (`pytest --cov --cov-fail-under=85`), rather than waiting on 0.9's
  pyproject `fail_under` (current coverage is 100%, so green). uv is provisioned
  via the official `astral-sh/setup-uv@v5`, Python pinned to 3.12 to match
  `.python-version`. TDD: `tests/test_ci_workflow.py` (string assertions —
  pyyaml is not a workspace dep) checks the file exists, triggers on
  push+pull_request, uses setup-uv, pins 3.12, lists every gate fragment **in
  order**, and that the two future gates are forward-compatible; watched 7 fail
  before adding `ci.yml`. Gates green: ruff/format/mypy clean, 46 passed, 100%
  coverage.

### 0.9 — Coverage gate ≥85%, config-driven (2026-05-30)
- **Prompt:** "Add [tool.coverage.run] (source = packages) and
  [tool.coverage.report] fail_under = 85 to pyproject. Wire `pytest --cov
  --cov-report=term-missing` into CI so it fails under 85%."
- **Context:** Closes issue #9. PRD §6.2 mandates `pyproject.toml` set
  `fail_under = 85` as the single source of truth. 0.8 had enforced 85
  provisionally via the CI flag `--cov-fail-under=85`; this task moves the
  number into config so it cannot diverge from the CLI.
- **Decision/outcome (config-driven gate — significant):** added
  `[tool.coverage.run]` with `source` = the five package namespace src roots
  (`packages/{core,log,api,cli,ui}/src`) + `branch = true`, and set
  `[tool.coverage.report].fail_under = 85` (replacing the 0.9 placeholder `0`)
  with `show_missing = true`. `pytest --cov` now reads the threshold from
  pyproject, so CI drops the hard-coded `--cov-fail-under=85` and runs
  `uv run pytest --cov --cov-report=term-missing` instead — **one source of
  truth**, no divergence. Reconciled `tests/test_ci_workflow.py`: its ordered
  gate fragments swapped `--cov-fail-under=85` → `pytest --cov` (still present,
  still in order). TDD: `tests/test_coverage_config.py` written first (asserts
  `fail_under == 85` and `source` covers all five `packages/*/src`), watched 2
  fail before adding config. Proved the gate bites by temporarily setting
  `fail_under = 101` (coverage rejected it), confirming pyproject is the active
  source; reverted. Gates green: ruff/format/mypy clean, 48 passed, coverage
  scoped to the 5 packages, 100%. Line-limit check (0.10) skipped — script not
  built yet; all touched files well under 150 lines.

### 0.10 — 150-line-per-file check script (2026-05-30)
- **Prompt:** "Write scripts/check_line_limit.py that walks packages/**/*.py,
  counts code lines excluding blank and comment-only lines, and exits non-zero
  listing any file > 150. Wire it into CI (0.8)."
- **Context:** Closes issue #10. PRD §3.2 caps every code file at 150 lines and
  mandates an automated CI check. ci.yml (0.8) already carried a
  forward-compatible guard (`if [ -f scripts/check_line_limit.py ]`) that
  activates the gate the moment the script lands — no workflow edit required.
- **Decision/outcome (token-accurate counting + scoped lint/type — significant):**
  counted code lines with stdlib `tokenize` rather than a regex heuristic — a
  physical line is code only if it bears a token that is not
  COMMENT/STRING/NL/NEWLINE/INDENT/DEDENT/ENCODING/ENDMARKER, so multi-line
  docstring interiors and comment-only lines are excluded while `x = "lit"`
  still counts. Threshold is a single named `DEFAULT_MAX_LINES = 150` constant
  with a `--max-lines` CLI override (no scattered magic number, §7.2). Script
  exposes `count_code_lines`/`find_offenders`/`main` so the logic is unit-tested
  and self-passes at 114 code lines. Brought *just* this script into the gate:
  narrowed ruff `extend-exclude` from `"scripts"` → `"scripts/create_issues.py"`
  and added the script to mypy `files`, keeping the data-heavy generator
  excluded. TDD: `tests/test_check_line_limit.py` written first (8 cases),
  watched red, then green. Gates green: ruff/format/mypy clean (21 files),
  56 passed, 100% coverage; `python scripts/check_line_limit.py` exits 0 on the
  current tree — the line-limit gate is now LIVE in CI.

### 0.11 — Secret-scan check in CI (2026-05-31)
- **Prompt:** "Add a secret scan to CI (e.g. gitleaks action, or a regex script
  for sk-…, api keys, tokens). Ensure it scans the diff/tree and fails on a hit.
  Confirm .env.example exists and contains only placeholders."
- **Context:** Closes issue #11. PRD §7.4 mandates **no secrets in the repo**
  and a CI gate that fails on a committed credential. ci.yml (0.8) already
  carried a forward-compatible guard (`if [ -f scripts/secret_scan.py ]`) that
  activates the gate the moment the script lands — no workflow edit required. A
  GitGuardian check also runs externally on PRs; this task adds our OWN
  self-contained in-repo scanner so the gate does not depend on a third party.
- **Decision/outcome (self-contained regex scanner + named config — significant):**
  built `scripts/secret_scan.py` with single named `PATTERNS` (anthropic /
  openai `sk-` tokens, AWS `AKIA…`, PEM private-key headers) and an `ALLOWLIST`
  of placeholder tokens (`your-`, `-here`, `xxxx`, …) so the `.env.example`
  template never trips the gate — no scattered magic regex (§7.2). `scan_text()`
  is filesystem-independent + importable so it is unit-tested on in-memory
  strings; `find_secrets()`/`main()` walk the tree skipping `EXCLUDED_DIRS`
  (`.git`/`.venv`/caches **and** `tests/`, whose fixtures plant clearly-fake
  pattern-matching strings on purpose) so the live scan stays clean. TDD:
  `tests/test_secret_scan.py` written first (14 cases), watched red, then green.
  Added the script to mypy `files` (mirrors 0.10). Gates green: ruff/format/mypy
  clean (23 files), 70 passed, 100% coverage; `python scripts/secret_scan.py`
  exits 0 on the current tree — the secret-scan gate is now LIVE in CI.

### 0.15 — Branch protection requires CI (2026-05-31)
- **Prompt:** "Configure branch protection on main so the CI workflow must pass
  before merge (via GitHub settings or `gh api`). Document the rule in the
  README/CONTRIBUTING."
- **Context:** Closes issue #15. Caps Epic 0 — every prior gate (lint, format,
  mypy, coverage, line-limit, secret-scan) only *runs* in CI; this makes a green
  CI **mandatory to merge**. The wrinkle: an autonomous loop running as the admin
  owner merges one PR at a time via `gh pr merge --merge`, so the protection
  must gate non-admins without blocking that loop.
- **Decision/outcome (server-side gate + reproducible script + doc-contract test —
  significant):** queried the real check-run name (`gh api .../commits/main/check-runs`)
  → **"Quality gates"** (the `name:` of the `quality-gates` job), and made that the
  single `required_status_checks` context. Tuned to keep the loop alive:
  `strict=false` (no up-to-date requirement → no rebase friction),
  `enforce_admins=false`, `required_pull_request_reviews=null`, `restrictions=null`.
  Applied via `gh api -X PUT .../branches/main/protection` and verified by reading
  the endpoint back. Made it reproducible with a committed
  `scripts/setup_branch_protection.sh` that derives owner/repo from `gh repo view`
  (no hard-coded slug) and builds the payload from one named `REQUIRED_CHECK_NAME`
  constant via `jq`. Since the live `gh api` call can't run in CI without an admin
  token, TDD targets the **doc + script contract** (`tests/test_branch_protection_doc.py`,
  written red-first): the README documents the rule and names the check; the script
  exists, is executable, references the check, keeps admins un-enforced + reviews
  null, and carries no secrets. Pattern set: *protection is configuration-as-code
  (script in repo) + a contract test guarding its documented invariants*, not a
  one-off click in the GitHub UI.

### 1.1 — structlog setup factory (2026-05-31)
- **Prompt:** "In packages/log, add a configure() factory that sets up structlog
  with two sinks: a human-readable console renderer and a JSONL file writer to
  runs/<run_id>.jsonl. Make it idempotent."
- **Context:** Closes issue #16. First real feature: the LOG package is the
  shared structured-logging surface used by every other package (PRD §5.7/§5.8).
  Scoped to the configuration factory only — event schema, get_logger/log_event
  and redaction are the follow-on tasks 1.2–1.5 that build on this chain.
- **Decision/outcome (dual-sink terminal processor + handle-cache idempotency —
  significant, sets the LOG sink pattern):** added `structlog>=25.5,<26`
  (resolved 25.5.0) to packages/log and relocked. TDD red-first
  (`tests/test_configure.py`). The two sinks (PRD §5.8) are realised by a single
  terminal processor `_DualSinkRenderer` that fans every event to **both** a
  per-run JSONL file (`<runs_dir>/<run_id>.jsonl`, append + flush, via
  `JSONRenderer`) and stdout (via `ConsoleRenderer`), then returns `""`. No
  hard-coded path: a `DEFAULT_RUNS_DIR="runs"` constant plus a parameterised
  `runs_dir`; the dir is created if missing. Idempotency is achieved by caching
  open file handles keyed on the resolved path (`_OPEN_SINKS`) so a repeat
  `configure()` reuses the handle and never duplicates sinks or errors — and the
  test asserts no duplicate JSONL lines. Generated `runs/*.jsonl`/`*.md` are
  gitignored (curated sample runs per PRD §12.5 added later with `git add -f`);
  `runs/.gitkeep` keeps the dir tracked. Pattern set: *LOG sinks are one terminal
  structlog processor fanning out to file + console, with per-run file handles
  cached for idempotent re-configuration.*

### 1.2 — Event schema model (2026-05-31)
- **Prompt:** "Add a Pydantic model LogEvent with fields run_id, ts, round,
  agent, event_type (Literal of message|tool_call|nudge|timeout|retry|verdict|
  system), payload, tokens, latency_ms. Validate event_type."
- **Context:** Closes issue #17. Builds directly on the 1.1 JSONL sink: gives the
  LOG package a typed shape (PRD §5.8) for every record the
  `runs/<run_id>.jsonl` sink emits. Scoped to the model + serialisation only —
  the `get_logger`/`log_event` helpers are task 1.3.
- **Decision/outcome (Pydantic v2 schema with a single-source-of-truth event-type
  set — significant, sets the LOG record contract):** added `pydantic>=2.9,<3`
  (resolved 2.13.4) to packages/log and relocked. TDD red-first
  (`tests/test_event.py`). `LogEvent` (in `event.py`) uses `extra="forbid"`, a
  strict `Literal` `event_type` so unknown values raise `ValidationError`, a
  `default_factory` UTC `ts`, a structured `payload` dict, and optional
  `tokens`/`latency_ms`. The allowed kinds live once as an `EVENT_TYPES` tuple
  kept in lock-step with the `EventType` `Literal` (a contract test guards the
  match) — no scattered inline list. `to_jsonl()` wraps `model_dump_json()` to a
  single newline-free line that round-trips back through `model_validate`,
  matching the 1.1 sink format. Pattern set: *LOG records are typed `LogEvent`
  Pydantic models; the allowed event-type set is one exported constant, and
  serialisation is a one-line JSONL string coherent with the per-run sink.*

### 1.3 — Logger helper API (2026-05-31)
- **Prompt:** "Add helpers: get_logger(run_id) returns a bound logger;
  log_event(**fields) validates via LogEvent and emits; context binding so
  run_id/round propagate. Keep files <150 lines."
- **Context:** Closes issue #18. Ties the 1.1 `configure()` setup factory and the
  1.2 `LogEvent` schema into the ergonomic public surface every other package
  uses to emit structured events (PRD §5.8). No new sink — reuses 1.1's.
- **Decision/outcome (the LOG public emit contract — significant, sets how
  dependents log):** TDD red-first (`tests/test_helpers.py`, 9 cases). New
  `_api.py` (~40 code lines): `get_logger(run_id, *, runs_dir=DEFAULT_RUNS_DIR)`
  is a thin idempotent wrapper over `configure()` returning a `run_id`-bound
  logger; `log_event(*, run_id, agent, event_type, round=None, payload=None,
  tokens=None, latency_ms=None, runs_dir=DEFAULT_RUNS_DIR)` **builds + validates
  a `LogEvent` first** (unknown `event_type` / missing required field raises
  `ValidationError` *before* any emit — the sink never sees a malformed record),
  then emits one `runs/<run_id>.jsonl` line and returns the validated event.
  Round context binds via structlog contextvars: `bind_round(n)`/`bind_context`/
  `clear_context`; an explicit `round` kwarg wins over the bound contextvar,
  else it falls back to the bound round, else stays unset so validation rejects
  it as a missing required field. No-hardcoding: `runs_dir` reuses
  `DEFAULT_RUNS_DIR`; the contextvar key is a module constant. mypy stays clean
  by building the `LogEvent` kwargs as a `dict[str, Any]` so **pydantic is the
  single validation point** (not the static signature). Pattern set: *dependents
  log via `get_logger`/`log_event`; every record is validated through `LogEvent`
  before it reaches the sink, and `run_id`/`round` ride structlog contextvars.*

### 1.4 — Redaction filter (2026-05-31)
- **Prompt:** "Add a structlog processor that redacts secret-like values (keys
  named *key*/*token*/*secret*, sk-… patterns) and truncates payloads over a
  configurable size. Add tests."
- **Context:** Closes issue #19. A **runtime** structlog processor — the
  counterpart to the build-time `scripts/secret_scan.py` gate (PRD §7.4) — wired
  into 1.1's `configure()` chain so it covers both PRD §5.8 sinks.
- **Decision/outcome (where redaction sits + how false positives are avoided):**
  TDD red-first (`tests/test_redaction.py`, 12 cases). New `redaction.py` (63
  code lines): pure recursive `redact_value(value, max_len)` walks dicts (a
  secret-like *key* redacts its value outright, else recurse), maps lists/tuples,
  redacts-or-truncates strings, passes other scalars through. The processor is
  inserted **immediately before the terminal `_DualSinkRenderer`**, so redaction
  + truncation apply to **both** the console and JSONL sinks. Named single-source
  configs (no scattered magic): `REDACTED`, `TRUNCATED_SUFFIX`,
  `MAX_VALUE_LEN=2048` (override via `make_redactor(max_len=…)`),
  `SECRET_KEY_HINTS`, and `SECRET_VALUE_PATTERNS` (aligned with `secret_scan.py`:
  `sk-ant-…`/`sk-…`/`AKIA…`/PEM + a bearer-token regex; a partial match redacts
  the whole value, fail-safe). Key subtlety — a `SAFE_KEYS` allowlist
  (`tokens`/`token_count`/`tokens_used`) prevents the `LogEvent` `tokens` *count*
  field (contains "token") from being false-positively redacted. Pattern set:
  *secrets are scrubbed at the LOG boundary by a single processor; never trust a
  payload to be secret-free, and allowlist legitimate hint-bearing metadata.*

## 1.5 — LOG unit tests (Epic-1 acceptance pass)

- **Prompt:** "Write pytest tests: an event is written to runs/<run_id>.jsonl
  and round-trips; invalid event_type rejected; redaction hides a fake key. Keep
  coverage high."
- **Context:** Closes issue #20. The LOG package (1.1–1.4) was already
  feature-complete at 100% coverage, each module shipped with its own unit
  suite. This task is the **integration/acceptance** pass: prove the three
  acceptance areas end-to-end **through the public API** (`agent_debate.log`),
  not by re-testing internals, then close any genuine edge-case gaps.
- **Decision/outcome (acceptance-through-public-API + the net-new gap closed):**
  Added `tests/test_log_acceptance.py` (the three areas via `log_event` →
  on-disk JSONL: write+**reconstruct a `LogEvent` from the disk line**, invalid
  `event_type` rejected with nothing written, fake `sk-ant-…` key redacted in
  the file) and `tests/test_log_edge_cases.py` (multiple events **appended** to
  one file in order; the **exactly-at-`MAX_VALUE_LEN`** truncation boundary;
  empty payload round-trip; bound-round propagate-then-clear in one flow;
  idempotent `get_logger` keeping a single sink between writes). TDD red-first
  came from a real gap: the truncation marker `TRUNCATED_SUFFIX` was not part of
  the public surface — the edge test imported it (red: `ImportError`), then it
  was exported from `agent_debate.log.__init__` (green). Pattern: *Epic
  acceptance tests drive the public API end-to-end and assert the on-disk
  artifact; finding the gap means promoting a genuinely-public constant, not
  inventing coverage.*

### 2.1 — Settings model (pydantic-settings, PRD §7)

- **Prompt:** "In packages/core, add a pydantic-settings Settings class with
  every PRD §7 field and sane defaults (ROUNDS=10, MAX_WORDS=150,
  TURN_TIMEOUT_S=60, MAX_RETRIES=2, SEARCH_BACKEND=duckduckgo). Load from
  environment and .env."
- **Context:** Closes issue #21. First config surface for the SDK; later tasks
  (e.g. 2.3 strict required-key validation, rate-limit config) build on it.
- **Decision/outcome (defaults-as-single-source + safe-to-import required key +
  per-side fallback):** Defaults live once in `core/constants.py` (`DEFAULT_*`,
  guideline §7.2 — no scattered literals); `settings.py` references them, which
  also keeps both files well under the 150-line gate. `Settings` is a
  `pydantic_settings.BaseSettings` with **no env prefix** (PRD §7 vars are bare
  names), `extra="ignore"`, `case_sensitive=False`, `env_file=".env"`. Key
  pattern: `ANTHROPIC_API_KEY` is typed `Optional[str]=None` so importing /
  instantiating `Settings` **never explodes** at test-collection time or in
  key-free packages — strict fail-fast validation is deferred to task 2.3. The
  `PRO_MODEL`/`CON_MODEL` per-side overrides bind via `alias=` onto
  `*_override` fields and resolve through computed `pro_model`/`con_model`
  properties that fall back to `DEBATER_MODEL`. `get_settings()` is an
  `lru_cache` singleton that emits a `settings_loaded` debug event through the
  LOG package. Tests avoid pydantic-settings' runtime-only `_env_file` kwarg
  (mypy strict rejects it) — they `monkeypatch`/`chdir` to an isolated tmp dir
  instead, so no ambient `.env` leaks into the suite.

### 2.2 — Model resolver (Pydantic AI, PRD §4) (2026-05-31)

- **Prompt:** "Add a resolver mapping
  DEBATER_MODEL/CONTROLLER_MODEL/PRO_MODEL/CON_MODEL strings to Pydantic AI
  model instances. PRO/CON fall back to DEBATER_MODEL. Anthropic default; any
  provider via model string."
- **Context:** Closes issue #22. Turns the task 2.1 settings strings into the
  concrete model objects the agents/controller (and the Epic 13 gatekeeper) will
  drive. Strict required-key validation stays in task 2.3.
- **Decision/outcome (config-only swap + one-place fallback + offline
  construction):** `core/models.py` wraps Pydantic AI's
  `pydantic_ai.models.infer_model` — the provider is chosen **entirely** by the
  `provider:model` string (Anthropic is the PRD §7 default, encoded in the
  string, not hard-coded), so swapping providers is a config-only change with
  zero code edits (proven by `test_env_swaps_debater_with_zero_code_changes`,
  which flips `DEBATER_MODEL` via env and asserts the resolved `model_name`
  changes). `resolve_models(settings)` returns a frozen `ResolvedModels`
  dataclass for the four roles and reuses the settings' computed
  `pro_model`/`con_model` properties, so the PRO/CON → DEBATER fallback lives in
  exactly one place. A bad string fails loudly (`infer_model` raises
  `ValueError`/`UserError`), never a silent broken model. Construction is
  **offline** — no network call; the Anthropic client only reads
  `ANTHROPIC_API_KEY` at build time, so tests inject a dummy key via
  `monkeypatch` (no real key needed). Actual API calls will route through the
  Epic 13 gatekeeper, which drives these resolved models. Dep added:
  `pydantic-ai-slim[anthropic]>=1.0,<2` (resolved 1.104.0); the `[anthropic]`
  extra ships the default-provider client.

### 2.3 — Validate required keys (PRD §7) (2026-05-31)

- **Prompt:** "On startup, validate that the active provider's key (e.g.
  ANTHROPIC_API_KEY) is present; raise a clear, actionable error if not."
- **Context:** Closes issue #23. Task 2.1 keeps `ANTHROPIC_API_KEY` optional so
  imports never explode, and task 2.2 builds the provider client eagerly — which
  with no key raises a deep Pydantic AI / SDK `UserError`. This task fires first
  with a friendly message.
- **Decision/outcome (friendly error precedes the SDK error, config-driven
  mapping):** `core/validation.py` adds `validate_required_keys(settings)`, which
  derives the active provider prefixes from the role model strings
  (`DEBATER_MODEL`/`CONTROLLER_MODEL`/`PRO_MODEL`/`CON_MODEL` — the part before
  `:`), looks each up in the new `constants.PROVIDER_KEY_ENV_VARS` mapping
  (`anthropic → ANTHROPIC_API_KEY`, `openai → OPENAI_API_KEY`; single source of
  truth, extensible), and raises one `MissingApiKeyError` naming every
  missing/blank var plus an actionable hint ("copy .env.example to .env and fill
  in your key"). Unmapped providers are lenient. `resolve_models()` calls it
  **before** constructing any model, so operators see our message instead of the
  SDK stack trace. Logged via the LOG package on failure; no run_id needed.

### 0.14 — config/rate_limits.json (versioned 1.00)

- **Prompt:** "Create config/rate_limits.json with version "1.00" and services
  (default, anthropic, search) each with requests_per_minute,
  requests_per_hour, concurrent_max, retry_after_seconds, max_retries (see
  docs/prds/api-gatekeeper.md). It will be loaded by Epic 13."
- **Context:** Closes issue #14. Establishes the rate-limit config file as the
  single source of truth for the API gatekeeper (sub-PRD §4); the loader
  `RateLimitConfig` is Epic 13, not built here.
- **Decision/outcome (data file + contract test, no loader):** The file's shape
  is copied **exactly** from `docs/prds/api-gatekeeper.md` §4 so "0 hard-coded
  limits" (§5.2) holds — Python never embeds these numbers. Pragmatic TDD for a
  data file: `tests/test_rate_limits_config.py` asserts the file exists, parses,
  `version == "1.00"`, and that `default`/`anthropic`/`search` each carry the
  five integer keys matching the sub-PRD; written red-first (10 failing cases,
  `FileNotFoundError`) before the file was added. Path resolves repo-root
  relative (`Path(__file__).resolve().parent.parent / "config" / ...`), not via
  cwd, matching `tests/test_python_pin.py`.

### 2.5 — Config acceptance tests (Epic 2 pass) (2026-05-31)

- **Prompt:** "Write tests: Settings loads from env; PRO/CON fall back to
  DEBATER_MODEL; an invalid model string raises clearly."
- **Context:** Closes issue #25. Epic 2 core config (2.1–2.4) was already
  implemented with ~100% unit coverage. This is the Epic-2 *acceptance* pass
  (mirrors how 1.5 consolidated Epic 1): one consolidated module exercising the
  three acceptance behaviours END-TO-END through the public `agent_debate.core`
  API rather than re-testing internals, plus genuine edge gaps.
- **Decision/outcome (acceptance module + real edge gaps, honest about overlap):**
  `tests/test_config_acceptance.py` drives `get_settings`/`Settings`/
  `resolve_model`/`resolve_models`/`validate_required_keys` from the package
  root. Net-new (previously unverified) edges: **empty-string** `PRO_MODEL=`/
  `CON_MODEL=` (exactly what copying `.env.example` produces) must *fall back* to
  `DEBATER_MODEL` (empty is falsy via `or`), not yield a broken empty model;
  the **mixed** case (PRO overridden, CON unset); a **malformed** (blank /
  no-colon) model string raising loudly (`UserError`/`RuntimeError`) vs the
  recognised-but-unknown provider raising `ValueError`; and the bad-`DEBATER_MODEL`
  error surfacing through `resolve_models`. TDD red-first was demonstrated on the
  empty-string fallback by briefly swapping `pro_model_override or …` for an
  `is not None` form (test went RED: `'' != 'anthropic:claude-sonnet-4-6'`), then
  reverting (GREEN). No production code changed. Coverage stayed 100%; all gates
  green (ruff, ruff-format, mypy, pytest --cov ≥85, line-limit, secret-scan).

### 3.6 — Search tests (Epic 3 acceptance pass) (2026-05-31)

- **Prompt:** "Write tests: registry returns the configured provider; DDG mapping
  shape; empty/error path returns []; swapping to the stub needs no engine change
  (mock network)."
- **Context:** Closes issue #31. Epic 3 search (3.1–3.5) was already implemented
  with ~100% unit coverage by the per-task suites. This is the Epic-3 *acceptance*
  pass (mirrors 1.5/2.5/13.7): one consolidated module exercising the sub-PRD §7
  criteria END-TO-END through the public `agent_debate.core` API rather than
  re-testing internals.
- **Decision/outcome (acceptance composition, honest about overlap):**
  `tests/test_search_acceptance.py` drives `create_search_provider` →
  concrete vendor → `ResilientSearchProvider` as one flow: DDG mapped-shape via a
  monkeypatched `DDGS`, registry returns the configured provider, the one-line
  `duckduckgo`↔`tavily` swap through the *same* factory call, and the empty/error
  paths returning `[]`. Net-new value is the **composition** — wrapping the
  *factory* provider in the resilient layer with the **real** `search`
  `ServiceLimits` loaded from `config/rate_limits.json` (not hard-coded), proving a
  vendor crash degrades to `[]` instead of escaping into a debate. TDD red-first
  demonstrated on that assertion: briefly asserting `pytest.raises(ConnectionError)`
  (RED — the layer degrades, never raises), then reverting to `== []` (GREEN). No
  production code changed (search package was already gap-free). Total coverage
  99%; all gates green (ruff, ruff-format, mypy, pytest --cov ≥85, line-limit,
  secret-scan).

### 2026-05-31 — 13.1 RateLimitConfig loader (Epic 13 opens)

- **Prompt (verbatim):** "Implement RateLimitConfig that loads
  config/rate_limits.json (per-service limits). No limit is hard-coded. See
  docs/prds/api-gatekeeper.md." (+ repo standards: TDD, ≤150 lines/file, ruff/mypy
  clean, no hard-coded values, gatekeeper-routed calls, LOG package, ≥85% cov.)
- **Context:** First task of **Epic 13**, the API gatekeeper
  (`docs/prds/api-gatekeeper.md`) — the single chokepoint every external
  LLM/search call must pass through. Task 0.14 had shipped the *data file*
  (`config/rate_limits.json`, shape locked by `tests/test_rate_limits_config.py`);
  this task ships the *loader + models* that read it, with clean room for
  `execute` (13.2), the FIFO overflow queue (13.3), retry + concurrency (13.4)
  and `get_queue_status` (13.5).
- **Decision/pattern set (a gatekeeper SUBPACKAGE + config-only-from-file):**
  Chose `agent_debate.core.gatekeeper/` as a subpackage (`__init__.py` re-exports
  + `config.py`) rather than a flat module, so Epic 13's later pieces grow there
  without any file crossing the 150-line cap. `ServiceLimits` (frozen,
  `extra="forbid"`, five required int fields, `gt=0` throughput / `ge=0`
  max_retries) carries **no default VALUES** — the "0 hard-coded limits"
  guideline (§5.2) is enforced structurally: the only literals in Python are the
  file *name* and the fallback service *key* `"default"`; every number comes from
  the file (proven by a tmp-file test loading custom values). `get_service_limits`
  falls back to the `default` service per sub-PRD §4. Loader resolves the
  repo-root path cwd-independently and raises clear `FileNotFoundError` /
  `ValueError`. TDD red-first (ModuleNotFound on the new subpackage), then green;
  all gates green, 100% coverage.

### 2026-05-31 — 13.2 ApiGatekeeper.execute (check → run → log)

- **Prompt (verbatim):** "Implement ApiGatekeeper.execute(api_call, *args,
  **kwargs): check rate limits before running, execute, and log every call
  (service, latency, outcome)." (+ repo standards: TDD, ≤150 lines/file,
  ruff/mypy clean, no hard-coded values, gatekeeper-routed calls, LOG package,
  ≥85% cov.)
- **Context:** Second task of **Epic 13** (`docs/prds/api-gatekeeper.md`).
  13.1 shipped the config surface; this task adds the **core class** every
  external LLM/search call routes through. Scope kept tight per the sub-PRD: a
  simple in-process limit *check* + execute + log now; the FIFO overflow queue
  (13.3), retry/concurrency (13.4) and full `get_queue_status` (13.5) hook in at
  marked seams later.
- **Decision/pattern set (split + clean seams):** Split the class across the
  gatekeeper subpackage to stay well under 150 lines and give later tasks clean
  homes — `_gatekeeper.py` (the `ApiGatekeeper` class), `_limiter.py` (a
  per-service sliding-window `_RateLimiter` with an **injectable clock** so the
  per-minute/per-hour windows + pruning are deterministically testable),
  `types.py` (`QueueStatus`, `CallOutcome`) and `errors.py`
  (`RateLimitExceededError`, `Error` suffix for ruff N818). `execute(api_call,
  *args, service="default", **kwargs)` picks the service's `ServiceLimits`
  (default fallback), calls `_check_limits` **before** running (an exhausted
  window raises `RateLimitExceededError`; this is the seam 13.3 swaps for FIFO
  enqueue/backpressure), times the call with `time.monotonic`, and logs **one**
  structured event via the LOG package (`log_event`, `event_type="tool_call"`,
  payload `{service, outcome}`, `latency_ms`) on both success and error (error is
  logged then re-raised — retry is 13.4). The gatekeeper takes `run_id`/`runs_dir`
  for logging context. **0 hard-coded limits:** all thresholds come from the
  injected `RateLimitConfig`; the only literals are unit conversions (60s/3600s/
  1000ms) and identifier labels. TDD red-first (ImportError: no `ApiGatekeeper`),
  then green; all gates green, 100% coverage.

### 2026-05-31 — 13.3 FIFO overflow queue (enqueue, backpressure, drain)

- **Prompt (verbatim):** "Add a FIFO overflow queue with max depth from config:
  when a limit is hit, enqueue instead of dropping; signal backpressure when
  full; drain as rate windows reset." (plus the repo-standard checklist: TDD,
  150-line cap, ruff/mypy clean, no hard-coded values, gatekeeper for external
  calls, LOG package, coverage >= 85%.)
- **Context:** Third task of Epic 13 (`docs/prds/api-gatekeeper.md` §5). It
  replaces 13.2's "raise `RateLimitExceededError` on overflow" seam with the
  sub-PRD overflow queue: overflow is **queued, never dropped or crashed**.
- **Decision/pattern set:** `execute(api_call, *args, service, **kwargs)` now
  returns `_T | None` — it runs the call immediately when the window has room,
  else **enqueues** it into a bounded per-service FIFO queue and returns `None`
  (the call runs later via `drain()`). Only a **full** queue (depth ==
  `queue_max_depth`) raises the new `QueueFullError` — the backpressure signal.
  `drain()` walks each service's queue oldest-first, running calls while the
  window has room (FIFO preserved across resets). Added a per-service
  `queue_max_depth` field to `config/rate_limits.json` + `ServiceLimits` (value
  **only** in JSON, default 100); no depth literal in Python. New module
  `gatekeeper/_queue.py` (`_OverflowQueue` + `PendingCall`) holds the bounded
  deque + lifetime enqueue/drain counters that back a now-**real** `QueueStatus`
  (depth/max_depth/enqueued_total/drained_total). The limiter clock is injectable
  through the gatekeeper (`time_fn`) so a test advances the fake clock to reset a
  window then drains deterministically. Queue lifecycle events (enqueue / drain /
  backpressure) log via the LOG package (`event_type="system"`). Updated the two
  config shape tests (0.14 `tests/test_rate_limits_config.py`, 13.1
  `packages/core/tests/test_rate_limit_config.py`) for the additive field (kept
  version `"1.00"`) and rewrote the two 13.2 raise-on-overflow execute tests to
  assert **enqueue** instead. TDD red-first (ImportError: no `QueueFullError`),
  then green; all gates green, 100% coverage.

### 2026-05-31 — 13.4 Retry-with-backoff + concurrent_max enforcement

- **Prompt:** "Add retry-with-backoff on transient failures per config
  (max_retries, retry_after_seconds) and enforce concurrent_max." (plus the
  repo-standard checklist: TDD, 150-line cap, ruff/mypy clean, no hard-coded
  values, gatekeeper for external calls, LOG package, coverage >= 85%.)
- **Context:** Fourth task of Epic 13 (`docs/prds/api-gatekeeper.md` §1/§4/§6/§7).
  Extends `execute` with the two remaining acceptance bullets: transient failures
  retried with backoff per config, and `concurrent_max` enforced.
- **Decision/pattern set:** New module `gatekeeper/_retry.py` owns the retry
  **policy**. *Transient vs permanent:* `TRANSIENT_ERRORS = (TimeoutError,
  ConnectionError)` (a type tuple) is retried; everything else (e.g.
  `ValueError`) propagates immediately, no retry. *Backoff:* **exponential**,
  `retry_after_seconds * _BACKOFF_BASE ** retry_index` — the base `2.0` is a named
  strategy constant; the magnitude derives entirely from config's
  `retry_after_seconds`, so nothing is hard-coded. `run_with_retry[T]` (PEP 695
  generic) retries up to `max_retries`, invoking `on_retry(n, delay, exc)` +
  `sleep_fn(delay)` between attempts. *Concurrency:* reused the `_RateLimiter`
  `_inflight` seam from 13.2 — added `at_concurrency_cap` / `acquire` / `release`
  (release guarded so the counter never goes negative). `execute` now overflows
  into the **same FIFO queue** when EITHER the rate window is exhausted OR the
  service is at `concurrent_max`, so an over-cap call is enqueued rather than
  exceeding the cap; `_run` holds one in-flight slot across the whole retry
  sequence and releases it in a `finally` (even on error). New injectable
  `sleep_fn` seam (default `time.sleep`) lets tests capture backoff delays with
  zero real waiting; each retry logs a `retry` `LogEvent` via the LOG package.
  Split for the 150-line cap: the three log emitters moved to
  `gatekeeper/_events.py` (`_GatekeeperLog`), dropping `_gatekeeper.py` from 155
  to 70 code lines. TDD red-first (new retry + concurrency tests, watched fail),
  then green; all gates green, 100% coverage, no existing tests changed.

### 2026-05-31 — 13.5 get_queue_status (complete depth+stats, surfaced to logs)

- **Prompt:** "Implement get_queue_status() returning queue depth and stats;
  surface to logs and the UI." (plus the repo-standard checklist: TDD, 150-line
  cap, ruff/mypy clean, no hard-coded values, gatekeeper for external calls, LOG
  package, coverage >= 85%.)
- **Context:** Fifth task of Epic 13 (`docs/prds/api-gatekeeper.md` §3/§6:
  `get_queue_status()` reports depth + stats). 13.2 left an empty seam, 13.3 made
  depth real; this makes the snapshot **complete, accurate and observable**.
- **Decision/pattern set:** Two-level typed schema. Per-service `QueueStatus`
  (frozen Pydantic) gains `backpressure_total` + `in_flight` alongside
  `depth`/`max_depth`/`enqueued_total`/`drained_total`. New `GatekeeperStatus`
  aggregate model (`services: dict[str, QueueStatus]` + `total_*` sums) with a
  `from_services()` classmethod — JSON-serializable (`model_dump_json`) so the
  Epic 11 UI/API/SSE can consume one object unchanged. **No hard-coded values:**
  `max_depth` from config; `backpressure_total` from a new
  `_OverflowQueue.record_backpressure()` counter (wired in `_enqueue` on a
  full-queue rejection); `in_flight` from a new `_RateLimiter.in_flight()` reader
  over the existing `_inflight` seam. `get_queue_status()` returns the full
  per-service status; new `get_status()` aggregates across live queues; new
  `log_queue_status()` snapshots + emits **one** `system` event tagged
  `queue_event="status"` (on-demand, never spams) and returns the snapshot. New
  `_GatekeeperLog.status()` emitter flattens the snapshot into the LOG payload.
  TDD red-first (new `test_gatekeeper_status.py`, watched fail on missing
  `GatekeeperStatus`), then green; existing gatekeeper tests untouched (additive);
  all gates green, 100% coverage.

### 2026-05-31 — 13.7 Gatekeeper acceptance + §7 edge tests (Epic-13 pass)

- **Prompt:** "Write tests: exceeding a limit queues (no drop); the queue drains;
  retries stop at max_retries; backpressure when full; concurrent_max saturation
  behaves." (plus the repo-standard checklist: TDD, 150-line cap, ruff/mypy
  clean, no hard-coded values, gatekeeper for external calls, LOG package,
  coverage >= 85%.)
- **Context:** Closes issue #96. The gatekeeper (13.1–13.5) was already
  feature-complete with per-task suites at 100% coverage. This is the **Epic-13
  acceptance/edge pass** (mirrors 1.5 / 2.5): prove the sub-PRD §6 behaviours and
  §7 edges **end-to-end through the public `ApiGatekeeper` API**, not by
  re-testing internals.
- **Decision/pattern set (acceptance-through-public-API):** Added
  `test_gatekeeper_acceptance.py` (the five §6 behaviours via
  `execute`/`drain`/`get_queue_status`: limit→queue no-drop, drain on injected
  window reset, retries-to-`max_retries`-then-raise, `QueueFullError`
  backpressure at `queue_max_depth`, `concurrent_max` saturation never exceeding
  the cap) and `test_gatekeeper_edges.py` (the §7 edges: **sustained overflow +
  multi-window FIFO drain** with depth>1 released one window at a time, repeated
  transient failures logging every retry **and** the terminal error, concurrent
  saturation→drain, and **config hot-values out of range** rejected). Shared
  `_gatekeeper_acceptance_helpers.py` (FakeClock + config/gatekeeper builders +
  JSONL reader; non-`test_` unique basename, imported by bare name under
  pytest's `prepend` mode). TDD red-first on a genuinely net-new assertion: the
  multi-window FIFO drain (probed with a deliberately-reordered expectation →
  red, then asserted the real `a,b,c,d,e` order → green) and `ServiceLimits`
  direct-model out-of-range validation (existing suite only covered
  `requests_per_minute=0` via the loader; the new parametrized test adds
  `concurrent_max`/`queue_max_depth`/`requests_per_hour` zero + negative
  `retry_after_seconds`). No source change needed — gatekeeper was already
  correct at 100%; deliverable is test-only. All gates green, 250 passed, 100%
  coverage. Pattern: *Epic acceptance tests compose the public API end-to-end and
  assert the on-disk log artifact; net-new value comes from edges no per-task
  test asserted, not from re-covering internals.*

### Task 3.1 — SearchProvider interface (Epic 3, issue #26)

- **Prompt:** "In packages/core search/base.py, define SearchResult
  (title,url,snippet) and a SearchProvider Protocol with name and
  search(query,*,max_results=5)->list[SearchResult]. Per
  docs/prds/search-plugin.md. Follow repo standards: TDD …"
- **Context:** Closes issue #26. First task of Epic 3 (pluggable web search,
  `docs/prds/search-plugin.md` §2 + PRD §5.5). Ships the **interface only** — no
  concrete provider (DuckDuckGo is 3.3) and no registry (3.2). The goal is a
  stable seam so the search vendor is swappable with one config change.
- **Decision/pattern set (interface-first plug-in seam):** New `search`
  subpackage mirroring the `gatekeeper` layout — `search/base.py` holds the
  surface, `search/__init__.py` re-exports, and `agent_debate.core` re-exports in
  turn. `SearchResult` is a **frozen, `extra="forbid"` Pydantic `BaseModel`**
  (same hardening as the gatekeeper's `QueueStatus`): a result flows on into
  sanitisation and the run log unchanged, and a malformed provider payload fails
  loudly. `SearchProvider` is a **`@runtime_checkable` `typing.Protocol`** so the
  registry (3.2) can `isinstance`-assert conformance — vendors are purely
  structural, no upstream subclassing. The `max_results=5` default has a single
  source: a module-level `DEFAULT_MAX_RESULTS = 5` constant used directly in the
  Protocol signature and re-exported. TDD red-first: wrote
  `test_search_base.py` (7 tests: field validation, JSON round-trip, non-string
  rejection, default-page-size constant, a dummy class satisfying the Protocol +
  duck-call honouring the default/explicit `max_results`, and a class missing
  both members **not** satisfying it), watched it fail (`ImportError:
  DEFAULT_MAX_RESULTS`), then implemented to green. No network/gatekeeper wiring
  yet — the docstrings flag that a future provider's `search` must route through
  the Epic 13 gatekeeper. All gates green: ruff/format clean, mypy clean (69
  files), 257 passed, 100% coverage, line-limit + secret-scan pass. Pattern:
  *introduce a plug-in as a re-exported interface-only subpackage first
  (frozen-BaseModel result + runtime_checkable Protocol + single-source default
  constant); concrete providers and the registry land on top without reshaping
  the contract.*

### Task 3.2 — Provider registry + factory (Epic 3, issue #27)

- **Date:** 2026-05-31
- **Prompt (verbatim):** "Add a registry mapping names to SearchProvider classes
  and a factory that returns the provider for SEARCH_BACKEND. Swapping backends
  must be a one-line config change." (+ repo standards: TDD red-first, ≤150
  code lines/file, ruff 0 + mypy clean, no hard-coded values, external calls via
  the API gatekeeper, log via LOG, coverage ≥85%.)
- **Context:** Epic 3's second task. The 3.1 interface (`SearchProvider`
  Protocol + `SearchResult`) exists; no concrete vendor yet (DuckDuckGo is 3.3).
  This adds the selection mechanism that makes the vendor swappable by config.
- **Outcome / pattern set:** `search/registry.py` holds a module-level
  `_REGISTRY: dict[name -> SearchProvider class]`, a `register_search_provider(name)`
  **class decorator** that records (and returns unchanged) a provider class, and
  a `create_search_provider(settings)` **factory** that resolves
  `settings.search_backend` via a *pure registry lookup* — no concrete class is
  ever named in the factory, so adding a backend never edits selection code.
  That is the whole "one-line config change" guarantee: a new vendor is
  selectable the instant it is decorated, and switching is just changing
  `SEARCH_BACKEND`. `SEARCH_API_KEY` is threaded only into providers whose
  constructor exposes an `api_key` parameter (an `inspect.signature` check), so
  keyless providers (DuckDuckGo) construct with no args while keyed ones (Tavily,
  …) get the key — no per-vendor branching. Unknown backends raise
  `UnknownSearchBackendError` (in `search/errors.py`), a `LookupError` whose
  message names the bad key *and* lists the available backends — actionable, not
  a bare `KeyError`. Duplicate registration fails loudly (`ValueError`) instead
  of silently shadowing. The factory makes **no network call** — it only
  *constructs*; the provider's `search` is what later routes through the Epic 13
  gatekeeper. TDD red-first: `test_search_registry.py` (9 tests incl. the
  one-line-swap proof — same code path, two `SEARCH_BACKEND` values, two
  provider types — an autouse fixture snapshots/restores `_REGISTRY`), watched it
  fail (`ImportError`), then implemented to green. Gates: ruff/format clean, mypy
  clean (72 files), 266 passed, 100% coverage, line-limit + secret-scan pass.
  *Pattern: select plug-ins by a decorator-populated name→class registry + a
  config-keyed lookup factory (never branch on concrete classes); thread optional
  credentials by constructor-signature introspection; make the not-found error
  enumerate the valid options.*

### Task 3.3 — DuckDuckGoSearchProvider (Epic 3, issue #28)

- **Date:** 2026-05-31
- **Prompt (verbatim):** "Implement DuckDuckGoSearchProvider using ddgs. Map raw
  results to SearchResult. No API key needed." (+ repo standards: TDD red-first,
  ≤150 code lines/file, ruff 0 + mypy clean, no hard-coded values, external calls
  via the API gatekeeper, log via LOG, coverage ≥85%.)
- **Context:** Epic 3's third task — the **default** search vendor on top of the
  3.1 interface + 3.2 registry. DuckDuckGo is the config default
  (`SEARCH_BACKEND=duckduckgo`) precisely because it is free and needs **no API
  key**, so a fresh install searches out of the box.
- **Outcome / pattern set:** Added `ddgs>=9` to `packages/core` deps and relocked
  (`uv lock` → ddgs 9.14.4) — the maintained successor to `duckduckgo-search`,
  imported `from ddgs import DDGS`. Verified the installed API rather than
  trusting docs: `DDGS().text(query, **kwargs) -> list[dict[str, Any]]` with keys
  `title`/`href`/`body`, and ddgs ships `py.typed`, so it is **typed** and needed
  **no** mypy ignore/override. `search/duckduckgo.py` maps each raw dict via
  `.get(key, "")` (missing keys → `""`, no crash; empty payload → `[]`, sub-PRD §6
  graceful handling). The single live `DDGS().text(...)` hop is isolated in a
  static `_fetch()` — a clear seam left for the API-gatekeeper wrapping in task
  13.6 — so the eventual rate-limit wiring is a one-spot change. No-hard-coded-
  values: `max_results` default = `DEFAULT_MAX_RESULTS`; the name `"duckduckgo"`
  is a single source `DUCKDUCKGO_BACKEND = constants.DEFAULT_SEARCH_BACKEND`,
  reused as both the class `name` and the `@register_search_provider` key, so the
  factory resolves the config default to this provider with zero factory edits.
  Re-exported from `search/__init__` (importing the subpackage triggers
  registration) and `agent_debate.core`. TDD red-first: `test_duckduckgo.py`
  (8 tests) **always monkeypatches a `_SpyDDGS` stand-in for the `DDGS` class**, so
  no test path touches the network — it asserts field mapping, default + explicit
  `max_results` pass-through, missing-key tolerance, empty → `[]`, name == key,
  Protocol conformance, and the factory default. Watched it fail
  (`ModuleNotFoundError`), then implemented to green. Gates: ruff/format clean,
  mypy clean (74 files), 274 passed, 100% coverage, line-limit + secret-scan pass.
  *Pattern: verify a new dependency's real return shape + typing from the installed
  package before mapping; isolate the one external call in a tiny seam method for
  later gatekeeper wrapping; mock the vendor client class in tests so the suite
  never hits the network.*

### Task 3.4 — Search resilience (Epic 3, issue #29)

- **Date:** 2026-05-31
- **Prompt (verbatim):** "Wrap provider calls with a timeout and retry/backoff;
  return an empty list (not an exception) on persistent failure, logged." (+ repo
  standards: TDD red-first, ≤150 code lines/file, ruff 0 + mypy clean, no
  hard-coded values, external calls via the API gatekeeper, log via LOG,
  coverage ≥85%.)
- **Context:** Epic 3's fourth task — the search layer's **own** graceful
  degradation, distinct from the API gatekeeper (Epic 13). The gatekeeper retries
  for the *rate/throughput* concern; this wrapper's single job is "**never throw to
  the caller** — a flaky/timed-out search returns `[]` (logged), so a debate never
  crashes from search" (sub-PRD §6).
- **Outcome / pattern set:** Added `search/resilient.py` —
  `ResilientSearchProvider`, a **transparent decorator** implementing the
  `SearchProvider` Protocol (so the registry/factory can return it in place of the
  inner provider). Per call it runs the inner `search` under a timeout, retries
  transient failures (`TimeoutError`/`ConnectionError`) with exponential backoff,
  and on persistent failure returns `[]` and logs the degradation. **Reused** the
  gatekeeper's `run_with_retry`/`backoff_delay` (`gatekeeper/_retry.py`) instead of
  duplicating backoff. No-hard-coded-values: `max_retries` + `retry_after_seconds`
  come from the **search** service `ServiceLimits` (`config/rate_limits.json`);
  `timeout_s` from `Settings.turn_timeout_s`; `sleep_fn` + `timeout_runner` are
  injected seams so tests assert exact delays with no real sleeping. Timeout
  approach (`search/_timeout.py`): run the synchronous inner call on a **daemon
  worker thread** and `join(timeout_s)` — still alive → raise `TimeoutError`
  (transient → retries, then degrades to `[]`); daemon so a hung call never blocks
  exit. Logging split into `search/_resilient_log.py` (a `retry` event per retry, a
  `timeout` event on degradation) to keep `resilient.py` ≤150 lines. TDD red-first:
  `test_search_resilience.py` (6 tests) — watched it fail (`ModuleNotFoundError`),
  implemented to green. Gates: ruff/format clean, mypy clean (78 files), 280
  passed, 100% coverage, line-limit + secret-scan pass.
  *Pattern: graceful degradation = a thin decorator that catches everything and
  returns the empty/neutral value (logged), distinct from rate-limit retry; reuse
  the existing retry policy rather than re-implementing backoff; bound a blocking
  sync call with a daemon-thread `join(timeout)` and inject the sleep/timeout seams
  so the suite never waits real time.*

### Task 4.2 — build_argument skill (Epic 4, issue #33)

- **Date:** 2026-05-31
- **Prompt (verbatim):** "Implement build_argument(...) that helps a debater
  structure a persuasive argument or rebuttal for its assigned side (claim,
  support, link to opponent's point). Register as a Pydantic AI tool with
  validated inputs." (+ repo standards: TDD red-first, ≤150 code lines/file,
  ruff 0 + mypy clean, no hard-coded values, external calls via the API
  gatekeeper, log via LOG, coverage ≥85%.)
- **Context:** The **first agent skill** (PRD §5.2). Skills are the named tools a
  debater exposes; later tasks add `analyze_opponent_argument` (4.3) and the real
  Pydantic AI tool registration (4.5).
- **Outcome / pattern set:** Created `core/skills/` mirroring the `search`/
  `gatekeeper` subpackage layout: `skills/models.py` (validated I/O models) +
  `skills/build_argument.py` (the function) + `skills/__init__.py` (re-export),
  with `agent_debate.core` re-exporting `ArgumentRequest`, `Argument`,
  `DebateSide`, `build_argument`. **Input** `ArgumentRequest` (frozen,
  `extra="forbid"`): `side: DebateSide` (a `StrEnum` pro/con — bad value fails
  loudly), non-empty `claim`, `supports: list[str]` (`min_length=1`, validator
  trims + drops blanks and rejects all-blank), optional `opponent_point`.
  **Output** `Argument` (frozen, `extra="forbid"`): side, claim, normalised
  supports, optional `rebuttal`, and a `conclusion`. The skill is **pure and
  deterministic** — it *structures* the agent-supplied content into the typed
  output and makes **no LLM/network call**, so the API gatekeeper (Epic 13) is
  **N/A** here (the LLM provides content as tool args; the skill arranges it).
  Anti-sycophancy (`docs/prds/anti-sycophancy.md` §2): when an `opponent_point` is
  given, the rebuttal quotes and *contests* it ("…— this does not hold,
  because:") rather than restating it. No hard-coded values — the rebuttal lead
  phrases and conclusion template live in `constants.py`. Optional `tool_call`
  debug line emitted via the LOG package (no run_id required for a pure call).
  TDD red-first: `test_build_argument.py` (10 tests) — watched it fail
  (`ImportError`), implemented to green. Gates: ruff/format clean, mypy clean
  (85 files), 305 passed, 100% coverage on the new subpackage (99.66% total),
  line-limit + secret-scan pass.
  *Pattern: a skill = a pure, deterministic structuring function over a validated
  Pydantic input → typed output; keep the LLM out of it so it stays testable and
  network-free (gatekeeper N/A); registration as a real Pydantic AI tool is a
  separate later task.*

_(add entries here as code is built — significant prompts that set a pattern,
unblocked a step, or changed a decision.)_
