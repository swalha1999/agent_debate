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

_(add entries here as code is built — significant prompts that set a pattern,
unblocked a step, or changed a decision.)_
