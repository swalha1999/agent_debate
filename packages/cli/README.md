# `agent_debate.cli` — the CLI

A thin [Typer](https://typer.tiangolo.com/) shell over the
[`core`](../core/README.md) SDK (PRD §6): run a full structured debate from your
terminal and watch the Pro/Con transcript stream live, with inline controller
nudges and the final verdict.

> Distribution `agent_debate_cli` · importable module `agent_debate.cli` ·
> console script **`agent-debate`**. Depends on
> [`agent_debate.core`](../core/README.md) and
> [`agent_debate.log`](../log/README.md).

## Install / run

```bash
uv sync                                   # from the repo root
uv run agent-debate run "Should cities ban cars downtown?"
```

A real run needs `ANTHROPIC_API_KEY` in your `.env` (validated by the SDK); every
model call is routed through the Epic-13 [gatekeeper](../core/src/agent_debate/core/gatekeeper/).

## Commands & options

The app is defined in [`app.py`](src/agent_debate/cli/app.py).

```text
agent-debate run TOPIC [OPTIONS]
```

| Option | Effect | Default |
| --- | --- | --- |
| `TOPIC` (arg) | The debate topic to argue. | required |
| `--rounds` | Debate rounds per side. | from config (`ROUNDS`) |
| `--max-words` | Word limit per message. | from config (`MAX_WORDS`) |
| `--model` | `provider:model` override for BOTH debaters. | from config (`DEBATER_MODEL`) |
| `--search-backend` | Search plug-in (e.g. `duckduckgo`/`tavily`). | from config (`SEARCH_BACKEND`) |
| `--json` | Emit the `DebateResult` as one machine-readable JSON blob (no live UI). | off (human view) |

No hard-coded defaults: every option defaults to `None` and only the flags you
actually pass override the process [`Settings`](../core/src/agent_debate/core/settings.py).
Change config, not the CLI, to change the defaults.

## Examples

```bash
# Human view: live Rich transcript + verdict, streamed round by round.
uv run agent-debate run "Should remote work be the default?" --rounds 6 --max-words 120

# Machine view: ONLY the DebateResult JSON on stdout (logs go to stderr), pipeable.
uv run agent-debate run "Is nuclear power worth the risk?" --json > result.json

# Help for the whole app or a command.
uv run agent-debate --help
uv run agent-debate run --help
```

On failure (missing key, invalid topic, a turn exhausting its retries, or any
engine error) both paths report to stderr and exit non-zero.

## Develop & test

Tests inject a stub engine, so the suite needs no key or network:

```bash
uv run pytest packages/cli --cov
```

## See also

- [Root README](../../README.md) · [SDK](../core/README.md) ·
  [API](../api/README.md) · [UI](../ui/README.md) · [LOG](../log/README.md)
- [`docs/PRD.md`](../../docs/PRD.md) §6 — surfaces.
