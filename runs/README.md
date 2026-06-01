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

These runs were **regenerated on the topic+system-prompt-fixed engine** (after the
two fixes in #202 — inject the debate topic into the debater context — and #203 —
actually deliver the agent system prompt to the model on the `message_history`
path). The debaters now argue the stated motion and rebut each other's actual words.

| Topic | Kind | Rounds | Winner | Total tokens | Cost (USD) | Read it |
| --- | --- | --- | --- | --- | --- | --- |
| Should governments impose congestion pricing to enter city centers? | policy | 4 | Pro | 107,744 | $0.419 | [`policy-congestion-pricing.md`](policy-congestion-pricing.md) |
| Should AI-generated art be eligible for copyright protection? | tech-ethics | 3 | Con | 67,173 | $0.265 | [`techethics-ai-art.md`](techethics-ai-art.md) |
| Is waking up at 5am the key to a productive life? | lifestyle | 3 | tie | 76,344 | $0.296 | [`lifestyle-morning-routine.md`](lifestyle-morning-routine.md) |
| Capitalism is, on balance, a force for good in society. | economics | 10 | Pro | 343,521 | $1.261 | [`capitalism.md`](capitalism.md) |

Each **Read it** link opens the human-readable transcript + verdict + cost table; the
matching machine-readable event log sits alongside it as `<run_id>.jsonl`. The
**Total tokens** / **Cost** columns are the actual billed figures reported in each
run's `## Cost & tokens` section. For a tidy one-row-per-run dataset across all four
runs (drift/nudge counts, latency, est. cost) see
[`dataset/runs_summary.csv`](dataset/runs_summary.csv) (documented in
[`dataset/README.md`](dataset/README.md)); the PRD §9 analysis of these runs lives in
[`../notebooks/analysis.ipynb`](../notebooks/analysis.ipynb).

The `capitalism` run is a **full 10-round** debate at the **default 150-word** message
limit — a complete exercise of the system's PRD default (PRD §2, §7). The original
three runs (`policy-congestion-pricing`, `techethics-ai-art`,
`lifestyle-morning-routine`) were instead run at a **reduced 3-4 rounds** with a
120-word limit purely to save real-API cost; see the section below.

## Reduced rounds for cost — the system supports the full 10

The original three runs (`policy-congestion-pricing`, `techethics-ai-art`,
`lifestyle-morning-routine`) were generated with a reduced round count (**4 rounds**
for the policy run, **3 rounds** for the other two) and a **120-word** message limit
(`--rounds {3,4} --max-words 120`) to keep total real-API cost to roughly a dollar
across all three. The `capitalism` run, by contrast, is a **full 10-round** debate at
the **default 150-word** limit (no reducing flags), so it demonstrates the system at
its PRD default end-to-end. This is *deliberate cost control*, not a limitation: the
system's default is the full **10 rounds × 150 words** (PRD §2, §7), and even a 3-4
round debate already exercises the entire mechanism — Pro/Con
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

uv run python scripts/generate_sample_runs.py --rounds 3 --max-words 120 \
    --run-id techethics-ai-art \
    --topic "Should AI-generated art be eligible for copyright protection?"

uv run python scripts/generate_sample_runs.py --rounds 3 --max-words 120 \
    --run-id lifestyle-morning-routine \
    --topic "Is waking up at 5am the key to a productive life?"

# Full 10-round debate at the default 150-word limit (no reducing flags):
uv run python scripts/generate_sample_runs.py \
    --run-id capitalism \
    --topic "Capitalism is, on balance, a force for good in society."
```

Every model call routes through the Epic-13 API gatekeeper inside the SDK; the
generator adds no direct external calls. Provider key is read from `.env` (never
committed).
