# Sample debate runs

This folder holds **committed sample debate runs** so the teacher can review real
debates end-to-end (PRD §11, TASKS.md 12.5). Each run is two files sharing a
`<run_id>`:

- `<run_id>.jsonl` — the machine-readable per-run event log written by the LOG
  package (PRD §5.8): every `message` / `tool_call` / `nudge` / `timeout` / `retry`
  / `verdict` / `system` event, with `run_id`, `round`, `agent`, `tokens`,
  `latency_ms`. Secrets are redacted by the LOG redactor before either sink.
- `<run_id>.md` — a human-readable rendering of the same run: the round-grouped
  transcript, the closing discussion, the controller's anti-sycophancy nudges, the
  final verdict, and the per-model cost-breakdown table. Rendered by
  `agent_debate.core.write_run_markdown` (which reuses the existing
  `format_cost_table` — no duplicated pricing/markdown).

## The committed runs

| Run id | Kind | Topic | Winner |
| --- | --- | --- | --- |
| `policy-congestion-pricing` | policy | Should governments impose congestion pricing to enter city centers? | Pro |
| `techethics-ai-art` | tech-ethics | Should AI-generated art be eligible for copyright protection? | Pro |
| `lifestyle-morning-routine` | lifestyle | Is waking up at 5am the key to a productive life? | Pro |

(A fuller index with links is task 12.6.)

## Reduced rounds for cost — the system supports the full 10

These sample runs were generated with **4 rounds per side** and a **120-word**
message limit (`--rounds 4 --max-words 120`) to keep the real-API cost to a few
cents each (~$0.3/run, well under a dollar). This is *deliberate cost control*, not
a limitation: the system's default is the full **10 rounds × 150 words** (PRD §2,
§7), and a 4-round debate already exercises the entire mechanism — Pro/Con
alternation, rebuttal of the opponent's actual words, the controller drift-check /
nudge path, the closing discussion, the debate-derived verdict, and the
token/cost-breakdown table. To reproduce at the full default, drop the flags:

```bash
uv run python scripts/generate_sample_runs.py \
    --topic "Should governments impose congestion pricing to enter city centers?"
```

## How they were generated

```bash
uv run python scripts/generate_sample_runs.py --rounds 4 --max-words 120 \
    --run-id policy-congestion-pricing \
    --topic "Should governments impose congestion pricing to enter city centers?"
```

Every model call routes through the Epic-13 API gatekeeper inside the SDK; the
generator adds no direct external calls. Provider key is read from `.env` (never
committed).
