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

_(add entries here as code is built — significant prompts that set a pattern,
unblocked a step, or changed a decision.)_
