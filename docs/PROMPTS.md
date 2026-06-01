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

### Task 4.3 — analyze_opponent_argument skill (Epic 4, issue #34)

- **Date:** 2026-05-31
- **Prompt (verbatim):** "Implement analyze_opponent_argument(...) that takes the
  opponent's last message, surfaces weaknesses/assumptions, and returns what to
  rebut. Validated inputs." (+ repo standards: TDD red-first, ≤150 code lines/file,
  ruff 0 + mypy clean, no hard-coded values, external calls via the API gatekeeper,
  log via LOG, coverage ≥85%.)
- **Context:** The **second agent skill** (PRD §5.2), reusing the `core/skills/`
  layout set by `build_argument` (4.2). A debater calls it to dissect the
  opponent's last message and **decide what to rebut**.
- **Outcome / pattern set:** Added `skills/analyze_opponent.py` plus two models in
  `skills/models.py`, re-exported from `agent_debate.core.skills` and
  `agent_debate.core`. **Input** `OpponentAnalysisRequest` (frozen,
  `extra="forbid"`): `side: DebateSide`, non-empty `opponent_message`, optional
  `weaknesses: list[str]` (validator trims + drops blanks). **Output**
  `OpponentAnalysis` (frozen): `side`, extracted `claims` (message split on
  `CLAIM_SPLIT_DELIMITERS` from `constants.py`), `weaknesses`, and a single
  prioritised `rebuttal_target`. Same **pure/deterministic, no-network** shape as
  `build_argument` (gatekeeper N/A). Anti-sycophancy (`docs/prds/anti-sycophancy.md`
  §2): `rebuttal_target` is **always** a concrete point — the strongest flagged
  weakness, else the opponent's lead claim — so the agent targets and rebuts, never
  concedes. **Composes** with `build_argument`: `rebuttal_target` feeds
  `ArgumentRequest.opponent_point` (asserted by an integration test). TDD red-first:
  `test_analyze_opponent.py` (12 tests) — watched it fail (`ImportError`),
  implemented to green. Gates: ruff/format clean, mypy clean (87 files), 317 passed,
  100% coverage on the new module (100% total), line-limit + secret-scan pass.
  *Pattern: extend an existing skills subpackage by adding one focused module +
  its models and two re-export lines; keep skills composable (one skill's output is
  a ready input for another) without coupling their models.*

### Task 4.4 — Controller skills: assess_drift / nudge / render_verdict (Epic 4, issue #35)

- **Date:** 2026-05-31
- **Prompt (verbatim):** "Implement controller skills: assess_drift(message, side)
  -> {captured, reason, confidence}; nudge(agent, reason) -> private correction;
  render_verdict(transcript) -> structured verdict. See docs/prds/anti-sycophancy.md."
  (+ repo standards: TDD red-first, ≤150 code lines/file, ruff 0 + mypy clean, no
  hard-coded values, external calls via the API gatekeeper, log via LOG, coverage ≥85%.)
- **Context:** The **controller's** three skills (PRD §5.3,
  `docs/prds/anti-sycophancy.md` §2–§4), reusing the pure/deterministic structuring
  shape set by `build_argument` (4.2) and `analyze_opponent` (4.3).
- **Outcome / pattern set:** Added `skills/controller.py` (the three functions) plus
  five models in `skills/models.py` (`DriftRequest`, `DriftAssessment`,
  `NudgeMessage`, `TranscriptTurn`, `VerdictRequest`, `Verdict`), re-exported from
  `agent_debate.core.skills` and `agent_debate.core`; concession phrases, confidence
  weights, and reason/correction/rationale/tie templates are named constants in
  `constants.py`. **`assess_drift`** returns `{captured, reason, confidence∈[0,1]}` —
  caller-supplied `signals` (controller-LLM heuristics) force capture, else a
  concession-phrase scan; deepened by Epic 8.1. **`nudge`** returns a private
  `NudgeMessage` with `is_debate_turn=False` (anti-sycophancy §2.4/§4: logged +
  surfaced, never a turn). **`render_verdict`** derives `winner`/`scores`/`rationale`
  from the transcript (LLM-supplied `VerdictRequest` verbatim, else a per-side score
  tally with a tie on equal) and exposes **only** debate-derived fields — never a
  pre-held controller stance (PRD §5.3), asserted by a dumped-keys test; deepened by
  Epic 8.3. Same pure/no-network shape (gatekeeper N/A). TDD red-first:
  `test_controller_skills.py` (20 tests) failed on `ImportError`, then to green.
  Gates: ruff/format clean, mypy clean (89 files), 336 passed, 100% on the new
  module (99.81% total), line-limit + secret-scan pass.
  *Pattern: a controller skill is the same validated-input → typed-output structuring
  helper as a debater skill; judgement (drift signals, the winner) arrives as
  arguments, and the verdict model is deliberately shaped to carry no controller
  stance — only debate-derived fields.*

### 7.1 — Security sanitisation gatekeeper (PRD §5.7)

- **Prompt (verbatim):** see `.building_tasks_logs/7.1-secgate-sanitise.json`.
- **Why it mattered:** establishes the *security* gatekeeper — deliberately a
  separate subpackage (`core/security/`) from the *API/rate-limit* gatekeeper
  (`core/gatekeeper/`, Epic 13). The two are easy to conflate; keeping them apart
  is the load-bearing decision Epic 7 (7.2–7.5) and the `web_search` skill (4.1)
  build on.
- **Outcome / pattern set:** Added `security/` with `constants.py` (`DEFAULT_MAX_
  UNTRUSTED_LEN`, `NEUTRALISED_MARKER`, `INJECTION_PATTERNS` — all named, no inline
  magic), `normalise.py` (NFKC + zero-width/control strip + whitespace collapse)
  and `sanitiser.py` (`sanitize_untrusted_text` + `SecurityGatekeeper`), re-exported
  from `agent_debate.core.security` and `agent_debate.core`. Strategy is
  **normalise → neutralise → cap**: normalise first so disguised keywords (fullwidth,
  zero-width-split) reassemble *before* the injection-pattern pass redacts them with
  an inert marker; cap last to bound payload/token blast radius. Pure text — no
  network (4.1's search results flow through it); when something is neutralised and a
  `run_id` is bound, an observable `system` event is logged via LOG. TDD red-first:
  `test_security_sanitiser.py` (14 tests) failed on `ModuleNotFoundError`, then green.
  Gates: ruff/format clean, mypy clean (94 files), 351 passed, 100% on the new module,
  line-limit + secret-scan pass.
  *Pattern: untrusted text is data, never instructions — fold it to a canonical
  form, redact the known injection phrasings to a visibly-inert marker, then
  length-cap; thresholds/patterns live in one named `constants.py`, overridable per
  call.*

### 7.2 — Input validation (PRD §5.7)

- **Prompt (verbatim):** see `.building_tasks_logs/7.2-input-validation.json`.
- **Context:** 7.1 *sanitises* (silently neutralises) untrusted text. 7.2 is the
  complementary **validation** posture for *direct user input* at a trusted
  boundary (the debate topic, a web-search query): reject abusive/oversized input
  with a clear, typed error instead of mangling it.
- **Outcome / pattern set:** Added `security/validation.py` —
  `validate_topic` / `validate_search_query` (length cap + control/escape-char
  rejection + non-empty), a typed `InvalidInputError(ValueError)` whose message
  names the field and the cap, and `TopicInput` / `SearchQueryInput` Pydantic
  models that reuse the same functions via `field_validator` (PRD §5.7 "tool
  inputs validated"). New caps `MAX_TOPIC_LEN` (500) / `MAX_QUERY_LEN` (256) live
  in `security/constants.py` (single source, no inline magic); all re-exported
  from `agent_debate.core.security` and `agent_debate.core`. TDD red-first:
  `test_security_validation.py` (16 tests) failed on an `ImportError`, then green.
  Gates: ruff/format clean, mypy clean (96 files), 367 passed, 100% on the new
  module, line-limit + secret-scan pass.
  *Pattern: sanitise untrusted text (data) but **validate-and-reject** direct user
  input — distinct postures sharing one named-constant config; expose both a
  function and a Pydantic model so every surface validates identically.*

### 7.4 — Secret hygiene check (PRD §7.4)

- **Prompt (verbatim):** see `.building_tasks_logs/7.4-secret-hygiene.json`.
- **Context:** Two secret defences already existed independently — the build-time
  scanner `scripts/secret_scan.py` (0.11) and the runtime LOG redactor (1.4).
  7.4 makes their *coverage explicit and coordinated*: the scan must cover logs
  too, and one test must prove a single planted fake key is caught by BOTH.
- **Outcome / pattern set:** Added `.jsonl` to the scanner's `SCANNED_SUFFIXES`
  so a stray committed `runs/*.jsonl` log artifact is covered (logs are normally
  gitignored, but the scan must not silently miss one). Added
  `tests/test_secret_hygiene.py` (5 tests) proving coordination: (a) `log_event`
  with the fake key in its payload → the on-disk JSONL omits the key and carries
  the `REDACTED` marker; (b) the same key written to a tmp source file and a tmp
  `runs/*.jsonl` is flagged by `find_secrets`. The planted key is assembled from
  string PARTS at runtime (`"sk-" + "ant-" + …`) so no `sk-ant-…` literal is
  committed — the live CI secret-scan gate still exits 0. TDD red-first: the
  log-coverage assertion failed (`.jsonl` absent from `SCANNED_SUFFIXES`), then
  green after the one-line config addition. Gates: ruff/format clean, mypy clean
  (97 files), 372 passed, 100% coverage, line-limit + secret-scan exit 0.
  *Pattern: a build-time gate and a runtime filter share ONE detector config and
  ONE integration test that plants a single fake key — proving both layers catch
  it by design, not coincidence; build the fake secret from parts so the
  coordination test never trips the very gate it exercises.*

### 7.5 — Security tests (Epic-7 acceptance consolidation, PRD §5.7)

- **Prompt (verbatim):** see `.building_tasks_logs/7.5-security-tests.json`.
- **Context:** 7.1 (sanitiser) and 7.2 (validators) already had per-task unit
  tests at 100%. 7.5 is the Epic-7 acceptance/consolidation pass (mirroring
  1.5 / 2.5 / 3.6 / 13.7): prove the §5.7 behaviours END-TO-END through the
  public API — a prompt-injection payload *embedded in a (mocked) web-search
  result* is neutralised, and oversized/abusive *direct input* is rejected.
- **Outcome / pattern set:** TDD red-first on a genuine gap — the acceptance test
  needed to sanitise a whole `SearchResult` (injection can hide in `title` *or*
  `snippet`), but only a per-string `sanitize_untrusted_text` existed. Added
  `security/result.py::sanitize_search_result(result)` (net-new source): copies
  the frozen result with `title`/`snippet` run through the sanitiser, `url` left
  as structural provenance. Then `tests/test_security_acceptance.py` (11 tests):
  injection in a snippet/title from a *mocked* DuckDuckGo provider is neutralised
  while benign text survives; over-length topic/query and empty/control-char
  input raise the typed `InvalidInputError`; and the trust-boundary posture is
  asserted side by side — untrusted text is *sanitised* (never raises), direct
  input is *validated* (rejected loudly). No network (DDGS monkeypatched), no
  committed secrets. Gates: ruff/format clean, mypy clean (99 files), 383 passed,
  100% coverage, line-limit + secret-scan exit 0.
  *Pattern: the acceptance pass is allowed to surface a real composition gap —
  when the end-to-end story needs an object-level seam the units never built,
  add the minimal typed helper (sanitise both prose fields, keep structural ones)
  rather than hand-threading fields in the test; assert the two security postures
  (sanitise-untrusted vs validate-trusted) in one place so the boundary is law.*

### 5.1 — Pro debater agent (Epic 5, PRD §5.2, anti-sycophancy §2)

- **Prompt (verbatim):** see `.building_tasks_logs/5.1-agent-pro.json`.
- **Context:** First agent of the system. PRD §5.2 requires each debater to be a
  Pydantic AI `Agent` whose **system prompt** states its side, the rules (word
  limit, must rebut), and an **explicit list of the skills it has + when to use
  them**. `web_search` (skill task 4.1) and full tool registration (4.5) are still
  blocked, so 5.1's deliverable is the AGENT carrying the correct system-prompt
  text — `web_search` is named in the prompt only, not attached.
- **Outcome / pattern set:** New `core/agents/` subpackage, **prompt text split
  from the factory**: `prompts.py` = pure `build_debater_system_prompt(side, *,
  max_words, skills=DEBATER_SKILLS) -> str` + named constants (no inlined values —
  side labels FOR/AGAINST, rule templates, and the `DEBATER_SKILLS` tuple with a
  one-line "when to use" each); `debater.py` = `create_pro_debater(...)` over a
  **side-parameterizable `create_debater(side, ...)` seam** so task 5.2 (Con)
  reuses it by flipping the `DebateSide`. `max_words` is read from `Settings`
  (changing it changes the prompt) — never hard-coded. Anti-sycophancy §2 is baked
  into the rules: MUST rebut + do-NOT-concede-merely-because-convincing.
  *Pattern: agent factories accept an **injected `model`** so tests pass a
  pydantic-ai `TestModel` — the eager Anthropic client (needs `ANTHROPIC_API_KEY`)
  is never built, the static `agent._system_prompts` is inspected, and the whole
  suite stays offline/key-free. Keep the prompt builder pure and side-parameterised
  so the next agent is a 3-line wrapper, not a copy.*

### 5.2 — Con debater agent (Epic 5, PRD §5.2)

- **Prompt (verbatim):** see `.building_tasks_logs/5.2-agent-con.json`.
- **Context:** Second agent. The Con debater **mirrors** Pro (5.1) with
  `side=AGAINST` and the **same** rules and skill list — only the side flips.
- **Outcome / pattern set:** Because 5.1 built the side-parameterizable
  `create_debater(side, ...)` seam and the shared `build_debater_system_prompt`
  builder, 5.2 is a **3-line wrapper**: `create_con_debater(...)` returns
  `create_debater(DebateSide.CON, ...)`, exactly as `create_pro_debater` does for
  `PRO`. **Zero prompt logic duplicated** — DRY pays off. Re-exported from
  `agent_debate.core.agents` / `agent_debate.core`. *Pattern: the mirror test is
  the contract — assert `con_prompt.replace("AGAINST", "FOR") == pro_prompt` at both
  the builder and the constructed-agent level, so any future drift between the two
  debaters' rules/skills fails loudly rather than silently diverging.*

### 5.3 — Controller agent (Epic 5, PRD §5.3)

- **Prompt (verbatim):** see `.building_tasks_logs/5.3-agent-controller.json`.
- **Context:** Third and last agent — the moderator/judge. Unlike the debaters, the
  Controller **knows both sides** (Pro = FOR, Con = AGAINST) but its defining
  constraint is anti-sycophancy §4: it must **NEVER reveal its own stance/opinion**
  or hint which side it leans. It detects drift, nudges privately (a correction that
  does **not** count as a debate turn), and renders a structured verdict.
- **Outcome / pattern set:** Because `prompts.py` was already near the 150-line cap,
  the controller prompt got its **own module** `agents/controller_prompts.py` rather
  than compressing the debater builder — split, don't compress. `create_controller`
  reuses the debater factory pattern (resolve `CONTROLLER_MODEL` or inject a
  `TestModel`, log via LOG). *Pattern: the negative test is the contract — assert the
  prompt **does not** leak a pre-held stance (no "I think Pro/Con is right", "I lean",
  "in my opinion the…") AND **does** carry the explicit "never reveal" instruction, so
  any future edit that makes the judge opinionated fails loudly.*

### 5.4 — Independent agent contexts (Epic 5, PRD §5.4 / anti-sycophancy §2)

- **Prompt (verbatim):** see `.building_tasks_logs/5.4-independent-contexts.json`.
- **Context:** Plumbing (no LLM prompt) for the core anti-sycophancy property —
  "Debaters never share a chat thread." Each agent (Pro/Con/Controller) keeps its
  **own** ordered message history in a separate `AgentContext`; the engine (Epic 6)
  feeds `AgentContext.message_history()` to `agent.run(message_history=…)`.
- **Outcome / pattern set:** Representation is a lightweight, typed, frozen `Turn`
  (`role`/`content`) rather than raw pydantic-ai `ModelMessage`, mapped to a run
  history via `Turn.to_model_message()` — trivially isolatable and easy for 5.5/5.6
  to extend. `append_user` is the seam 5.6 uses to drop an *already-framed* opponent
  message as a `user` turn in the agent's **own** thread (relay framing itself is 5.6,
  not here). *Pattern: the isolation test is the contract — appending to the Pro
  context must leave the Con context empty (and the three contexts are distinct
  objects), so any future change that re-merges the threads fails loudly.* Adding the
  re-exports would have pushed `core/__init__.py` past 150 lines, so per "split, don't
  compress" the secondary names (`Role`, `CONTROLLER_IDENTITY`) export only from
  `agent_debate.core.agents` while the key surface stays on `agent_debate.core`.

### 5.5 — Per-turn side anchoring (Epic 5, PRD §5.2 / anti-sycophancy §2 mechanism 2)

- **Prompt (verbatim):** see `.building_tasks_logs/5.5-side-anchoring.json`.
- **Context:** Re-inject the agent's assigned side (FOR/AGAINST) + an explicit "do not
  concede merely because the opponent is convincing" instruction **before each turn**
  — in addition to the system prompt, as a per-turn reminder.
- **Outcome / pattern set:** New module `agents/anchoring.py`. `build_side_anchor(side,
  *, max_words=None)` builds the reminder from named templates; the anti-concession
  wording is hoisted into one shared constant `ANTI_CONCESSION_RULE` in `prompts.py`,
  reused by BOTH the system-prompt rules and the anchor (DRY — one source). `anchor_turn`
  appends the anchor as a `user` turn into THAT agent's **own** `AgentContext` (reuses
  5.4 isolation), folding an already-framed 5.6 `opponent_message` into the same turn
  (anchor first). *Pattern: the isolation + per-round tests are the contract — anchoring
  Pro must leave Con's history empty, and anchoring twice must add the reminder both
  rounds, so any change that drops the per-turn re-injection fails loudly.*

### 5.6 — Adversarial relay (Epic 5, PRD §5.2 / anti-sycophancy §2 mechanism 1)

- **Prompt (verbatim):** see `.building_tasks_logs/5.6-adversarial-relay.json`.
- **Context:** Pass the opponent's last message into an agent framed adversarially
  (*"Your opponent argued: «…». Rebut it."*), NOT as an agreeable peer turn.
- **Outcome / pattern set:** New module `agents/relay.py`. `build_adversarial_relay`
  **sanitises the opponent message first** (`security.sanitize_untrusted_text` —
  opponent text is another agent's untrusted output) and only then wraps it in the
  single named `ADVERSARIAL_RELAY_TEMPLATE` (the `«»` framing lives once). The
  per-turn helper `relay_opponent_turn` reuses `anchoring.anchor_turn(...,
  opponent_message=framed)` so the side anchor + framed relay combine into ONE
  `user` turn in the agent's **own** context. *Pattern: untrusted text re-entering a
  prompt must pass the security gatekeeper BEFORE framing (sanitise-then-frame), and
  the isolation test is the contract — the relay enters as a `user` turn in the
  agent's own context and never touches the opponent's thread; an "Ignore previous
  instructions…" payload must be neutralised in what reaches the prompt.*

### 5.7 — Word-limit enforcement (Epic 5, PRD §5.2 / §7)

- **Prompt (verbatim):** see `.building_tasks_logs/5.7-word-limit.json`.
- **Context:** The prompt already instructs `<= max_words`; this task **verifies after
  generation** — if a message exceeds `MAX_WORDS`, trim it and log a violation.
- **Outcome / pattern set:** New module `agents/word_limit.py`. `count_words` defines the
  one counting rule (`str.split()` — any whitespace run is one separator; empty/whitespace
  text = 0 words). `enforce_word_limit(text, *, max_words, run_id=None, ...)` returns a
  frozen `WordLimitResult(text, violated, original_words)`: within the limit (including
  exactly `max_words`) it returns the text verbatim with `violated=False` and logs nothing;
  over the limit it **trims to exactly `max_words` words** at a clean word boundary (first
  N tokens re-joined with single spaces — no sentence heuristic) and, when a `run_id` is
  given, logs a violation. *Decision: the LOG schema has no `"violation"` event_type, so a
  word-limit breach is logged as a `system` event with payload `{"violation": "word_limit",
  "words": N, "limit": max_words, "trimmed": true}`.* `max_words` is config-driven (caller
  passes `Settings.max_words`; never hard-coded), and the event_type/agent/tag are named
  constants in `core.constants`. *Pattern: prompt-instruct AND post-verify — the same
  policy is both stated in the prompt and enforced deterministically after generation; the
  enforcement helper is a clean reusable seam the Epic-6 engine calls per turn.*

### 5.8 — Agent/prompt acceptance tests (Epic-5 consolidation, PRD §5.2/§5.3, anti-sycophancy)

- **Prompt (verbatim):** see `.building_tasks_logs/5.8-agent-tests.json`.
- **Context:** The Epic-5 acceptance/consolidation pass (mirrors 1.5/2.5/3.6/7.5/13.7). The
  per-task suites (5.1–5.7) already cover each unit (~100% agents coverage); the value here
  is asserting the four headline anti-sycophancy guarantees together, **through the public
  `agent_debate.core` API**, as one integrated story.
- **Outcome / pattern set:** New `tests/test_agents_acceptance.py` (5 tests): both debater
  prompts list their named skills; the controller prompt mirrors "never reveal" and leaks no
  pre-held stance; the relay framing is the adversarial «»/rebut frame, sanitised, landing as
  a USER turn in the agent's OWN context (5.4 isolation); over-`MAX_WORDS` output is trimmed
  to the config limit and logs a `system` violation. *Genuine gap fixed (TDD red-first): the
  relay + word-limit symbols (`relay_opponent_turn`, `build_adversarial_relay`,
  `enforce_word_limit`, `count_words`, `WordLimitResult`, `anchor_turn`, `build_side_anchor`,
  `ADVERSARIAL_RELAY_TEMPLATE`, `ANTI_CONCESSION_RULE`) were only on the `…agents` subpackage,
  not the top-level hub — so the four behaviours couldn't be asserted via `agent_debate.core`.
  Added the 9 re-exports.* Pattern (split, not compress): the hub `__init__` already sat at
  the 150-line limit, so the agents re-export group was factored into a `_agents_public.py`
  shim (explicit imports + an explicit, mypy-checked `__all__`), pulled in via a single `*`
  import, with a scoped `per-file-ignores = [F403, F405]` for that one re-export `__init__`.

### 6.1 — DebateConfig + DebateResult (Epic 6, orchestration sub-PRD §2, issue #46)

- **Prompt (verbatim):** see `.building_tasks_logs/6.1-debate-models.json`.
- **Context:** First task of Epic 6 (the orchestration engine) — the **typed models only**,
  building clean seams for the 10-vs-10 loop, timeout wrapper, closing discussion, event
  streaming and SDK entrypoint that follow (6.2+). No loop is built here.
- **Outcome / pattern set:** New `engine/` subpackage — `engine/models.py` (`DebateConfig`,
  the input contract) and `engine/result.py` (`DebateResult` output + `DebateMessage`,
  `ToolCallRecord`, `CostTotals`). **Config-driven:** `DebateConfig.from_settings(settings)`
  lifts every tunable (rounds/max_words/timeout/retries/models, incl. the resolved per-side
  pro/con fallback) from `Settings` — no hard-coded defaults; the model only validates bounds
  (`rounds/max_words/turn_timeout_s > 0`, `max_retries >= 0`). `DebateResult` reuses the
  existing skills `NudgeMessage` / `Verdict` / `DebateSide` rather than re-modelling them, and
  `CostTotals.from_messages` aggregates token/cost/latency (mirroring `GatekeeperStatus.
  from_services`). `DebateMessage.word_count` is a computed field, so the message model uses
  `extra="ignore"` to let the JSON dump round-trip cleanly. *Pattern (split, not compress):*
  the hub `__init__` sat at the 150-line cap, so the engine re-export group was factored into
  a `_engine_public.py` shim (mirroring `_agents_public.py`); the hub splices the shim's
  `__all__` via `*_engine_public.__all__` (no new literal entries) to stay under the cap.

## 6.2 — Topic setup & private side assignment

- **Prompt (verbatim):** see `.building_tasks_logs/6.2-topic-setup.json`.
- **Context:** The SETUP step of the debate flow (orchestration §3.1) — the controller
  receives/sets the topic, privately assigns Pro = FOR and Con = AGAINST, and keeps its own
  stance hidden. NOT the loop (that is 6.3).
- **Outcome / pattern set:** New `engine/setup.py` — `setup_debate(topic, config, *, settings,
  models, run_id, runs_dir) -> DebateSetup`. (1) VALIDATES the untrusted topic via the 7.2
  `validate_topic` (rejects empty/control-char/oversized with the typed `InvalidInputError`).
  (2) Privately ASSIGNS Pro = FOR / Con = AGAINST as a fixed STRUCTURED mapping keyed by the
  `DebateSide` constants, labelled via the existing `SIDE_LABEL` (no hard-coded side strings).
  (3) Builds the three agents (Pro/Con/Controller) on injected per-agent `TestModel`s (offline,
  no network/key) + three ISOLATED contexts (`create_debate_contexts`). **No model call is made**
  — setup only prepares state; the loop's calls route through the API gatekeeper (Epic 13) in
  6.3. *Controller neutrality pattern:* `DebateSetup` is a frozen dataclass with deliberately
  NO stance/opinion field — a test asserts no `stance`/`opinion`/`winner`/`lean`/`bias` field
  exists, and the single `system` setup log event (topic + assignment, `round=0`) carries no
  stance. Re-exports added to `engine/__init__` + the `_engine_public.py` shim (split, not
  compress).

## 6.3 — Main 10v10 debate loop

- **Prompt (verbatim):** see `.building_tasks_logs/6.3-debate-loop.json`.
- **Context:** The MAIN LOOP of the debate flow (orchestration §3.2) — for
  `round = 1..config.rounds` alternate Pro turn → controller drift-check (+nudge) → Con turn
  (must rebut Pro) → controller drift-check (+nudge). NOT the timeout/retry wrapper (6.4) or
  verdict/closing discussion (6.5/6.8).
- **Outcome / pattern set:** Split into four small files (each ≤ 150 code lines). `engine/loop.py`
  — `run_debate_loop(setup, config, *, gatekeeper=None, run_id, runs_dir) -> DebateResult`
  drives the rounds, tracking each side's last message so Con rebuts Pro's latest and Pro (from
  round 2) rebuts Con's last. `engine/turn.py` — `run_debate_turn(...)`: inject side anchor (+
  adversarial relay of the opponent) into the debater's OWN context, generate via the gatekeeper,
  `enforce_word_limit` (trim + log), append + log a `message` event. `engine/drift.py` —
  `run_drift_check(...)`: `assess_drift` → on capture `nudge` (NOT a debate turn) + log a `nudge`
  event. `engine/gatekeeper_proto.py` — a `Gatekeeper` `Protocol` so the loop depends on the
  `execute` *shape* and tests inject a spy. **Gatekeeper pattern:** every debater model call
  routes through `gatekeeper.execute(agent.run_sync, message_history=ctx.message_history(),
  service="anthropic")`; absent an injected gatekeeper the loop builds a default `ApiGatekeeper`
  from `load_rate_limit_config()`. The 6.4 timeout/retry wraps exactly at that `execute` call
  (clean seam, no behaviour change). pydantic-ai note: `run_sync` is called with only
  `message_history` (its trailing `user` turn is the live prompt); `.usage` is now a property
  (input/output tokens fold into `DebateMessage`/`CostTotals`). Verdict left `None` and
  `closing_discussion` `[]` as 6.5/6.8 seams. Re-exports added to `engine/__init__` + the
  `_engine_public.py` shim.

## 6.4 — Timeout + retry wrapper for per-turn model calls

- **Prompt (verbatim):** see `.building_tasks_logs/6.4-timeout-retry.json`.
- **Context:** Wrap the per-turn MODEL CALL (the `gatekeeper.execute(agent.run_sync, ...)` seam in
  `engine/turn.py`) to enforce `config.turn_timeout_s` (cancel on timeout), retry up to
  `config.max_retries` with backoff, and after exhaustion mark the turn FAILED + inform the
  controller — logging `timeout`/`retry` events. Orchestration §4. NOT verdict/closing (6.5/6.8).
- **Outcome / pattern set:** New `engine/_call.py` — `generate_turn_output(gatekeeper, api_call,
  *, message_history, service, config, run_id, round_, agent, runs_dir, sleep_fn, timeout_runner)`
  routes the call THROUGH `gatekeeper.execute` (every external call still does), **reusing** the
  search layer's thread-based `run_with_timeout` (daemon worker joined for `timeout_s`; on timeout
  `TimeoutError` raised + the hung worker abandoned — the documented cancel semantics for the
  synchronous `run_sync` path) and the gatekeeper's `run_with_retry`/`backoff_delay`/`is_transient`
  retry policy (no duplication). **Compose-not-double-count:** the gatekeeper retries the
  rate/throughput concern INSIDE `execute`; this wrapper composes AROUND `execute` to add the
  `turn_timeout_s` + turn-failure semantics; backoff base = the service's `retry_after_seconds`
  (single source of truth). A non-transient error (e.g. `ValueError`) is NOT retried — it
  propagates raw; only an exhausted transient/timeout budget raises `TurnFailedError`. New
  `engine/_call_log.py` — `_CallLog` emits `timeout`/`retry`/`system` events (split to keep
  `_call.py` ≤ 150 code lines). **Turn-failed policy:** `turn.py` catches `TurnFailedError` and
  returns a `failed=True` `DebateMessage` marker (new field on `DebateMessage`); the wrapper has
  already logged a `system` event (`payload.turn_failed`) informing the controller; `loop.py`
  records the marker and returns `None` as the next `opponent_message` so the opponent gets a fresh
  anchor (never rebuts a failure). The debate runs all rounds and never crashes. **Test seams:**
  `sleep_fn` + `timeout_runner` injected so tests are deterministic and fast (no real
  threads/sleeping); backoff delays asserted via a recording `sleep_fn`. New constants
  `TURN_{TIMEOUT,RETRY,FAILED}_EVENT_TYPE` + `TURN_FAILED_TAG`/`TURN_FAILED_CONTENT` (no hard-coded
  values; caps from `DebateConfig`). `run_debate_turn` gained `sleep_fn`/`timeout_runner` defaults
  (backward-compatible — existing `test_debate_loop.py` stayed green).

### 13.6 — Route ALL calls through the gatekeeper + no-bypass test (Epic 13, api-gatekeeper §2/§6, issue #95)

- **Prompt (verbatim):** "Route every external call (Pydantic AI model calls and SearchProvider
  calls) through ApiGatekeeper. Add a test asserting there is no bypass path."
- **Context:** MODEL calls already routed via `gatekeeper.execute(service="anthropic")` (engine
  `turn.py`/`_call.py`, tasks 6.3/6.4); SEARCH calls (`duckduckgo.py`'s `DDGS().text()` in the
  `_fetch` seam) were not yet gatekeeper-routed. The sub-PRD §6 acceptance is "no bypass exists
  (test-enforced)".
- **Outcome / pattern set:** New `search/gatekept.py` — `GatekeptSearchProvider`, a transparent
  decorator over any `SearchProvider` (analogous to `ResilientSearchProvider`) that routes the
  inner `search` through `gatekeeper.execute(self._inner.search, query, max_results=...,
  service=SEARCH_SERVICE)` instead of calling it directly. The factory
  `create_search_provider(settings, *, gatekeeper=None)` wraps the active provider in it when a
  gatekeeper is supplied (backward-compatible default keeps the bare provider, so existing
  search/registry tests stay green). New `constants.SEARCH_SERVICE = "search"` (named, mirrors
  `LOOP_MODEL_SERVICE`; limits read from `config/rate_limits.json`, 0 hard-coded). `name` is a
  plain settable attribute (`self.name = inner.name`) so the structural `SearchProvider` protocol
  is satisfied when returned typed. **No-bypass test (`test_no_bypass.py`) — two complementary
  checks:** (a) *behavioral* — a spy gatekeeper asserts the gatekept provider invokes
  `execute(service="search")` (model routing already proven in `test_turn_timeout.py`); (b)
  *structural/static* — a maintainable source grep over `packages/*/src` (comments + string
  literals stripped via `tokenize`, so docstring prose never false-positives) asserts the only
  direct external-call constructs (`DDGS(`, `.run_sync(`, `.run_async(`) live inside a named
  `_ALLOWLISTED_FILES` constant; a NEW direct call elsewhere fails CI, catching a future bypass. A
  guard test asserts the scan globbed real files (no vacuous pass).

### 4.1 — web_search skill (Epic 4, PRD §5.2 / search-plugin §5, issue #32)

- **Prompt (verbatim):** see `.building_tasks_logs/4.1-web-search-skill.json`.
- **Context:** all building blocks already existed — `create_search_provider(...,
  gatekeeper=)` (wraps the active backend in `GatekeptSearchProvider`, routing
  through `ApiGatekeeper.execute(service="search")`), `ResilientSearchProvider`
  (timeout/retry → `[]`), `validate_search_query` (7.2), and
  `sanitize_search_result` (7.5). 4.1 is the skill that *composes* them into the
  flow the debater calls. Full Pydantic AI tool registration is 4.5; here it is
  the tool-ready function + validated input model.
- **Outcome / pattern set:** TDD red-first (`tests/test_web_search.py`, 9 tests,
  watched fail on the missing import). New `skills/web_search.py::web_search(query,
  *, settings=None, gatekeeper=None, max_results=None, run_id=None, runs_dir=…)`:
  **validate** (`validate_search_query`, rejects oversized/blank/control-char)
  → **gatekeeper-routed provider** (built in a split `skills/_web_search_build.py`
  so the skill file stays a thin policy flow under 150 lines: `create_search_provider`
  for the API-gatekeeper hop, wrapped in `ResilientSearchProvider` whose retry knobs
  come from the `search` `ServiceLimits` and timeout from `Settings.turn_timeout_s`
  — 0 hard-coded) → **sanitise** each result through `sanitize_search_result`
  *before* returning → **log** one `tool_call` event (query + result count) via the
  LOG package. `WebSearchInput` (in `skills/models.py`) reuses the 7.2 validator so
  it is tool-ready. New named constants `WEB_SEARCH_EVENT_TYPE/_TOOL/_DEFAULT_RUN_ID`;
  `max_results` defaults to `DEFAULT_MAX_RESULTS`. Provider-agnostic: a test proves
  it works with the tavily stub too. While wiring re-exports, `core/__init__.py`
  crossed the 150-code-line limit — fixed structurally by switching the skills
  re-export to the existing `import *` + `*skills.__all__` splat pattern (same shim
  `_engine_public`/`_agents_public` already use), which *reduced* the file to 121
  lines rather than hacking the cap. Gates: ruff/format clean, mypy clean (138
  files), 522 passed, 100% coverage (new files 100%), line-limit + secret-scan exit 0.
  *Pattern: a skill that touches the network threads BOTH gatekeepers — API
  (rate-limit, via the provider factory) on the way out and security (sanitise) on
  the way back — and splits provider assembly into a private `_build` helper so the
  policy flow file stays small; when a re-export aggregator outgrows the line cap,
  collapse it onto the package's own `__all__` splat instead of raising the limit.*

### 4.5 — Register skills as Pydantic AI tools (Epic 4, PRD §5.2/§5.3, issue #36)

- **Prompt (verbatim):** see `.building_tasks_logs/4.5-register-tools.json`.
- **Context:** the six skills (4.1–4.4) already existed as functions + Pydantic
  input models, and the agents (Epic 5) already carried system prompts *naming*
  those skills — but did **not** attach them as tools. 4.5 closes that loop:
  register each skill as a real `pydantic_ai.Tool` and group them per agent.
- **Outcome / pattern set:** TDD red-first (`tests/test_skill_tools.py`, 17 tests,
  watched fail on the missing `controller_tools` import). New `agents/tools.py`:
  two grouping factories `debater_tools(settings=None, gatekeeper=None)` and
  `controller_tools()` returning `list[Tool]`, wired into `create_debater` /
  `create_controller` via `Agent(model, …, tools=[…])` (pydantic-ai v1.104.0).
  Each skill is wrapped in a thin closure whose **single argument is a Pydantic
  input model**, so pydantic-ai validates at the tool boundary — a malformed
  payload raises `ValidationError` before the skill runs (introspect registered
  tools via `agent._function_toolset.tools`; validate via
  `tool.function_schema.validator.validate_python(payload)`). Tool **names** come
  from `DEBATER_SKILLS` / `CONTROLLER_SKILLS` + `WEB_SEARCH_TOOL` (no literal
  inlined) so they cannot drift from the names the prompt advertises. `web_search`
  captures `settings`/`gatekeeper` in its closure and threads them through, keeping
  the no-bypass property (external call still routes via the API gatekeeper, Epic
  13). Added one input model (`NudgeRequest`) since `nudge` had no request model.
  Sets are disjoint (debater has no controller tools and vice versa).
  *Pattern: to make every skill a validated tool, wrap each function in a closure
  taking ONE Pydantic input model and register it as `Tool(fn, name=<constant>)`
  passed to the `Agent` at construction — name tools from the same skill-list
  constants the system prompt uses so registration and prompt can never diverge;
  return tool sets from small per-agent grouping factories so the cross-wiring is
  impossible by construction and the gatekeeper is threaded only where needed.*

### 8.1 — Deepen assess_drift logic (Epic 8, anti-sycophancy §3, issue #60)

- **Prompt (verbatim):** see `.building_tasks_logs/8.1-assess-drift.json`.
- **Context:** 4.4 shipped a light baseline `assess_drift` (caller signals force
  capture, else a flat concession-phrase scan at fixed 0.6 confidence). 8.1 deepens
  the LOGIC to robustly classify the four §3 drift signals while keeping the public
  `assess_drift` / `DriftAssessment` contract STABLE so 4.4's callers + the engine
  drift tests stay green.
- **Outcome / pattern set:** TDD red-first (`tests/test_assess_drift.py`, 13 tests,
  watched fail on the missing `DRIFT_CAPTURE_THRESHOLD`). New deterministic detector
  `skills/_drift_logic.py` (`detect_drift(message, opponent_message=None) ->
  (confidence, labels)`) fires four named §3 signals — **concession**, **agreement
  / framing-adoption**, **hedging**, and **restating-without-rebuttal** (token
  overlap ≥ `DRIFT_OVERLAP_THRESHOLD` with the opponent AND no rebuttal marker). A
  transparent **additive weighted** confidence (named per-signal weights, clamped to
  `[0,1]`); `captured = confidence >= DRIFT_CAPTURE_THRESHOLD`; reason names the
  fired signal(s). All phrase sets / weights / threshold / labels are named
  constants in a dedicated `skills/_drift_constants.py` (split out of
  `constants.py`, which would otherwise exceed the 150-line cap; the lexicon now
  sits next to its logic). `DriftRequest` gained an optional `opponent_message`
  (back-compat default `None`) and `assess_drift` a 4th optional `opponent_message`
  param — the first three positional params (`message, side, signals`) are unchanged
  so `tools.py`'s positional call still works (now forwards opponent context).
  PURE/no-network heuristic, so the API gatekeeper (Epic 13) is N/A. Gates green:
  ruff/format/mypy clean, 602 passed, 100% coverage, line-limit + secret-scan clean.
  *Pattern: deepen a heuristic behind a stable public contract by extracting the
  scoring into its own module with a `(confidence, labels)` return and ALL tuning as
  named constants in a sibling `_constants` module — extend the input model with a
  back-compat-default optional field rather than reordering params, so existing
  positional callers and tests keep passing.*

## 6.5 — Closing discussion phase (`engine/closing.py`)

- **Prompt (verbatim):** see `.building_tasks_logs/6.5-closing-discussion.json`.
- **Context:** the 6.3 loop produced exactly `rounds*2` Pro/Con turns and left
  `DebateResult.closing_discussion=[]` as a seam. Orchestration §3.3 calls for "a
  freer exchange before judgement" after the main rounds and before the 6.8 verdict.
- **Outcome / pattern set:** TDD red-first (`tests/test_closing_discussion.py`, 5
  tests, watched fail on the missing `CLOSING_EXCHANGES` import). New
  `engine/closing.py`: `run_closing_discussion(setup, config, *, gatekeeper,
  run_id, runs_dir) -> list[DebateMessage]` runs `CLOSING_EXCHANGES` (a single
  named constant = 1) exchanges, each one closing statement per side (Pro then
  Con). The "freer" framing is a NON-adversarial per-turn prompt
  (`CLOSING_PROMPT_LINE`: "respond freely … strongest final case — stay on your
  side") injected as a plain `user` turn — instead of the main loop's strict
  `relay_opponent_turn` ("…«…». Rebut it."). It REUSES the existing turn pieces:
  `generate_turn_output` (so the model call still routes through the gatekeeper
  under the 6.4 timeout+retry wrapper — no bypass) → `enforce_word_limit` (config
  `max_words`) → `context.append_assistant`. Each closing turn logs a `message`
  event tagged `payload["closing"]=True` with the `CLOSING_ROUND` (0) marker
  (event_type stays within the LogEvent literal). Wired into `run_debate_loop`
  after the rounds; closing turns land in `closing_discussion` (kept separate from
  `transcript`) and feed `CostTotals.from_messages(transcript + closing)`. Updated
  two existing loop tests honestly to scope to non-closing messages / account for
  closing gatekeeper calls.
  *Pattern: to add a phase that "reuses a turn but with different framing", keep
  the gatekeeper-routed `generate_turn_output` + `enforce_word_limit` core and vary
  only the injected `user` prompt; tag the new phase in the log payload + reuse a
  documented round marker (0) rather than inventing a new `event_type`, and drive
  the count from one named constant — never an inline `2`.*

## 6.6 — Event streaming (`engine/stream.py` + LOG `_stream.py`)

- **Prompt:** "Make the engine yield/stream events as they happen so CLI/API/UI
  can render live. Events are ordered and typed."
- **Outcome / pattern set:** TDD red-first (`tests/test_event_stream.py`, watched
  fail on the missing `CollectingSink`/`stream_debate` imports). The streamed event
  IS the LOG event — ONE schema (`LogEvent`), already typed + JSON-serialisable for
  SSE. Rather than build events twice, the sink primitives live in the LOG package
  (`log/_stream.py`): `EventSink` (Protocol), `CollectingSink`, and `emit_event(
  sink, …)` — the single DRY chokepoint that calls `log_event` AND forwards the
  SAME validated record to an optional sink (`sink=None` ⇒ identical log-only
  behaviour, backward compatible). Every engine site that logged an event
  (`turn._record`, `drift`, `closing`, `_call_log`, agents `word_limit`) swapped
  its bare `log_event(...)` for `emit_event(sink, ...)`, and an optional
  `sink: EventSink | None` is threaded through `run_debate_loop` → turn/drift/
  closing/`generate_turn_output`. A thin GENERATOR `stream_debate(...)` sits on top:
  it runs the debate on a daemon thread whose sink `Queue.put`s each event, yields
  them live in order, then yields the final `DebateResult` (and re-raises a worker
  error). "Ordered + complete" is asserted by equality to the JSONL sequence
  (minus the gatekeeper's OWN infra `tool_call`/`retry`/`system` events, which come
  from its independently-bound run_id — an Epic 13 concern, not the debate stream).
  *Pattern: to add a live STREAM to a synchronous engine that already logs, don't
  invent a second event type — make ONE emit helper that logs + forwards the same
  validated record to an opt-in sink, thread the sink (default `None`) through the
  call tree so it stays backward compatible, and put the generator/thread wrapper
  on top of the sink rather than re-plumbing the engine.*

## 6.7 — Token/cost accounting (`engine/_usage.py` + `result.py`)

- **Prompt:** "Capture token usage per model call and aggregate into DebateResult
  (per agent, per round, totals). Feed the LOG package. This supports Epic 15 cost
  reporting."
- **Outcome / pattern set:** TDD red-first (`tests/test_token_accounting.py`,
  watched fail on the missing `UsageBreakdown` export). Confirmed the installed
  pydantic-ai API: `result.usage` is now a **property** (not a method) returning a
  `RunUsage` with `input_tokens`/`output_tokens`/`total_tokens`; `TestModel`
  reports deterministic, **non-zero** usage (≈51 in / 4 out per call), so tests
  assert real captured numbers — no `FunctionModel` stub needed. Per-call capture
  already existed in `turn._record`; this task (a) factored the defensive
  `getattr(output, "usage", …)` read into one `call_tokens(output)` helper reused
  by `turn` AND `closing` (closing previously dropped usage), and (b) added a small
  `UsageBreakdown` value + `usage_by_agent`/`usage_by_round` folds in a new
  `engine/_usage.py` (split, not compress — `result.py` was already near the
  150-line cap). `CostTotals.from_messages` now also fills `by_agent` /
  `by_round`; grand totals + both breakdowns re-sum to the same total. **Prices are
  deliberately left out** (`cost_usd` stays `0.0`): Epic 15's per-model price table
  (task 15.1) consumes this typed, JSON-serialisable shape. *Pattern: when the SDK
  result already exposes usage, capture it through ONE defensive reader at every
  call site, store raw tokens on the message + the LOG event's `tokens` field, and
  aggregate into typed per-slice breakdowns — leave pricing to the downstream epic
  so token capture has no hard-coded values.*

## 6.8 — Public SDK entrypoint (`engine/sdk.py`)

- **Prompt (verbatim):** see `.building_tasks_logs/6.8-sdk-entrypoint.json`.
- **Context:** the engine seams already existed — `setup_debate` (validate +
  prepare), `run_debate_loop` (rounds + closing → `DebateResult`), and
  `stream_debate` (threaded generator yielding events then the result). This task
  ties them into ONE ergonomic facade other packages (CLI/API/UI) drive.
- **Outcome / pattern set:** TDD red-first (`tests/test_debate_engine.py`, 7 tests,
  watched fail on the missing `DebateEngine` export). `DebateEngine(config).run(
  topic) -> DebateResult` is the blocking call; `.stream(topic)` is the streaming
  variant — yields each `LogEvent` live then the final `DebateResult` as the last
  item of one iterator (documented contract). Config-driven: `config=None` builds
  from `Settings` via `DebateConfig.from_settings`; the gatekeeper is injected or
  left `None` so the loop builds its own rate-limited default **bound to the run
  id** (the gatekeeper needs `run_id` at construction, so it can't be built in
  `__init__` before a run id exists — the facade holds only an *optional injected*
  keeper and defers the default to the loop). `run_id` defaults to `uuid4().hex`.
  **Subtlety:** `run()` logs the one `system` setup event for observability, but
  `stream()` skips it (`log_setup=False`) so the streamed sequence stays identical
  to the JSONL log — the setup event precedes the threaded worker and would
  otherwise not flow through the live sink. Canonical import is `from
  agent_debate.core import DebateEngine` (the SDK is the `agent_debate.core`
  namespace package — no top-level `agent_debate.__init__` shim; this is THE
  documented surface, matching the PRD's `from agent_debate import DebateEngine`
  intent). Re-exported alongside `__version__`, `DebateConfig`, `DebateResult`.
  *Pattern: a public facade owns the config + injectables and composes existing
  seams; when a dependency (gatekeeper) needs per-run state it can't hold at
  construction, defer its default to the seam that has that state — never bypass it.*

## 6.9 — Engine acceptance tests, mocked LLM (`tests/test_engine_acceptance.py`)

- **Prompt (verbatim):** see `.building_tasks_logs/6.9-engine-tests.json`.
- **Context:** the per-task Epic-6 suites already covered each unit at ~100%; this
  is the consolidation/acceptance pass (mirrors 1.5/2.5/3.6/4.6/5.8/7.5/13.7) that
  proves the orchestration sub-PRD §7 criteria compose as ONE story through the
  **public `DebateEngine` SDK** at the DEFAULT scale, mocked LLM, no network.
- **Outcome / pattern set:** TDD red-first demonstrated on the net-new assertion —
  a default-config `DebateEngine().run()` yields exactly `10 Pro + 10 Con`
  alternating turns (the wrong expectation `== 11` was watched fail, then restored
  to `10`). The four §7 behaviours: (1) the 10v10 default-scale debate + word
  limit + alternation through the SDK; (2) the adversarial relay (5.6) framing is
  asserted to reach the agent via a `FunctionModel` that records the prompt text it
  sees — sliced to the main rounds since the closing turns are (correctly)
  relay-free; (3) timeout→cancel→retry→success and (4) exhausted-retry→FAILED are
  driven through `run_debate_turn` with the **injectable `timeout_runner`/`sleep_fn`
  seams** (the SDK deliberately does not expose them), plus a full SDK debate that
  survives every turn timing out (`max_retries=0` so the loop never sleeps) via a
  `TimeoutGatekeeper`; (5) streamed events equal the JSONL log, in order.
  **Subtlety:** the public SDK has no sleep/timeout seam, so the timeout edges use
  the turn-level seams (honest: unit-level determinism, SDK-level composition) — NO
  real sleeps/threads/network. Files split to honour the 150-line cap
  (`_engine_acceptance_helpers.py` holds the `FunctionModel`/gatekeeper/`hang_n_times`
  fixtures). No source change needed — the engine already satisfied §7; this pass
  is pure acceptance composition. *Pattern: when the public surface hides a
  determinism seam, exercise the edge at the seam's own level and compose the happy
  path through the public API — don't widen the public API just to test it.*

## 8.2 — Nudge logic: private correction injected into the captured agent (`tests/test_nudge_logic.py`)

- **Prompt (verbatim):** see `.building_tasks_logs/8.2-nudge-logic.json`.
- **Context:** 8.1 deepened drift *detection* and `drift.py` already recorded +
  logged a nudge on capture, but the private correction was never actually
  **delivered** to the offending agent. 8.2 closes that loop: "private" must mean
  the correction lands in the captured agent's OWN context only.
- **Outcome / pattern set:** TDD red-first (5 tests, watched `ImportError:
  inject_nudge` fail, then green). New `engine/drift.py` helper
  `inject_nudge(context, correction)` appends the correction as a `user` turn into
  the captured agent's isolated `AgentContext`; `run_drift_check` gained an opt-in
  `context` param (default `None` = log-only, back-compat) that injects on capture
  before emitting the `nudge` event, and `loop.py` `_drift` passes
  `setup.contexts.for_side(side)` so the live loop injects into the right agent —
  never the opponent's context, never the public transcript. The correction text
  is a single deepened named constant (`NUDGE_CORRECTION_TEMPLATE`) naming the
  reason + assigned side. The nudge stays logged + streamed (6.6) and **not** a
  debate turn (`is_debate_turn=False`), so the 10-vs-10 invariant holds (existing
  loop/acceptance/controller tests stay green). *Pattern: deliver a side-channel
  correction through the recipient's isolated context, not the shared transcript —
  "private" is enforced by where it is injected, asserted by its absence from the
  opponent's history and the transcript.*

## 8.3 — Verdict: deepened render_verdict + engine wiring (`tests/test_verdict.py`)

- **Prompt (verbatim):** see `.building_tasks_logs/8.3-verdict.json`.
- **Context:** 4.4 shipped a BASELINE `render_verdict` (winner from a per-side
  score tally) and the engine left `DebateResult.verdict=None` as a seam. 8.3
  DEEPENS the verdict to the PRD §3.2 step-4 contract and WIRES it into the loop:
  the controller writes a summary, whether the agents converged/agreed, the
  result, and WHO WON with reasoning — judged on argumentation/rebuttal/engagement,
  explicitly NOT factual correctness (PRD §3: no fact-checking).
- **Outcome / pattern set:** TDD red-first (8 tests, watched 6 fail, then green).
  `Verdict` gained ADDITIVE fields `summary`, `converged`, `criteria_scores` (back-
  compat defaults, so existing usage validates). New `skills/_verdict_logic.py`
  (`score_debate` + `build_verdict`) scores each side on three NAMED criteria from
  transparent text signals — argumentation = per-turn base weight + any controller-
  supplied per-turn `score`; rebuttal/engagement = counts of NAMED marker phrases;
  winner = higher total, tie within `VERDICT_TIE_MARGIN`; `converged` = both sides
  show agreement/concession markers. ALL phrase sets / weights / margin / criteria
  labels / templates are named in `skills/_verdict_constants.py` (split out of
  `constants.py` to keep it under 150 lines). NO truth-checking anywhere — a
  test proves a factually-false but better-argued side still wins. The loop's new
  `_verdict` helper builds `TranscriptTurn`s from the main+closing transcript
  (failed markers excluded; all-failed → `None`), calls `render_verdict`, sets
  `DebateResult.verdict`, and logs/streams a `verdict` event via `emit_event` (6.6)
  under the neutral controller label. *Pattern: judge argument QUALITY from named,
  transparent transcript signals — never claim truth — so the verdict is
  deterministic, testable, and PRD-§3 compliant; deepen the output model additively
  so the baseline contract stays green.*

## 8.4 — Staged-drift test fixture (`tests/test_staged_drift.py`, anti-sycophancy §4, issue #63)

- **Prompt (verbatim):** "Add a test fixture that forces a debater to parrot/concede
  to the opponent and assert assess_drift flags it and nudge corrects it at least once."
- **Context:** §4 acceptance requires a STAGED drift fixture — force an agent to
  parrot/concede, then prove it is DETECTED and NUDGED back ≥1. The drift pipeline
  (assess_drift 8.1, nudge 8.2, engine `run_drift_check`/loop wiring) already existed,
  so this is a test-only task: a meaningful, non-trivial fixture that drives a REAL
  conceding message through the real engine/SDK drift path.
- **Outcome / pattern set:** No source change needed — staging drift surfaced no gap.
  New reusable `tests/_staged_drift_helpers.py`: `drifting_model(side, concede_round)`
  builds a `FunctionModel` whose `concede_round`-th turn deterministically emits a
  clearly-conceding line (sourced from `DRIFT_CONCEDE_PHRASES`, no literal dup) and is
  otherwise on-side; `staged_run()` drives a full debate through the public
  `DebateEngine` SDK with an injected `ApiGatekeeper` (Epic 13) + per-run JSONL sink.
  5 tests assert: `assess_drift` flags the concession (captured); the engine records
  ≥1 nudge in `DebateResult.nudges` AND logs a `nudge` event; the nudge is PRIVATE
  (10-vs-10 invariant holds, `is_debate_turn=False`, never leaks into the opponent's
  transcript); a NON-drifting control yields ZERO nudges (the red→green guard proving
  nudges come from the STAGED concession, not noise); the correction reaches the
  captured agent's OWN later prompt. *Pattern: stage drift deterministically via an
  injectable FunctionModel + a reusable helper, then assert detection/nudge end-to-end
  through the SDK; pair the staged assertion with an on-side control so the fixture's
  trigger is proven, not assumed.*

### Typer CLI app — `agent-debate run` (task 9.1, issue #64)
- **Prompt (verbatim):** "Build a Typer CLI with a run command taking a topic and
  options (--rounds, --max-words, --model, --search-backend). It drives the SDK
  (DebateEngine)."
- **Context:** Epic 9 opens the CLI surface (PRD §6: `agent-debate run "<topic>"
  [--rounds 10] [--max-words 150] [--model …]`). The Epic-6 SDK (`DebateEngine`,
  `DebateConfig.from_settings`, `Settings`/`get_settings`) was already the documented
  facade; 9.1 is the thin Typer shell over it (live streaming is 9.2, `--json` is 9.3).
- **Outcome / pattern set:** A `typer.Typer` app (`cli/app.py`) with a `run` command
  whose every option defaults to `None`; `_resolve_settings()` loads `get_settings()`
  and `model_copy(update=…)`s ONLY the flags the user passed, then
  `DebateConfig.from_settings()` derives the run config — so **config, not the CLI,
  owns the defaults** (no hard-coded magic). `--model` sets `debater_model` (resolving
  both sides via the Settings fallback); `--search-backend` flows to the engine via
  `settings=`; rendering split into `_render.py` to keep files <150 lines. Tests drive
  the app with `typer.testing.CliRunner` + a recording stub engine so **no network/API
  key** is touched (the SDK already routes real calls through the Epic-13 gatekeeper).
  *Gotcha worth remembering: re-exporting the Typer app as `app` from the package
  `__init__` shadows the `cli.app` submodule (breaks monkeypatching in the full suite)
  — re-export it under a different name (`cli_app`). Console entry point registered as
  `[project.scripts] agent-debate = agent_debate.cli.app:app`.*

### Rich LIVE transcript rendering (task 9.2, issue #65)
- **Prompt (verbatim):** "Use Rich to render the live transcript: Pro and Con
  messages per round with inline controller nudges, and the final verdict."
- **Context:** Epic 9 continues the CLI surface (PRD §6). 9.1 was a blocking
  `DebateEngine.run()` + plain-text `render_result`; 9.2 switches the default human
  view to render the transcript LIVE as events arrive, consuming `DebateEngine.stream`
  (ordered typed `LogEvent`s, then the final `DebateResult` as the last item, 6.6/6.8).
- **Outcome / pattern set:** A Rich renderer split across three files (each <150 lines):
  `_live.py` (`render_stream(topic, events)` — prints a topic header then iterates the
  stream, rendering EACH event the instant it arrives and capturing the final
  `DebateResult`), `_live_events.py` (a dispatch table on `event_type` → per-kind
  handlers; `message` → side-coloured `Panel`, `nudge` → distinct dim/italic inline
  `moderator nudge` marker, `verdict` → final `Panel`; unsurfaced kinds like
  `tool_call`/`retry` silently ignored), and `_live_style.py` (every label/colour/style
  a NAMED constant — Pro=green, Con=red — so no hard-coded values; Rich terminal output,
  so the global RTL/CSS rules don't apply). Wired into `run` as the default (`--json` is
  separate, 9.3). Tests drive it with `CliRunner` + a stub engine yielding a CANNED
  sequence (Pro msg, Con msg, nudge, verdict, result) so **no network/key** — asserting
  Pro/Con distinguished, the nudge inline (ordered after the turns), the verdict last.

### `--json` machine output + non-zero exit on failure (task 9.3, issue #66)
- **Prompt (verbatim):** "Add --json to print the DebateResult as JSON; exit
  non-zero on failure."
- **Context:** Epic 9 finishes the CLI surface (PRD §6). 9.2 made the default human
  view a Rich LIVE transcript; 9.3 adds a `--json` flag that emits the final
  `DebateResult` as a single machine-readable JSON blob for piping/parsing, and makes
  the command exit non-zero on any debate failure.
- **Outcome / pattern set:** New `cli/_json.py` (split out of `app.py` to stay <150
  lines): `emit_json(result)` writes `DebateResult.model_dump_json()` (the canonical
  serialisation — transcript/nudges/closing/verdict/totals) as ONE line; a generic
  `run_or_fail(produce, *, log)` wrapper that runs a callable and, on a known debate
  failure (`MissingApiKeyError`/`InvalidInputError`/`TurnFailedError`) OR any other
  engine error, logs `cli_run_failed` via the LOG package, prints `Error: …` to
  **stderr**, and raises `typer.Exit(code=EXIT_FAILURE)` (a NAMED constant, no magic
  number); and a `clean_stdout()` context manager that diverts `sys.stdout` → `sys.stderr`
  for the duration of the `--json` engine run so the LOG package's console sink (which
  prints to stdout, PRD §5.8) never pollutes the JSON — stdout carries ONLY the blob.
  `run` gained `--json` and is split into `_run_json` (blocking `engine.run` under
  `clean_stdout`, then `emit_json`) / `_run_human` (LIVE `render_stream`); BOTH paths go
  through `run_or_fail` so failure semantics are identical. Tests (`test_cli_json.py`)
  use `CliRunner` + stub engines (blocking/failing/crashing) so **no network/key** —
  asserting `--json` stdout parses to the DebateResult shape (topic/transcript/verdict),
  a failing or crashing engine exits non-zero with the error on stderr, and the human
  path also exits non-zero on failure.

### CLI acceptance/consolidation tests (task 9.4, issue #67)
- **Prompt:** "Write tests running the CLI against a mocked engine, asserting transcript
  + verdict are printed and exit codes are correct."
- **Context:** Epic-9 acceptance pass (mirrors prior epics' `*_acceptance` modules). The
  per-task suites (9.1 `test_cli_run.py` / 9.2 `test_cli_live.py` / 9.3 `test_cli_json.py`)
  already cover each behaviour and the CLI is ~99% covered; the value here is the
  integrated acceptance composition, not net-new coverage.
- **Outcome / pattern set:** New `packages/cli/tests/test_cli_acceptance.py` driving the
  Typer app via `CliRunner` against MOCKED engines (stubs in a split
  `_acceptance_helpers.py` to stay <150 code lines), NO network/key. It asserts the
  headline Epic-9 story END-TO-END: `run "<topic>"` prints the full transcript (Pro **and**
  Con messages) **and** the verdict in render order (the human/live path); `--json` prints
  a parseable `DebateResult` blob; exit codes are correct (0 on success, non-zero on
  failure for **both** the human and `--json` paths, with `--json` keeping stdout clean of
  partial JSON); the `--rounds`/`--max-words`/`--model`/`--search-backend` flags reach the
  engine config (read from a frozen `Settings`, no hard-coded numbers); and `--help` lists
  the `run` command + every option. TDD red-first demonstrated on the net-new integrated
  transcript assertion (dropping the streamed Con message turns it red, then restored).
  Test-only change — no source fix needed; the CLI was already a thin, correct driver.

### FastAPI app skeleton (task 10.1, issue #68)
- **Prompt:** "Create a FastAPI app with a Uvicorn entrypoint in packages/api, wired to the
  SDK." (full standards prompt: TDD, 150-line cap, ruff/mypy clean, no hard-coded values,
  gatekeeper for external calls, LOG package, coverage ≥85%).
- **Context:** Epic-10 kickoff — the API package was a bare version-re-export shell. This
  task lays the FastAPI foundation the debate endpoints (10.2), SSE (10.3) and
  CORS/validation (10.4) build on, without adding any real endpoints/network yet.
- **Outcome / pattern set:** Added `fastapi`/`uvicorn`/`httpx` to `packages/api` and
  relocked. New `app.py` with a `create_app()` **factory** (reusable, config-driven —
  loads `Settings` via `get_settings()` onto `app.state` for later routes) plus a
  module-level `app = create_app()` for Uvicorn; skeleton routes `GET /health` →
  `{"status":"ok","version":__version__}` and `GET /` → service info. `config.py` resolves
  host/port from `API_HOST`/`API_PORT` env with single named-constant defaults
  (`DEFAULT_API_HOST`/`DEFAULT_API_PORT`) — no scattered magic. `__main__.py` exposes
  `run_server()`/`main()` (the `agent-debate-api` console script + `python -m
  agent_debate.api`) calling `uvicorn.run`. LOG package used at app/server startup; the SDK
  already routes every external call through the Epic-13 gatekeeper, so the API adds no new
  edges. TDD red-first via `fastapi.testclient.TestClient` (no port bind, no network):
  factory returns a `FastAPI` and is reusable; `/health`/`/` return the version; the
  entrypoint resolves env/default host-port and invokes a patched `uvicorn.run`. 100%
  coverage on the api package.

### Debate endpoints — `POST /debates` + `GET /debates/{id}` (task 10.2, issue #69)
- **Prompt (verbatim):** see `.building_tasks_logs/10.2-debate-endpoints.json`.
- **Context:** Builds on the 10.1 FastAPI skeleton: adds the first real endpoints over the
  SDK. The challenge is testability — a full debate is long-running and makes model calls,
  but tests must be fast with NO network/key.
- **Outcome / pattern set:** Split into four small modules (all ≤150 code lines).
  `debate_store.py` — a thread-safe in-memory `DebateStore` (run_id → `DebateRecord`) +
  a `DebateStatus` `StrEnum` (`running`/`done`/`failed`) so status strings are a single
  source of truth, not inline magic; storage is in-memory only (durable persistence out of
  scope). `debate_runner.py` — the **injectable seam**: a `DebateRunner` Protocol
  `(topic, overrides) -> DebateResult`; `default_runner` drives `DebateEngine` (every model
  call routes through the Epic-13 gatekeeper inside the engine) applying overrides to
  `Settings.model_copy`; `set_debate_runner(app, ...)`/`get_debate_runner(app)` store/read
  it on `app.state` so **tests substitute a stub** returning a canned `DebateResult`
  instantly. `debate_models.py` — `DebateRequest` (topic reuses the 7.2 `validate_topic`
  field validator → oversized/empty/control-char topics become a clean 422; optional
  `rounds`/`max_words`/`model`/`search_backend` overrides) + `DebateStarted`/`DebateState`
  responses. `debate_routes.py` — `POST /debates` validates, mints a uuid4 `run_id`,
  registers a `running` record, schedules the run on `BackgroundTasks`, returns
  `{run_id,status}` (201); the worker flips the record to `done`/`failed` and never crashes;
  `GET /debates/{id}` returns status + result (or 404). Wired into `create_app()` (per-app
  store on `app.state`, router included). TDD red-first via `TestClient` + the injected
  stub: POST returns a non-empty run_id; GET returns status and the result when done; unknown
  id → 404; oversized/empty/missing topic → 4xx; overrides reach the runner; a raising runner
  → `failed`. 100% coverage on the new endpoint code.

### SSE stream endpoint — `GET /debates/{id}/stream` (task 10.3, issue #70)
- **Prompt (verbatim):** see `.building_tasks_logs/10.3-sse-stream.json`.
- **Context:** Builds on 10.2: stream a debate's ordered, typed events to live consumers as
  Server-Sent Events. The run executes on a background worker, so the challenge is the
  worker→consumer hand-off, plus testing live streaming with NO network.
- **Outcome / pattern set:** Three small new modules (all ≤150 code lines). `event_buffer.py`
  — a thread-safe, append-only `EventBuffer` per run (one `threading.Condition`): the worker
  `publish()`-es each event, each SSE consumer `stream()`-s from index 0 (blocking for live
  events, terminating on `close()`). Append-only ⇒ the **same code path** serves a live tail
  and a faithful **replay** of a finished run; each consumer keeps its own cursor so nothing
  is dropped/double-counted. `sse.py` — the dependency-free wire format: named constants
  (`SSE_MEDIA_TYPE = "text/event-stream"`, the field labels, the `done` sentinel — no inline
  magic) + `format_log_event` (SSE `event:` = the event's `event_type`, `data:` = its JSON).
  `stream_runner.py` — a streaming seam `(topic, overrides, publish, run_id) -> DebateResult`;
  `default_stream_runner` drives `DebateEngine.stream` (model calls still through the Epic-13
  gatekeeper), forwarding each `LogEvent` to `publish` and keeping the final `DebateResult`;
  `get_stream_runner` resolves an injected streaming stub first, else **adapts** a 10.2 plain
  `DebateRunner` (backward compatible), else the default. The `DebateRecord` gained an
  `events: EventBuffer`; the 10.2 worker now drives the streaming runner and `mark_done`/
  `mark_failed` `close()` the buffer so attached streams terminate. The route is a plain
  `StreamingResponse(media_type=SSE_MEDIA_TYPE)` yielding each event then a `done` sentinel;
  unknown id → 404. TDD red-first via `TestClient` (it buffers the full body) + a stub runner
  publishing canned events: the SSE body parses to ordered, typed records ending in `done`;
  unknown id → 404; a finished run replays. No network in any test. 98–100% coverage on the
  new modules.

### 2026-05-31 — Task 10.4: Validation, errors, CORS (#71)

- **Prompt (verbatim):** "Add request validation, consistent error responses, and CORS
  configured for the UI origin." (+ repo standards: TDD, ≤150 code lines/file, ruff 0 + mypy
  clean, no hard-coded values, gatekeeper, LOG, coverage ≥85%).
- **Context:** Hardening the FastAPI surface (10.1–10.3). The endpoints already validated the
  topic (7.2 + Pydantic) and 404'd unknown ids, but errors used FastAPI's default ad-hoc
  shapes and there was no CORS — the UI (a separate browser origin) could not call the API.
- **Outcome / pattern set:** One consistent error envelope —
  `{"error": {"type": <machine label>, "message": <safe human text>, "detail": <extra|null>}}`
  — with `type` a `StrEnum` (`ErrorType`, single source of truth) and `ERROR_KEY` named, no
  inline magic. New `errors.py` registers handlers (most→least specific) via
  `app.add_exception_handler` in `create_app`: `RequestValidationError`→422 (field errors made
  JSON-safe with `jsonable_encoder` so a raw `InvalidInputError` in a rule's `ctx` serialises),
  the 7.2 `InvalidInputError`→422, `MissingApiKeyError`→**503 with a fixed safe message that
  never echoes the key**, `HTTPException`→re-wrapped (404 vs internal), and a catch-all
  `Exception`→**500 with a fixed message + the real fault logged via LOG, never a stack
  trace/secret in the body**. CORS: `config.py` gained `resolve_cors_origins()` reading
  `CORS_ORIGINS` (comma-separated) with a named `DEFAULT_UI_ORIGIN = http://localhost:5173`
  default — config-driven, never a wildcard; `create_app` wires `CORSMiddleware` for those
  origins + the GET/POST/OPTIONS the JSON+SSE endpoints need. Key design call: the background
  worker swallows exceptions (must not crash), so a *pre-run* misconfiguration like a missing
  key can't reach the client that way — added a synchronous `preflight.py` seam the `POST`
  route runs *before* scheduling; `default_preflight` validates provider keys (2.3),
  injected-runner apps get a no-op (their stub owns preconditions), tests inject a raising
  stub. TDD red-first via `TestClient` (error envelope shape, CORS allow-origin for the
  configured origin and *not* a disallowed one, config-driven override, key-not-leaked). 100%
  coverage on the new modules; all existing api tests kept green.

- **Task 11.1 — UI topic-input page (#73).** Prompt: *"Build a web page with a topic
  input that starts a debate via the API. Keep it simple and clean."* Stack call: keep the
  UI inside the Python package as a small FastAPI app (mirroring the API's `create_app`
  factory + Uvicorn entrypoint) that **serves a static frontend** (HTML/CSS/JS) — so the
  serving routes are pytest-testable via `TestClient` with no network, while the
  browser-side `fetch` to `POST /debates` stays out of the test path. Key design call: the
  **API base URL is config-driven, never hard-coded** — `config.py` adds
  `resolve_api_base_url()` (`API_BASE_URL` env → named `DEFAULT_API_BASE_URL`), and the app
  surfaces it *two* ways: injected into the served HTML via an `__API_BASE_URL__`
  placeholder swap (zero extra round-trips for the page) **and** exposed at `GET /config`
  (JSON, for tests + programmatic readers). Host/port likewise from `UI_HOST`/`UI_PORT` or
  named defaults. CSS uses **logical properties only** (`margin/padding-inline`,
  `inset-inline`, `text-align: start`) for RTL-readiness (task 11.5 hardens further);
  semantic, labelled, `aria-live` result. TDD red-first via `TestClient`: `GET /` → 200
  HTML with the topic input + start control, the injected base URL matches an env override,
  `/config` returns it (+ named-default fallback), static assets reachable, factory
  reusable. 100% coverage on the new Python modules; all existing tests kept green.

- **Task 11.2 — Live streaming transcript (#74).** Prompt: *"Consume GET
  /debates/{id}/stream and render the Pro vs Con transcript live as it streams."* Stack
  call: the live render is browser JS (`EventSource` over the API's SSE endpoint), so — as
  with 11.1 — it's **tested at the serving level**, not in a real browser. `app.js` opens
  `new EventSource(${apiBaseUrl()}/debates/{id}/stream)` (reusing 11.1's config-driven
  `apiBaseUrl()`, so the origin is **never hard-coded**), listens for `message` events,
  `JSON.parse`s each `LogEvent`, routes it into a Pro or Con column by `event.agent`
  (matching the engine's `DebateSide` `"pro"`/`"con"` values) and appends a turn in arrival
  order (live); it **closes on the `done` sentinel** (and on `error`). `index.html` gains a
  two-column `#transcript` region; `style.css` gives Pro vs Con distinct palettes
  (`--pro`/`--con`) using **logical properties only** (`border-inline-start`,
  `padding-inline`, `text-align: start`) for RTL-readiness. TDD red-first via `TestClient`:
  the served `app.js` wires `EventSource` + the `/debates/{id}/stream` path + the
  config-driven base URL + `message`/`done` dispatch + Pro/Con render; the page has the
  transcript container; the CSS distinguishes the two sides and uses no physical
  left/right. Honest scope: browser behaviour itself is the UI smoke test (11.8); dedicated
  nudge/system + verdict panels are 11.3/11.4.

- **Task 11.3 — Separate panels (#75).** Prompt: *"Lay out three separate panels (don't
  overload one view): debate transcript, controller actions/nudges, and system log."*
  Building on 11.2's serving-level approach: the SSE `event` name **is** the
  `LogEvent.event_type`, so `app.js` routes each event to its panel by type — `message` →
  the Pro/Con **debate transcript**, `nudge` → the **controller actions/nudges** panel
  (the moderator's private corrections, kept OUT of the transcript), and the technical
  events (`system`/`tool_call`/`timeout`/`retry`, declared once as `SYSTEM_EVENT_TYPES`) →
  the **system log** panel. `index.html` gains a `#panels` grid wrapping three distinct,
  labelled `<section>`s (`#transcript`, `#controller-panel`, `#system-log`), each with its
  own list (`#controller-actions`, `#system-log-list`); the transcript keeps its two
  Pro/Con columns. `style.css` lays them out with a responsive `grid-template-areas`
  (transcript wide on top, controller + system below) using **logical properties only**
  (no left/right) for RTL-safety. `verdict` is intentionally left to 11.4. TDD red-first
  via `TestClient`: the served HTML has three labelled panel containers + their lists; the
  served `app.js` wires the per-type routing (`appendMessage`/`appendControllerAction`/
  `appendSystemEvent`); the CSS styles each panel distinctly and uses no physical
  left/right. Honest scope: browser behaviour itself is the UI smoke test (11.8).

- **Task 11.4 — Verdict view (#76).** Prompt: *"Add a verdict view showing the summary,
  whether agents agreed, who won, and token/cost totals."* Continuing the serving-level
  approach: the SSE stream ends with a `verdict` event then a `done` sentinel. Rather than
  accumulate streamed token deltas, the cleanest source is the **final `DebateResult`**
  (`verdict` + `totals` together), so on `done` `app.js` GETs `/debates/{id}` (the result
  endpoint, no `/stream` suffix, via a new `resultUrl()` built from the same config-driven
  `apiBaseUrl()`) and `renderVerdict()` fills a **distinct** `#verdict` `<section>`: who won
  (`verdict.winner` mapped to **Pro / Con / Tie** via `WINNER_LABELS`), whether the agents
  **converged/agreed** (`verdict.converged`), the **summary** (`verdict.summary`, falling
  back to `rationale`), and **token totals** (`totals.total_tokens`/`input_tokens`/
  `output_tokens` — cost is Epic 15, so tokens are surfaced now). The view starts `hidden`,
  is re-hidden when a new debate starts, and stays hidden on fetch/parse failure. `style.css`
  styles `.verdict` with **logical properties only** (no left/right) for RTL-safety. TDD
  red-first via `TestClient`: the served HTML exposes the `#verdict` region + outcome
  containers (`#verdict-winner/summary/converged/tokens`); `app.js` fetches the result on
  `done` and references the winner/summary/converged/`total_tokens` fields; the CSS is
  RTL-safe. Browser behaviour itself is the UI smoke test (11.8).

- **Task 11.5 — RTL-safe styling (#77).** Prompt: *"Style the UI using CSS logical
  properties (text-start/end, ps-/pe-, ms-/me-, items-start/end) for RTL support; never
  left/right."* This was the dedicated RTL audit/hardening pass over the UI built in
  11.1–11.4. The audit found the CSS **already clean** — 11.1–11.4 had used logical
  properties throughout (`text-align: start`, `margin/padding-inline`, `border-inline-
  start`, `inset`-free, `min-block-size`), no physical `left/right` declarations. The real
  gap was RTL *capability*: `<html>` carried only `lang="en"`, no `dir`. Decision: add an
  explicit `dir="ltr"` on `<html>` (default LTR, but the document is now genuinely RTL-
  switchable — flipping to `dir="rtl"` mirrors the whole layout because every directional
  rule is logical). The durable deliverable is `test_ui_rtl.py`: it serves `style.css` +
  `index.html` and **asserts no physical-direction property declarations** (`margin/padding-
  left/right`, bare `left:/right:`, `border-left/right`, `text-align: left/right`, `float/
  clear: left/right`) using boundary-anchored regexes (so logical names like `margin-inline-
  start` and the word "right" inside values/content never false-match), AND asserts logical
  props are positively present + `<html>` carries `dir`. Red→green proven honestly: with the
  CSS already clean, the physical-prop tests passed and only the `dir` test was red; planting
  `margin-left`/`text-align: right` made the enforcement test fail as designed. The test now
  fails the build for any future CSS that reintroduces physical direction.

### 11.6 — Nielsen heuristics (issue #78)

Prompt: *"Apply Nielsen's heuristics: visible system status (round/streaming
indicator), error prevention/recovery, consistency, minimalist design,
recognition over recall."* A usability hardening pass over the UI built in
11.1–11.5, turning Nielsen's 10 heuristics into concrete, serving-level testable
affordances. Implemented: (#1 visibility of system status) an honest status line
— `Connecting… / Debating — round N / Complete / Error` — driven by a single
`setStatus(state, round)` source of truth, with a pulsing "live" dot
(`prefers-reduced-motion` aware) toggled while connecting/debating; round is
tracked from `message` events. (#5 error prevention) Start stays disabled until
the topic is non-empty (`input` listener + initial sync) and the empty-topic
guard returns before the POST. (#9 error recovery) network/non-2xx/SSE-drop
failures show a friendly `"Something went wrong. Please try again."` message and
an error status — never a raw stack; the SSE `error` handler distinguishes a
clean `done` from a real drop. (#3 user control & freedom) a `New debate`
secondary button (`resetDebate()`) clears panels/verdict/status so the user is
never trapped. (#10 help) a minimalist help/about line above the form. (#2/#4/#6
consistency & recognition) consistent Pro/Con/**Moderator**/Verdict terminology
(controller panel renamed to "Moderator actions / nudges"). All new CSS is
RTL-safe logical-properties-only, keeping `test_ui_rtl.py` green. Durable
deliverable: `test_ui_usability.py` asserts each affordance at the serving level.
TDD red→green: 9 of 11 tests failed first, then the HTML/JS/CSS changes made
them pass.

### 11.8 — UI smoke test (issue #80)

Prompt: *"Add a smoke test or capture a screenshot of a completed debate for the
docs/submission."* A real browser render (Playwright/Selenium) is neither
available nor appropriate in headless CI, so the deliverable is an honest
end-to-end smoke proof at the serving/integration level, in three parts:
(1) **UI shell** — `TestClient(create_app())` asserts `GET /` returns the full
page a user sees (topic input + the three panels + verdict region + status
indicator); (2) **API completed-debate contract** — the API app, driven by a
stub *streaming* runner installed via the 10.3 `set_stream_runner` seam (no
network, no key) that returns a canned completed `DebateResult` (Pro/Con
transcript + a full verdict with winner/summary/converged + token totals),
satisfies the exact surface the UI calls: `POST /debates` → `run_id`;
`GET /debates/{id}` → done + verdict + totals; `GET /debates/{id}/stream` →
ordered SSE ending with the `done` sentinel; (3) **UI↔API cross-check** — the
served `app.js` references those exact paths and verdict fields
(`winner`/`converged`/`summary` + token totals) and those fields exist in the
API's completed-debate response, so client and server line up. Split a
`smoke_helpers.py` (rich completed result + canned events + SSE parser) to keep
the test file under the 150-line cap. Optional artifact: a small committed
`docs/ui-completed-debate.html` snapshot — the served shell with the verdict
region pre-filled from the same canned result, as "what a completed debate looks
like" for the submission (not a live render). TDD red→green demonstrated by
breaking the verdict contract (drop `summary`/`converged`) → the contract test
fails → restore → green.

### Cost-breakdown table (task 15.2, 2026-05-31)
- **Prompt:** "Generate a cost-breakdown table per run and aggregate: input/output
  tokens × price → total, per model and overall (guideline §11). Surface in the
  result and docs."
- **Context:** 6.7 captured per-turn tokens (by side); 15.1 shipped the config-driven
  per-model price table + `compute_cost`. This task turned tokens into money.
- **Outcome/pattern:** Added `CostBreakdown` / `ModelCostRow` value objects +
  `cost_breakdown_from_result` (maps each turn's side → its configured model via
  `config.pro_model`/`con_model`, sums tokens per model, prices via the table),
  `format_cost_table` (markdown), and `aggregate_costs` (sum many runs). The engine
  loop now prices the completed run: `DebateResult.cost_breakdown` + a non-zero
  `totals.cost_usd`, with an optional `price_table` injection for tests. Set the
  convention that runtime cost is priced at finalisation from config — no hard-coded
  prices — and that the loop is split (`_cost.py`, `_verdict.py`) to hold the 150-line
  cap.

### Budget cap + over-budget alert (task 15.3, 2026-05-31)
- **Prompt:** "Add a configurable budget cap and an over-budget alert (during/after
  a run). Document how cost scales with rounds × word-limit."
- **Context:** 15.1 shipped the config-driven per-model price table; 15.2 priced a
  completed run into `DebateResult.cost_breakdown` + `totals.cost_usd`. This task
  made that cost *actionable* — a cap + an alert when a run blows it.
- **Outcome/pattern:** Added a `BUDGET_USD` config knob (PRD §7 → `Settings` →
  `DebateConfig.budget_usd`, default `0` = **unlimited** so existing runs are
  unchanged). Split the logic the same way as 15.2's cost code: a *pure* decision
  surface — `BudgetStatus` + `check_budget(spent_usd, budget_usd)` in
  `pricing/budget.py` — and an I/O side next door, `alert_over_budget(...)` in
  `pricing/_alert.py`, which logs ONE structured `system` event (`payload.budget_alert`
  + spent/cap/remaining) via the LOG package only on a genuine overrun. The engine
  wiring (`engine/_budget.py`) runs right after `price_result` in the loop. Documented
  cost-vs-scale in PRD §10: output ≈ linear in `ROUNDS × MAX_WORDS`, input faster
  (replayed context grows with `ROUNDS`). Also set the convention that a long
  re-export `__init__.py` collapses to the existing `*pkg.__all__` star-import shim
  (matching `skills`/`_engine_public`) to hold the 150-line cap rather than trimming
  the public surface.

### Acceptance-criteria tests (task 12.1, 2026-05-31)
- **Prompt:** "Write/aggregate tests covering each PRD §11 acceptance criterion.
  Ensure coverage on the engine and both gatekeepers keeps total >=85%."
- **Context:** Every epic already shipped its own per-task + consolidated
  acceptance suite (1.5 / 2.5 / … / 13.7). PRD §11 is the lecturer-facing
  ~15-bullet checklist, but nothing mapped each bullet to a single, named,
  greppable test — so "is §11 box N covered?" had no one answer.
- **Outcome/pattern:** Added a consolidated §11 acceptance pass —
  `packages/core/tests/test_acceptance_criteria.py` (behavioural bullets 1-7, 9,
  end-to-end through `DebateEngine` + both gatekeepers) and
  `test_acceptance_criteria_meta.py` (surfaces + hygiene/meta bullets 8, 10-15),
  split with `_acceptance_criteria_helpers.py` to hold the 150-line cap. Every
  test is named `test_cN_*` and the module docstring carries the explicit
  criterion→test map, so the §11 checklist is provably green at a glance. Set the
  convention to **aggregate, not duplicate**: reuse the existing offline helpers
  (`_engine_acceptance_helpers`, `_staged_drift_helpers`, `_gatekeeper_acceptance_helpers`,
  `_skills_acceptance_helpers`) and the scripted gates (`secret_scan`,
  `check_line_limit`) rather than re-implementing them. Hygiene bullets that
  depend on the *local* `.env` (secret-scan over the real tree) are verified via a
  synthetic-tree mechanism check + a `.gitignore` assertion, so the suite stays
  green in CI without coupling to a developer's local key file. Coverage held at
  99.7% (>=85%).

### Per-package + root READMEs (task 12.2, 2026-05-31)
- **Prompt:** "Write a README per package and ensure the root README quickstart
  covers SDK, CLI, API, UI, LOG."
- **Context:** The root README still carried an Epic-0 "scaffolding" status note
  and marked CLI/SDK/API/UI runs **(planned)** — stale now that Epics 6/9/10/11
  shipped the real `DebateEngine`, the `agent-debate` Typer command, the
  `/debates` FastAPI routes, and the `agent-debate-ui` app. No package had its
  own README.
- **Outcome/pattern:** Added a `README.md` per package, each documenting that
  surface for a new developer against the ACTUAL code — `core` (the `DebateEngine`
  facade + `DebateConfig`/`DebateResult`/`Settings`/`ApiGatekeeper` surface from
  `__init__.__all__`), `cli` (the real `run` command + `--rounds/--max-words/
  --model/--search-backend/--json` options), `api` (the real `POST /debates`,
  `GET /debates/{id}`, `GET /debates/{id}/stream` routes + the `agent-debate-api`
  entrypoint), `ui` (`GET /` `/config` `/static`, the `agent-debate-ui` script,
  config-driven `API_BASE_URL`), and `log` (`get_logger`/`log_event`/`configure`/
  redaction). Updated the root README status note + Quickstart to be truthful
  (all five surfaces runnable, dropped the `(planned)` claims and the non-existent
  `DebateEngine.from_env()` — `DebateEngine()` already derives config from
  `Settings`), and cross-linked every README to its siblings + `docs/`. Kept the
  existing `tests/test_readme.py` contract green (System requirements / Install /
  Quickstart / Troubleshooting / `docs/` links). Docs-only — no Python added.
  *Pattern: README examples must be copy-pasted from the real entrypoints/`__all__`,
  never invented; correct stale status truthfully rather than aspirationally.*

### Architecture/decisions doc (task 12.4, 2026-05-31)
- **Prompt:** "Write an architecture/decisions doc (or expand PRD §5) explaining
  the system, packages, and key decisions for a new team member."
- **Context:** PRD §5 + the four sub-PRDs + the per-package READMEs (12.2) each
  cover a slice, but a newcomer had no single map tying them together — and no
  consolidated record of *why* the key designs are the way they are.
- **Outcome/pattern:** Added a dedicated `docs/ARCHITECTURE.md` (cleaner than
  bloating the PRD): system overview + the three-agent model and an ASCII
  orchestration diagram; the five packages with responsibilities + the one-way
  dependency graph (core = heart, LOG = shared leaf, CLI/API/UI = thin shells);
  a code map ("where to look"); the key mechanisms (anti-sycophancy, both
  gatekeepers, pluggable search, timeout/retry, logging, cost/budget) each
  pointing at the REAL modules/classes; and an **ADR-style decisions table**
  (decision → why → trade-off, D1–D12). Cross-linked from PRD §5 and the root
  README Documentation table; summarises-and-links the deeper docs rather than
  duplicating them. *Pattern: every module/class name cited was verified against
  the actual tree (e.g. `engine/loop.py::run_debate_loop`,
  `gatekeeper/_gatekeeper.py::ApiGatekeeper`, `search/registry.py`,
  `security/sanitiser.py`) so the doc cannot drift from reality.*

### Docstrings & comments (task 12.4a, 2026-05-31)
- **Prompt:** "Add docstrings to all public modules/classes/functions and
  meaningful comments where logic is non-obvious. Optionally enforce with ruff
  pydocstyle rules."
- **Context:** PRD §3.3 mandates documented public APIs + comments on non-obvious
  logic. The tree's docstring coverage was already near-complete (88 of ~108
  source files used Google-style `Args:`/`Returns:`/`Raises:` sections), so the
  job was to *standardise + enforce* rather than rewrite working code.
- **Outcome/pattern:** Turned the guideline into a **machine-enforced gate** by
  enabling ruff's pydocstyle family (`select += ["D"]`) with
  `convention = "google"` to match the existing style, plus a `"**/tests/**"`
  per-file ignore (tests document themselves through names + assertions, and
  §3.3 targets the public surface). Ruff then surfaced exactly 11 real gaps:
  7 undocumented `__init__` (D107), 3 docstrings with backslashes needing the
  `r"""` prefix (D301), and 1 function missing two arg descriptions (D417). All
  fixed with concise one-line docstrings / argument entries — no behaviour
  change, no new comments that merely restate code. *Pattern: line-limit check
  counts CODE lines only (tokenize excludes docstring/comment lines), so adding
  docstrings can never push a file over the 150-line guideline.*

### ISO/IEC 25010 mapping (task 12.4b, 2026-05-31)
- **Prompt:** "Add a short table mapping the system to ISO/IEC 25010
  characteristics: functional suitability, reliability, performance efficiency,
  security, maintainability, portability — with how each is addressed."
- **Context:** PRD §8/§13 mandate (guideline §13) that the system be mapped to
  the ISO/IEC 25010 product-quality characteristics, but only a one-line
  *reference* existed — no actual mapping. The quality docs already live in
  `ARCHITECTURE.md` (§7 quality standards, §6 decisions), so the mapping belongs
  there rather than in a separate file.
- **Outcome/pattern:** Added `ARCHITECTURE.md` **§8 "ISO/IEC 25010
  product-quality mapping"** — a table covering all **eight** characteristics
  (the six named in the prompt plus **compatibility** and **usability**). Each
  row names the characteristic and *how the system concretely addresses it*,
  citing the REAL mechanism/module already documented in §3–§5: async +
  `concurrent_max` (performance), timeout/retry + the FIFO overflow queue that
  never drops (reliability), both gatekeepers + sanitiser + log redaction + no
  secrets (security), the 150-line/ruff/mypy/≥85%-coverage/TDD gates
  (maintainability), pydantic-ai + pluggable `SearchProvider` + `uv` workspace
  (portability), and Nielsen heuristics + RTL (usability). Cross-linked from
  PRD §8/§13. *Pattern: a quality-attribute mapping is only credible if every
  cell points at a verified, already-shipped mechanism — so each claim reuses a
  module/test name confirmed against the tree, never an aspiration.*

### Sample debate runs committed for the teacher (task 12.5, 2026-05-31)
> **Update (2026-06-01):** the three reduced-round sample debates described
> below (`policy-congestion-pricing`, `techethics-ai-art`,
> `lifestyle-morning-routine`) were later **removed** from the repo; only the
> full 10-round `capitalism` run is now committed. The narrative below is kept
> as the build-audit record of how the task was originally done. References to
> "n = 4" / the three topics reflect that earlier state, not the current repo.
- **Prompt:** "Run several debates on varied topics and commit each run under
  `runs/` as `<run_id>.jsonl` plus a readable `<run_id>.md` (transcript, verdict,
  token/cost). This is the evidence the teacher reviews."
- **Context:** PRD §11's final acceptance bullet wants *real* committed runs the
  teacher can read. The LOG package already writes the machine `runs/<run_id>.jsonl`
  event log, and Epic 15 already renders a cost table (`format_cost_table`), but **no
  `.md` exporter existed** (grepped `packages/` for markdown/render/export). These
  are REAL Anthropic API calls (real money), so cost control was a first-class
  constraint.
- **Topics chosen (one per kind, for variety):** a **policy** question — *"Should
  governments impose congestion pricing to enter city centers?"*; a **tech-ethics**
  question — *"Should AI-generated art be eligible for copyright protection?"*; and a
  **lifestyle** question — *"Is waking up at 5am the key to a productive life?"*.
- **The real lesson — attempting real runs surfaced two engine bugs:** the *first*
  batch of sample runs were generated before two now-merged fixes, and reading the
  transcripts is exactly what exposed the bugs. The debaters were arguing *generic*
  positions, not the stated motion. Root causes: (1) #202 — the debate topic was
  never injected into the debater's context, so the agent only knew "argue the FOR
  side" of *some* topic; and (2) #203 — even once a system prompt was built, the
  engine *dropped it* on the `message_history` path and never delivered it to the
  model. Both are the kind of bug that unit tests with mocked models happily pass but
  that a human reading a real transcript catches in seconds. **Prompt-Book lesson:
  the cheapest validation of an LLM pipeline is to read one real transcript end-to-end
  — paid runs are not just evidence, they are a test.** After both fixes merged to
  `main`, the runs were **regenerated on the fixed engine**: the debaters now name and
  argue the exact motion (e.g. Pro on congestion pricing cites London's 30% traffic
  drop; Con on AI art invokes *Thaler v. Perlmutter* and human-authorship doctrine)
  and rebut each other's actual words. Winners on the regenerated runs: Pro (policy),
  Con (tech-ethics), tie (lifestyle).
- **Reduced-rounds decision (documented in `runs/README.md`):** sample runs use a
  reduced round count (**`--rounds 4`** policy, **`--rounds 3`** the other two) with
  **`--max-words 120`** instead of the default **10×150**, purely for cost — total
  ≈$1 across all three (regeneration on the fixed engine cost ~$0.42 + ~$0.26 + ~$0.30)
  instead of low-single-dollars. A 3-4 round debate still exercises the *entire*
  mechanism (Pro/Con alternation, rebuttal of the opponent's actual words, the
  controller drift-check/nudge path, the closing discussion, the debate-derived
  verdict, the per-model cost table), so it is valid evidence; the system's default
  remains the full 10×150. A **`--rounds 1` smoke test ran first** (and was rerun
  after the fixes merged) to confirm the engine delivers the topic + system prompt
  end-to-end with the configured key before spending on the three real runs.
- **Outcome/pattern:** Wrote a small TDD-first md exporter
  (`core/export/markdown.py` + `_sections.py`, <150 lines each) that renders a
  completed `DebateResult` and **reuses `format_cost_table` verbatim** — no
  duplicated pricing/markdown (§4). A build-time `scripts/generate_sample_runs.py`
  drives `DebateEngine.run` (writes the jsonl via LOG) then `write_run_markdown`
  (writes the md), with all debate params as CLI flags (no hard-coding). Two
  Windows/env gotchas surfaced on the real run: a *blank* process `ANTHROPIC_API_KEY`
  shadowed the `.env` value (pydantic-settings: env wins over env_file) — fixed by
  clearing the blank shadow so `Settings` reads `.env`, then exporting the key for
  pydantic-ai; and the pretty console LOG sink died on emoji debate text under a
  legacy code page (cp1255) — fixed by forcing UTF-8 on the script's streams.
  *Pattern: a readable artifact reuses the existing renderer rather than
  re-implementing it; and "cost-conscious" means smoke-test-then-reduce, never
  loop-on-error against a paid API.*

### Aggregate runs dataset (task 14.1, issue #97, 2026-05-31)

- **Prompt intent:** read `runs/*.jsonl` and aggregate per-topic outcomes,
  drift/nudge counts per side, tokens and latency into a tidy dataset (CSV/parquet).
- **Source-of-truth decision:** the dataset is built *only* from the committed
  `runs/<run_id>.jsonl` LOG event logs — the same machine log the teacher reviews —
  not from a re-run engine or the `.md` files. Reading one log end-to-end first
  (the 12.5 lesson) revealed the exact shape: per-`message` `tokens` is a combined
  count (no input/output split, no per-model id), the topic lives in the
  `debate_setup` system event, and the winner/`converged` flag in the `verdict`
  event. The runs dir *also* holds package LOG chatter files (`api.jsonl`, …) with
  no `event_type`; an `is_debate_run` filter (has a setup or verdict) cleanly
  excludes them so only the three real debates land in the dataset.
- **Cost is an honest estimate, not a fabrication:** because the JSONL lacks the
  input/output split, `est_cost_usd` prices `total_tokens` at the configured
  debater model's *input* rate from `config/model_prices.json` (config-driven, no
  hard-coded price). Input tokens dominate (~99.8k vs ~8k output on the policy run),
  so the estimate tracks the real billed cost closely; the *exact* per-model cost
  still lives in each `<run_id>.md`. The column README documents this caveat rather
  than silently presenting an approximation as the truth.
- **Outcome/pattern:** TDD red-first (`packages/core/tests/test_runs_aggregation.py`
  with synthetic in-memory JSONL fixtures, never the committed runs), then a small
  `core/research/` package split four ways under the 150-line cap (`_summary` value
  object, `_parse` fold, `_aggregate` dir-walk, `_dataset` stdlib-CSV io) plus a thin
  `scripts/aggregate_runs.py` CLI. **Stdlib `csv`, not parquet** — pandas/pyarrow are
  not workspace deps and the acceptance criteria only need a dataset to *exist*; a
  heavy dep just for this would violate "don't add deps you don't need". No external
  API calls, so the Epic-13 gatekeeper rule is N/A. *Pattern: aggregate from the
  durable log artifact, filter non-domain files explicitly, and label any value the
  source can't supply exactly (cost) as an estimate.*

### Analysis notebook (task 14.2, issue #98, 2026-05-31)

- **Prompt intent:** a `notebooks/` analysis presenting who-wins distribution,
  agree-vs-disagree rate, drift/nudge frequency per side (anti-sycophancy
  evidence) and tokens/latency per round.
- **Thin-notebook / tested-module decision:** all reusable analysis logic lives
  in the *tested* `agent_debate.core.research.analysis` module (pure functions:
  `who_wins`, `agree_vs_disagree`, `nudges_per_side`, `round_metrics`,
  `tokens_latency_per_topic`); the `notebooks/analysis.ipynb` notebook just
  imports them and prints tables. This keeps the analyses under the TDD/coverage
  gate (a notebook can't be unit-tested cleanly) and the notebook's code cells
  minimal. Note: ruff/mypy in `pyproject.toml` only scan `packages/*/src` + tests
  + select scripts, so the notebook is outside the type/lint gate — its cells are
  kept clean regardless and committed with **cleared outputs** so no stale numbers
  or accidental secrets land in the repo (a stdlib smoke test asserts this).
- **Tables, not charts — no new deps:** `matplotlib`/`pandas` are not workspace
  dependencies, and rich visualisation is the separate task **14.3**, so 14.2
  stays stdlib-only and presents the analyses as printed tables. Jupyter is pulled
  in on demand via `uv run --with jupyter` rather than added as a permanent dep.
- **Round-level detail from the JSONL:** the 14.1 `RunSummary` only carries
  run-level totals, so `round_metrics` parses per-round tokens/latency (with a
  per-side split) straight from the durable LOG event log — reusing the 14.1
  source-of-truth rather than re-implementing parsing. *Pattern: put the analysis
  in a covered module, keep the notebook a thin presentation layer, and only reach
  into the raw log for detail the aggregated dataset can't supply.*

### Interpreted visualizations (task 14.3, issue #99, 2026-05-31)

- **Prompt intent:** produce charts for the §9 analyses, *save* them, and
  *interpret each in prose* connecting the observation to the design — §9 wants
  interpretation, not just numbers.
- **Reuse-not-reimplement:** the chart module
  (`agent_debate.core.research.viz`) takes the 14.2 analysis outputs
  (`who_wins`, `agree_vs_disagree`, `nudges_per_side`, `RoundMetric`) and draws
  them; it never re-aggregates the runs. The thin
  `scripts/generate_figures.py` CLI (mirroring `aggregate_runs.py`) writes the
  PNGs to `notebooks/figures/`.
- **Optional dep, guarded import:** matplotlib is a *research/notebook* concern,
  not a runtime dep of the SDK/API/CLI surfaces, so it goes into the dev group
  plus a dedicated `[dependency-groups] viz` group (`uv sync --group viz`) — not
  `core`'s runtime deps. The import is **deferred** inside a `_pyplot()` helper
  that forces the headless Agg backend, so `agent_debate.core` still imports fine
  when the extra is absent; only drawing a chart needs it.
- **Interpretation over metrics:** the prose (`notebooks/figures/README.md` + a
  notebook viz section) reads each chart against the anti-sycophancy design —
  balanced who-wins, **0% convergence as the *expected* adversarial outcome**,
  **0/0 nudges as evidence the side-anchoring held without controller
  intervention** (the nudge path itself is covered by engine staged-drift tests
  8.4), and the super-linear per-round token/latency growth as the §10 cost
  signature. Kept honest about the small **n = 4** sample. *Pattern: a chart is
  only useful once it is read back against the design hypothesis it tests.*

### Parameter exploration (task 14.4, issue #100, 2026-05-31)

- **Prompt intent:** run a small sweep over `MAX_WORDS`/`ROUNDS`/model and report
  the effect on debate quality and cost.
- **Cost-free, data + model-driven approach:** the user is cost-sensitive, so we
  ran **no new paid debates**. Instead the exploration is grounded in three
  transparent sources: (1) the **4 existing runs** (already span `ROUNDS` ∈
  {3, 4, 10}, `MAX_WORDS` ∈ {120, 150}) via the 14.1 aggregation; (2) the
  **validated PRD §10 cost model** — output ~linear in `ROUNDS × MAX_WORDS`,
  input ~quadratic in `ROUNDS` (context replay) — scaled from the richest run;
  (3) the **config price table** (`config/model_prices.json`) for the model lever.
- **Reuse-not-reimplement:** new `agent_debate.core.research.params` builds on the
  14.1 `RunSummary` rows and the Epic-15 `compute_cost`/`PriceTable` — it adds no
  pricing logic of its own. Pure functions only: `empirical_points`,
  `fit_token_model`, `project_grid` (rounds × max_words grid), `model_choice_table`
  (same usage priced per model). No hard-coded prices/paths.
- **Honesty about the method:** the empirical points are real but **n = 4 is
  small**; the grid is an analytical *projection*, not a fresh paid sweep — a real
  paid parameter sweep is a documented future extension. Concrete sanity check
  (Sonnet debater): 10r/150w ≈ \$1.86, halving both knobs to 5r/120w ≈ \$0.58
  (~the 4× saving §10 predicts); same usage costs ≈ \$0.62 on Haiku, ≈ \$9.3 on
  Opus. *Pattern: when a paid sweep is too costly, a validated cost model + the
  config price table can project the parameter surface from the runs you already
  have — as long as you label the projection as such.*

### runs/ index (task 12.6, issue #87, 2026-06-01)

- **Prompt:** "Create `runs/README.md` indexing each saved debate (topic, who won,
  link) and link it from the root README."
- **Context:** `runs/README.md` already existed from 12.5 with a context table but
  (a) no links to the per-run transcripts and (b) a `(A fuller index with links is
  task 12.6.)` placeholder, and the root README's Documentation table did not point
  to it at all. So 12.6 was a *finish-and-wire-up*, not a rewrite.
- **Verify-from-source, not memory:** every winner/round/topic in the index was
  re-read from the actual `runs/<run_id>.md` verdict + `## Cost & tokens` sections
  (and cross-checked against `runs/dataset/runs_summary.csv`) rather than trusted
  from prior notes — policy = Pro (4r), tech-ethics = Con (3r), lifestyle = tie (3r),
  capitalism = Pro (10r). The token/cost columns are each run's actual billed totals.
- **Index shape:** the issue's required columns are **topic → who won → link**; the
  table leads with those and keeps the useful 12.5 context (kind, rounds, the
  reduced-rounds-for-cost vs full-10-round capitalism note) plus cross-links to the
  aggregated `dataset/runs_summary.csv` and the §9 `notebooks/analysis.ipynb`.
- **Docs-only, no Python:** no exporter/code change was needed, so none was made; the
  README contract test (`tests/test_readme.py`) stays green and the root README now
  links the runs index from its Documentation table. *Pattern: when a prior task
  leaves a labelled placeholder, the follow-up task's job is to make it true and
  wire it into the entry-point doc — not to regenerate the underlying artifacts.*

## 12.7 — Final pass vs Improvements checklist

> Go through docs/Improvements_to_keep_in_mind.md and verify/tick every item; fix any gaps. (Repo standards: TDD, ≤150 lines/file, ruff+mypy clean, no hard-coded values, external calls via the API gatekeeper, LOG for logging, coverage ≥85%.)

- **Verification, not feature work:** all 13 Improvements items were already
  satisfied by the mature Epics 0–15 codebase, so this task added **no product
  code**. Each box was ticked only after confirming it against a real gate run or
  the actual file (PRD §10 for cost, `.github/workflows/ci.yml` for tooling,
  `core/security/sanitiser.py` + `core/gatekeeper/` for the trust-boundary item,
  `.env`-ignored + `scripts/secret_scan.py` for secrets, etc.).
- **Evidence inline:** every ticked box carries a one-line "— evidence" pointer
  to the backing file/command, so the checklist is auditable from the doc alone.
- **Honest scoping:** the "keep docs current" item notes ongoing upkeep is owned
  by task D.6, and the lecturer-guidelines final pass remains task 12.8 — neither
  was claimed here. *Pattern: a P0 "tick every box" pass is a verify-and-cite
  task; tick only what a gate or file proves, and name the owning task for the
  rest rather than faking a tick.*

## 12.8 — Final pass vs lecturer guidelines

> Go through the lecturer's software_submission_guidelines-V3 and the §17 final checklist; verify each requirement is met and fix gaps. (Repo standards: TDD, ≤150 lines/file, ruff+mypy clean, no hard-coded values, external calls via the API gatekeeper, LOG, coverage ≥85%.)

- **Deliverable = a completed, evidence-backed checklist, not a tick in the PDF.**
  The guideline §17 list is the lecturer's authoritative doc and shouldn't be
  edited; the cleaner home was a new [`docs/SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md)
  that reproduces all 30 §17.1–§17.6 items and maps each to a **specific file or
  gate** in the repo, linked from the README docs table and PRD companion-docs list.
- **Verification, not feature work:** every §17 item was already satisfied by the
  mature Epics 0–15 codebase, so this task added **no product code**. Each item was
  marked ✅ only after confirming it against a real gate run (`ruff`=0, `mypy` clean,
  `pytest --cov`=99.24%, `check_line_limit`=pass) or the actual artifact (sub-PRDs,
  `config/*.json` versioned `1.00`, `notebooks/figures/`, ISO 25010 mapping in
  ARCHITECTURE §8, etc.).
- **PLAN/TODO naming:** the guideline names `PLAN.md`/`TODO.md`; the repo's
  `ARCHITECTURE.md` (planning/architecture) and `TASKS.md` (task list) fill those
  roles — recorded explicitly in the checklist rather than renaming mature docs.
- **Honest scoping:** the known Windows test-env failures (live-tree secret scan
  on the real local `.env`, two path-regex `test_missing_file` cases, long-topic
  teardown env-var limit, Unix permission checks) are documented as TEST-ENV
  artifacts that don't affect any §17 item; ongoing doc upkeep stays owned by task
  D.6. *Pattern: when the lecturer's checklist lives in an authoritative doc, ship
  a separate evidence-mapped checklist and cite a gate/file for every box.*

## D.6 — Keep planning docs updated (doc-reconciliation pass, 2026-06-01)

> As implementation progresses, keep docs/PRD.md, docs/prds/*, docs/TASKS.md, docs/PROMPTS.md, and docs/Improvements_to_keep_in_mind.md in sync with reality. Update the Prompt Book with significant prompts. (Repo standards: TDD, ≤150 lines/file, ruff+mypy clean, no hard-coded values, external calls via the API gatekeeper, LOG, coverage ≥85%.)

- **The last open task, and a pure docs pass:** with every epic (0–15) built and
  merged, D.6 reconciles the *planning* docs against the finished system — no product
  code changed.
- **The real drift found:** `docs/TASKS.md` still showed **every** task as `[ ]`
  except the most-recent doc tasks — i.e. the entire implemented backlog (Epics 0–11,
  13, 15.1/15.2, 12.3) read as "todo" despite being merged. Ticked all 91 task bullets
  + the PRD §11 acceptance boxes to `[x]`, and moved both `Status:` lines from "Draft
  v0.2 / 2026-05-30" to "v1.0 — implemented / 2026-06-01". The root README already
  pointed at TASKS.md "for the per-epic status", so fixing the ticks was what made that
  link honest.
- **PRD:** §13 Milestones (M1–M5) were phrased as a future plan → marked **realized**;
  §5/§6/§9/§10 already described what exists, so left intact.
- **Sub-PRDs:** the four were content-accurate but stamped "Draft v0.1"; bumped to
  "v1.0 — implemented". Added an explicit *delivery* note to `anti-sycophancy.md` §2 and
  `debate-orchestration.md` §3 that the side **and topic** reach the model via the
  leading `SystemPromptPart` on the `message_history` path (the #202/#203 fixes) — the
  one place the specs lagged the engine.
- **PROMPTS / Improvements / README:** promoted the #202/#203 lesson to a dedicated
  Prompt-Book entry (it was embedded in the 12.5 entry); confirmed the Improvements
  "keep docs current" item (its owner is D.6) is now honestly satisfied; README
  project-status text was already accurate (finished system, no stale scaffold language).
- *Pattern: a "keep docs current" task is mostly an audit — flip the stale state markers
  (checkboxes, Status/Last-updated), reconcile only the specs that actually lag the code,
  and resist rewriting docs that are already true.*

---

### Engine bug fixes #202 / #203 — the debaters were running WITHOUT their system prompt (2026-06-01)

> Curated standalone lesson (first surfaced in the 12.5 sample-runs entry above).
> Significant enough to stand on its own because it is the single most instructive
> failure of the whole build.

- **The symptom (caught by a human, not a test):** the first batch of paid sample
  runs (task 12.5) read wrong — Pro and Con argued *generic* for/against positions
  and never named the actual motion. Every unit test was green. Reading **one real
  transcript end-to-end** is what exposed it.
- **Two root causes, two merged fixes:**
  - **#202 — the topic never reached the debater.** The debate topic was not injected
    into the debater's system prompt, so the agent only knew "argue the FOR side" of
    *some* unstated topic. Fix: `setup_debate` now builds each debater's prompt with
    the validated topic baked in (`build_debater_system_prompt(side, topic=…, …)`).
  - **#203 — the system prompt was silently dropped.** Even once a correct
    `system_prompt` was configured on the pydantic-ai `Agent`, the engine **always**
    runs debaters with a `message_history` (each agent's isolated `AgentContext`), and
    **pydantic-ai does not re-inject a configured `system_prompt` once a
    `message_history` is supplied.** So the model received *no* `SystemPromptPart` at
    all — no side, no rules, no skills list, no topic. Fix: the agent's own prompt text
    is stored on its `AgentContext` and `message_history()` embeds it as the leading
    `SystemPromptPart` of the first request, **exactly once** per run, isolated to that
    agent's thread (`core/agents/context.py`, `engine/setup.py::_attach_system_prompts`).
- **TDD lock-in:** `packages/core/tests/test_system_prompt_delivery.py` drives the real
  engine turn/closing path with a `FunctionModel` that captures the full `ModelMessage`
  list and asserts the debater's full prompt (side label + topic + a skill name) reaches
  the model as one leading `SystemPromptPart`, delivered once across a multi-turn run and
  isolated per side (Con sees AGAINST, never FOR) — a regression guard against both bugs.
- **Prompt-Book lesson (the durable one):** *the cheapest, highest-yield validation of an
  LLM pipeline is to read one real transcript end-to-end.* Mocked-model unit tests happily
  pass while the model silently receives an empty/incomplete prompt; a human reading a paid
  run catches it in seconds. Two corollaries: (1) when you supply `message_history` to
  pydantic-ai, you own system-prompt delivery — the framework will not do it for you; and
  (2) a paid sample run is not just *evidence*, it is a *test* — budget for at least one
  and actually read it. After both fixes merged, the runs were regenerated on the fixed
  engine and the debaters now name and argue the exact motion (see `runs/` + the 12.5 entry).

---

## HW2 requirements PDF alignment (2026-06-01)

### Align the PRD with the authoritative exercise spec
- **Prompt:** "Align `docs/PRD.md` with the authoritative HW2 requirements PDF … fold in
  the eight PDF-mandated requirements the PRD does not yet state (no-tie verdict,
  child→father→child routing, JSON IPC format, watchdog+keep-alive, log FIFO rotation,
  terminal menu, architecture class diagram, README screenshots). Be honest that several
  are not yet implemented — spec-only; implementation tracked by separate issues."
- **Outcome:** PRD updated to **v1.1 (HW2 compliance pass in progress)**. Added a
  companion-doc reference to `hw2_requirements.pdf` as authoritative; folded the eight
  requirements into §3, §5.4, §5.8, §6, §8, §11; added a §11.1 PDF-requirement→status
  map; adjusted status/milestone wording so the doc does **not** claim the gaps are done.
  Spec-only change — no code touched; the eight gaps are tracked by dedicated issues.

---

## HW2 §8.4 — Forbid tie verdicts (2026-06-01, issue #215)

### Verdict must always decide a winner
- **Prompt:** "Remove 'tie' as a permitted outcome (constrain `winner` to PRO|CON), use
  weighted/differential scoring so exact ties are near-impossible, and add a deterministic
  tie-breaker cascade (rebuttal quality → fewer drift captures → sourcing) for the
  equal-score case. Update the controller's system prompt to forbid declaring a tie."
- **Outcome:** `Verdict.winner` / `VerdictRequest.winner` constrained to `DebateSide`
  (no more `str`/`"tie"`). Engagement weight made distinct/non-integer (0.75) so the
  differential totals rarely collide. Added a deterministic `_break_tie` cascade
  (rebuttal criterion → fewer agreement-drift signals → engagement → fixed PRO fallback)
  that always yields PRO/CON. Controller system prompt gained a "tie is forbidden — you
  MUST declare a decisive winner; differential scoring permitted" block. TDD: the old
  balanced-debate-ties tests were rewritten to assert a decisive winner; acceptance
  `winner ∈ {PRO,CON,"tie"}` assertions narrowed to `{PRO,CON}`.

---

## HW2 §8.6 — Watchdog with keep-alive (2026-06-01, issue #216)

### Detect a fallen worker and restart it
- **Prompt:** "Add a Watchdog component (config-driven) that monitors agent/process
  liveness via keep-alive and restarts on failure, distinct from the timeout/retry seam.
  TDD; ≤150 lines/file; ruff/mypy/coverage ≥85%; log via the LOG package."
- **Outcome:** New `agent_debate.core.watchdog` subpackage (`_config.py`, `_watchdog.py`).
  `config/watchdog.json` (mirrors `rate_limits.json`) supplies `heartbeat_interval_s`,
  `liveness_timeout_s`, `max_restarts` via a frozen `WatchdogConfig`. `Watchdog.run`
  drives a worker through injected `start`/`kill`/`heartbeat` callables and injected
  `monotonic`/`sleep` clock seams (deterministic, no real timing); a keep-alive stale
  beyond `liveness_timeout_s` is treated as fallen → kill + restart up to `max_restarts`,
  then give up. Each detect/kill/restart/give_up logs a `system` event tagged
  `payload['watchdog']`. Distinct from per-turn timeout/retry (which bounds/retries one
  `execute()` call): the Watchdog guards a longer-running unit of work by liveness. TDD
  red-first (`tests/test_watchdog.py`).

### FIFO-rotate the built-in JSONL logs within configured caps

- **Prompt:** "Add config-driven FIFO log-file rotation (max files, max lines/file;
  oldest dropped first). TDD; ≤150 lines/file; ruff/mypy/coverage ≥85%; no hard-coded
  counts." (HW2 §8.6)
- **Outcome:** New `agent_debate.log._rotation` (`RotationConfig`, `load_rotation_config`,
  `RotatingJsonlSink`) wired into `_setup._open_sink`. `config/logging.json` (mirrors
  `rate_limits.json`/`watchdog.json`) supplies `max_files` + `max_lines_per_file`;
  defaults 20×500 follow the PDF example. The live file stays `runs/<run_id>.jsonl`
  (backward compatible); at the line cap it rolls over logrotate-style (`<stem>.1.jsonl`
  newest archive, higher index = older) and the oldest archive is deleted first so total
  files never exceed `max_files`. TDD red-first (`packages/log/tests/test_log_rotation.py`).

### Route every debate message through the controller (child → father → child)

- **Prompt:** "Refactor so each message is explicitly routed through the controller
  (father) before reaching the opponent. Keep context isolation + anti-sycophancy
  intact; TDD; ≤150 lines/file; ruff/mypy/coverage ≥85%." (HW2 §8.3.7)
- **Outcome:** New `engine.forward.forward_to_opponent` makes the controller the
  explicit relay hub: it frames the message via the reused `build_adversarial_relay`
  and logs a `system` routing event tagged `message_routed_through_controller`
  (from/to side + round) — the demonstrable evidence the message passed through the
  father. The loop forwards each produced message through the controller, and the
  opponent's `run_debate_turn` rebuts the controller-forwarded frame (param renamed
  `opponent_message` → `framed_opponent_message`; the turn no longer re-frames). 5.4
  isolation, 5.6 adversarial framing, side-anchoring, drift-check/nudge, 10-vs-10 and
  timeout/retry are all preserved. TDD red-first
  (`packages/core/tests/test_controller_relay.py`).

### Structured JSON envelope for inter-agent messages

- **Prompt:** "Wrap inter-agent turns in a structured JSON schema (round, side,
  content, etc.) while keeping prompts legible to the model. TDD; ≤150 lines/file;
  ruff/mypy/coverage ≥85%." (HW2 §8.3.8)
- **Outcome:** New `engine.message.AgentMessage` (pydantic) is the structured JSON
  envelope for each inter-agent hop — `round`, `from_side`, `to_side`, `type`,
  `content` — JSON-serialisable and lossless round-trip. The controller's forward
  step builds the envelope, logs it on the existing
  `message_routed_through_controller` routing event (additive `envelope` payload key,
  no schema break), and *renders* the legible §5.6 adversarial relay from `content`
  via the reused `build_adversarial_relay` — so the model still receives "Your
  opponent argued: «…». Rebut it." (debate quality preserved). Envelope = monitorable
  JSON transport/log; render = the legible prompt injected into the opponent. TDD
  red-first (`packages/core/tests/test_agent_message.py`).

---

_(add entries here as code is built — significant prompts that set a pattern,
unblocked a step, or changed a decision.)_
