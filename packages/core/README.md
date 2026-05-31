# `agent_debate.core` — the SDK (debate engine)

The **heart of the system** (PRD §5.1): the debate engine, the Pro/Con/controller
agents, the skills, the anti-sycophancy logic, the [API gatekeeper](src/agent_debate/core/gatekeeper/),
the pluggable [search backends](src/agent_debate/core/search/), the input
[security](src/agent_debate/core/security/) validator, and the
[pricing](src/agent_debate/core/pricing/) / cost table. Every other surface
(CLI, API, UI) is a thin shell over this package.

> Distribution `agent_debate_core` · importable module `agent_debate.core`
> (a [PEP 420](https://peps.python.org/pep-0420/) namespace package). Depends on
> [`agent_debate.log`](../log/README.md).

## Install / import

The whole workspace installs in one step from the repo root:

```bash
uv sync                       # installs every package + dev tooling into .venv
```

Then import the SDK facade — note the canonical path is `agent_debate.core`:

```python
from agent_debate.core import DebateEngine
```

## Public API

The package re-exports its surface from
[`__init__.py`](src/agent_debate/core/__init__.py). The entrypoints a new
developer reaches for:

| Symbol | What it is |
| --- | --- |
| `DebateEngine` | The SDK facade. `DebateEngine(config).run(topic)` returns a `DebateResult`; `.stream(topic)` yields live events then the result. |
| `DebateConfig` | The validated run input (rounds, max_words, models, timeout, retries, budget). Build from settings via `DebateConfig.from_settings(settings)`. |
| `DebateResult` | The structured output: `transcript`, `tool_calls`, `nudges`, `closing_discussion`, `verdict`, `totals`, `cost_breakdown`. |
| `Settings` / `get_settings()` | Config-driven runtime settings, loaded from the environment / `.env` (PRD §7). |
| `ApiGatekeeper` | The Epic-13 gatekeeper every external model/search call routes through (rate-limit + FIFO queue + retry). |
| `create_search_provider()` | Build the configured search plug-in (`duckduckgo`/`tavily`/…). |
| `SecurityGatekeeper`, `validate_topic`, `sanitize_untrusted_text` | Input validation + untrusted-text sanitising (PRD §7.x). |
| `CostBreakdown`, `format_cost_table` | Per-model token → cost table (Epic 15). |

See `agent_debate.core.__all__` for the full list.

## Minimal example

```python
from agent_debate.core import DebateEngine

# Config + provider key come from .env / the environment (no hard-coded values):
# with no args, DebateEngine derives its DebateConfig from the process Settings.
engine = DebateEngine()
result = engine.run("Should cities ban cars downtown?")

print(result.verdict)              # winner + summary + agree/disagree
print(result.totals.total_tokens)  # token accounting
print(result.cost_breakdown)       # per-model cost table

# Stream live instead of blocking:
for event in engine.stream("Should cities ban cars downtown?"):
    print(event)  # each LogEvent in order; the final item is the DebateResult
```

A real run needs `ANTHROPIC_API_KEY`; tests inject a stub model so no key or
network is required (see `models=` on `DebateEngine`).

## Configuration

`DebateEngine`/`DebateConfig` read everything from `Settings` (PRD §7), so
behaviour is changed via config — not code. Key variables (full list in
[`.env.example`](../../.env.example)):

| Variable | Purpose | Default |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Provider key (required for real runs). | — |
| `DEBATER_MODEL` | Model for both debaters. | `anthropic:claude-sonnet-4-6` |
| `CONTROLLER_MODEL` | Model for the controller/judge. | `anthropic:claude-opus-4-8` |
| `ROUNDS` | Rounds per side. | `10` |
| `MAX_WORDS` | Word limit per message. | `150` |
| `TURN_TIMEOUT_S` | Per-turn timeout (s). | `60` |
| `MAX_RETRIES` | Retries on timeout/error. | `2` |
| `SEARCH_BACKEND` | Search plug-in. | `duckduckgo` |
| `BUDGET_USD` | Per-run USD cap; `0` = unlimited. | `0` |

API rate limits live in versioned [`config/rate_limits.json`](../../config/rate_limits.json);
per-model prices in [`config/model_prices.json`](../../config/model_prices.json).

## Develop & test

```bash
uv run pytest packages/core --cov   # this package's suite (coverage gate >= 85%)
uv run ruff check . && uv run mypy   # lint + types (run from repo root)
```

## See also

- [Root README](../../README.md) — full quickstart for all five surfaces.
- [`docs/PRD.md`](../../docs/PRD.md) §5–6 — architecture and surfaces.
- [`docs/prds/debate-orchestration.md`](../../docs/prds/debate-orchestration.md),
  [`anti-sycophancy.md`](../../docs/prds/anti-sycophancy.md),
  [`api-gatekeeper.md`](../../docs/prds/api-gatekeeper.md),
  [`search-plugin.md`](../../docs/prds/search-plugin.md).
- Sibling surfaces: [CLI](../cli/README.md) · [API](../api/README.md) ·
  [UI](../ui/README.md) · [LOG](../log/README.md).
