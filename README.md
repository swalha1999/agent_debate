# agent_debate

**Two AI agents debate opposite sides of a topic — one *for*, one *against* —
across a fixed number of rounds, while a third *controller* agent moderates,
keeps each debater on track, and at the end writes a summary, the result, and a
verdict on who won.**

The point of interest is **the debate itself** — whether the agents genuinely
engage, rebut each other, and converge or stay opposed — **not** fact-checking.
A core design risk the system engineers against is **sycophancy**: LLMs tend to
drift toward the last speaker's position, so the architecture keeps each debater
on its assigned side and lets the controller nudge a "captured" agent back.

The project ships five surfaces — **SDK** (the `core` engine), **CLI**, **API**,
**UI**, and **LOG** — built as a [`uv`](https://docs.astral.sh/uv/) workspace of
namespace packages under `packages/`. For the full product vision, goals, and
architecture, see [`docs/PRD.md`](docs/PRD.md).

> **Project status:** all five surfaces are built and runnable. The debate
> engine (SDK), CLI, API, UI, and LOG packages are implemented over the `uv`
> workspace, with the API gatekeeper, search plug-ins, anti-sycophancy logic,
> and cost accounting in place (see [`docs/TASKS.md`](docs/TASKS.md) for the
> per-epic status). Each surface has its own README — linked from the
> [Quickstart](#usage--quickstart) below.

## System requirements

| Requirement | Version / notes |
|---|---|
| **Python** | **>= 3.12** (pinned via `.python-version`). |
| **[uv](https://docs.astral.sh/uv/)** | Package & workspace manager (replaces pip/venv). Install from the uv docs. |
| **git** | To clone the repository. |
| **OS** | Developed on macOS/Linux; Windows works via WSL2 (the helper scripts assume a POSIX shell). |
| **Anthropic API key** | Required to run debates against the default provider. Free local tasks (tests, lint) need no key. |

`uv` manages the Python toolchain and a project-local virtual environment, so no
global Python or manual `venv` setup is needed.

## Installation

Step by step, from a clean machine:

```bash
# 1. Clone the repository
git clone https://github.com/swalha1999/agent_debate.git
cd agent_debate

# 2. Install every workspace package + dev tooling into a local .venv
uv sync

# 3. Create your local environment file from the template
cp .env.example .env
```

Then open `.env` and fill in **`ANTHROPIC_API_KEY`** with your key from
<https://console.anthropic.com/>. The remaining variables ship with working
defaults — see the [Configuration](#configuration) section. `.env` is
git-ignored and must never be committed; `.env.example` documents every variable
and contains only safe placeholders.

Verify the install:

```bash
uv run pytest        # the test suite should pass
```

## Usage / Quickstart

### Run a debate

All five surfaces are runnable. A real run needs `ANTHROPIC_API_KEY` in your
`.env` (see [Installation](#installation)); every external model/search call is
routed through the API gatekeeper. Each surface has a dedicated README with its
full reference — links below.

**CLI** ([`packages/cli`](packages/cli/README.md)) — run a debate from the
terminal and watch the transcript stream live:

```bash
uv run agent-debate run "Should cities ban cars downtown?" --rounds 10 --max-words 150
uv run agent-debate run "Is nuclear power worth the risk?" --json   # machine-readable
```

**SDK** ([`packages/core`](packages/core/README.md)) — drive a debate
programmatically (the canonical import is `agent_debate.core`):

```python
from agent_debate.core import DebateEngine

engine = DebateEngine()                       # config comes from .env / Settings
result = engine.run("Should cities ban cars downtown?")
print(result.verdict)                         # winner + summary + agree/disagree
for event in engine.stream("Should cities ban cars downtown?"):
    print(event)                              # live events, then the final result
```

**API** ([`packages/api`](packages/api/README.md)) — FastAPI service; start it,
then POST a topic and stream events:

```bash
uv run agent-debate-api                        # serves http://localhost:8000 (docs at /docs)
# POST /debates {"topic": "..."} -> {run_id}; GET /debates/{id}; GET /debates/{id}/stream (SSE)
```

**UI** ([`packages/ui`](packages/ui/README.md)) — web frontend over the API;
enter a topic and watch the Pro/Con transcript, moderator nudges, and verdict:

```bash
uv run agent-debate-ui                         # serves http://localhost:5173 (needs the API running)
```

**LOG** ([`packages/log`](packages/log/README.md)) — structured logs (JSON +
pretty console) accompany every run, one JSONL file per `run_id`:

```python
from agent_debate.log import get_logger
get_logger("my-run").info("debate_run_started", topic="...")
```

A typical workflow: pick a topic → the controller assigns sides → 10 Pro/Con
rounds with web-search-grounded rebuttals → a closing discussion → the controller
renders a summary, an agree/disagree result, and who won.

### Repo quality gates

These work without any API key — run them before opening a PR:

```bash
uv run pytest --cov          # run the test suite with coverage (>= 85% gate)
uv run ruff check .          # lint (target: 0 violations)
uv run ruff format --check . # formatting check
uv run mypy                  # static type check

# Repo-hygiene gates (also enforced in CI):
uv run python scripts/check_line_limit.py   # no code file > 150 lines
uv run python scripts/secret_scan.py        # fail if a secret is committed
```

## Configuration

Runtime behaviour is configured through environment variables (copied from
`.env.example` into `.env`). The most important ones:

| Variable | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Default provider key (**required** to run debates). | — |
| `DEBATER_MODEL` | Model for both debaters. | `anthropic:claude-sonnet-4-6` |
| `CONTROLLER_MODEL` | Model for the controller/judge. | `anthropic:claude-opus-4-8` |
| `ROUNDS` | Rounds per agent. | `10` |
| `MAX_WORDS` | Word limit per message. | `150` |
| `TURN_TIMEOUT_S` | Per-turn timeout (seconds). | `60` |
| `MAX_RETRIES` | Retries on timeout/error. | `2` |
| `SEARCH_BACKEND` | Search plug-in (`duckduckgo`/`tavily`/…) — swap with one value. | `duckduckgo` |

See `.env.example` for the complete annotated list and
[`docs/PRD.md`](docs/PRD.md) §7 for the full reference. API rate limits are **not**
env vars — they live in versioned `config/rate_limits.json` (PRD §5.6).

## Troubleshooting

| Symptom | Likely cause & fix |
|---|---|
| `uv: command not found` | `uv` is not installed or not on `PATH`. Install it from <https://docs.astral.sh/uv/> and reopen your shell. |
| `uv sync` resolves the wrong Python / fails on version | Your Python is older than 3.12. `uv` reads `.python-version`; let it manage the toolchain, or install Python 3.12+. |
| Authentication / `ANTHROPIC_API_KEY` errors when running a debate | `.env` is missing or the key is unset. Run `cp .env.example .env` and set a real key from <https://console.anthropic.com/>. |
| Imports like `agent_debate.core` not found | Run via `uv run …` so the workspace venv is active, and re-run `uv sync` after pulling new packages. |
| `pytest` reports coverage below the threshold | The suite enforces `fail_under = 85`; add tests for the uncovered lines shown by `--cov`'s "missing" report. |
| A commit is blocked by the secret scan | A key-like string was staged. Move secrets into `.env` (git-ignored); see `scripts/secret_scan.py`. |

## Documentation

| Document | What it covers |
|---|---|
| Per-package READMEs | One per surface: [`core` (SDK)](packages/core/README.md), [`cli`](packages/cli/README.md), [`api`](packages/api/README.md), [`ui`](packages/ui/README.md), [`log`](packages/log/README.md) — install/run/import, public API, config, and a minimal example for each. |
| [`docs/PRD.md`](docs/PRD.md) | Product Requirements — vision, goals, architecture, surfaces, acceptance criteria. |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture & decisions doc — the system, the five packages, key mechanisms, and an ADR-style "decisions / rationale" table for a new team member. |
| [`docs/UI.md`](docs/UI.md) | The web UI — annotated layout diagrams + UX walkthrough (understand the interface without running it). |
| [`docs/TASKS.md`](docs/TASKS.md) | The full task breakdown by epic, with status and dependencies. |
| [`runs/README.md`](runs/README.md) | Index of the committed **sample debate runs** — topic, who won, and a link to each readable transcript + verdict (the teacher's review evidence, PRD §11). |
| [`docs/prds/`](docs/prds/) | Dedicated sub-PRDs: [debate orchestration](docs/prds/debate-orchestration.md), [anti-sycophancy](docs/prds/anti-sycophancy.md), [API gatekeeper](docs/prds/api-gatekeeper.md), [search plug-in](docs/prds/search-plugin.md). |
| [`docs/PROMPTS.md`](docs/PROMPTS.md) | The Prompt Book — significant prompts that shaped the project (guideline §8.3). |
| [`docs/software_submission_guidelines-V3.en.md`](docs/software_submission_guidelines-V3.en.md) | The lecturer's submission guidelines (authoritative). |
| [`docs/SUBMISSION_CHECKLIST.md`](docs/SUBMISSION_CHECKLIST.md) | The completed **§17 final checklist** — every guideline item mapped to repo evidence (the submission-readiness proof). |
| [`docs/Improvements_to_keep_in_mind.md`](docs/Improvements_to_keep_in_mind.md) | Standing quality/lessons checklist. |

## Contributing & quality gates

This repo follows the engineering standards in [`docs/PRD.md`](docs/PRD.md) §8,
enforced in CI on every push:

- **TDD** — write the failing test first, then the code (Red → Green → Refactor).
- **Test coverage >= 85%** — enforced via `fail_under = 85`.
- **Max 150 lines per code file** — split into small modules; don't compress.
- **`ruff` = 0 violations** + **`mypy`** clean (strict).
- **No hard-coded values** — read configuration from `.env` / `config/`.
- **No secrets in the repo** — the secret scan fails the build on a hit.
- **Every external API call** goes through the API gatekeeper (PRD §5.6).

Before opening a PR, run the gate locally:

```bash
uv sync && uv run ruff check . && uv run ruff format --check . \
  && uv run mypy && uv run pytest --cov \
  && uv run python scripts/check_line_limit.py \
  && uv run python scripts/secret_scan.py
```

### Branch protection

`main` is a **protected branch**: there are **no direct pushes** — all changes
land through a pull request, and a PR **cannot merge unless the CI
`Quality gates` check is green**. This is enforced server-side by GitHub branch
protection (the `required_status_checks` rule names the `Quality gates`
check-run produced by [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

To keep the build reproducible, the exact rule is applied by a committed,
re-runnable script — owner/repo are read from `gh repo view`, never hard-coded:

```bash
./scripts/setup_branch_protection.sh   # requires an admin `gh auth login`
```

The rule is deliberately scoped so an admin maintainer can still merge an
approved PR once CI is green (`enforce_admins` is off and no approving reviews
are required); non-admins remain fully gated by the required check.

## License & credits

Coursework project for **Orchestration of AI Agents**, by **swalha1999** and
**Mhmdabad**. Built on open-source libraries including
[uv](https://docs.astral.sh/uv/), [Pydantic AI](https://ai.pydantic.dev/),
[FastAPI](https://fastapi.tiangolo.com/), [Typer](https://typer.tiangolo.com/),
[structlog](https://www.structlog.org/), [ruff](https://docs.astral.sh/ruff/),
[mypy](https://mypy-lang.org/), and [pytest](https://pytest.org/); each remains
under its own license. No project license has been declared yet.
