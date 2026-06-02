# Sample debate runs

This folder holds **committed sample debate runs** so the teacher can review real
debates end-to-end (PRD §11, TASKS.md 12.5). Each run lives in its own
subdirectory `<run_id>/` containing two files:

- `<run_id>/<run_id>.jsonl` — the machine-readable per-run event log written by
  the LOG package (PRD §5.8): every `message` / `tool_call` / `nudge` /
  `timeout` / `retry` / `verdict` / `system` event, with `run_id`, `round`,
  `agent`, `tokens`, `latency_ms`. Secrets are redacted by the LOG redactor
  before either sink.
- `<run_id>/<run_id>.md` — a human-readable rendering of the same run: the
  round-grouped transcript, the closing discussion, the controller's
  anti-sycophancy nudges, the final verdict, and the per-model cost-breakdown
  table. Rendered by `agent_debate.core.write_run_markdown` (which reuses the
  existing `format_cost_table` — no duplicated pricing/markdown).

## The committed run

This run was **generated on the topic+system-prompt-fixed engine** (after the
two fixes in #202 — inject the debate topic into the debater context — and #203 —
actually deliver the agent system prompt to the model on the `message_history`
path). The debaters argue the stated motion and rebut each other's actual words.

The repo keeps **five committed sample debates**: a full 10-round `capitalism` run at
the PRD default, plus four 5-round debates (`four-day-work-week`, `online-education`,
`nuclear-energy`, and `social-media-ban`). Three earlier reduced-round sample debates
were removed to avoid presenting them as current evidence.

> **⚠️ Rounds & cost (HW2 requirements §8.7).** The exercise/PRD default is **10 rounds
> per side**. The **`capitalism`** debate runs the **full 10 rounds** to demonstrate that
> default end-to-end. The **other four debates use 5 rounds instead of 10 to save API
> cost** — the budget reduction the HW2 requirements explicitly permit (§8.7: *reducing
> from 10 pings to 5 is allowed provided it is stated explicitly in the README, and does
> not reduce the grade*). The system still runs the full 10 rounds by default; the
> reduction is a per-run CLI flag only (`--rounds 5`). A 5-round debate still exercises
> the entire mechanism — Pro/Con alternation, mutual rebuttal, the controller
> drift-check/nudge path, the closing discussion, the verdict, and the cost/token
> breakdown.

| Topic | Kind | Rounds | Winner | Total tokens | Cost (USD) | Read it |
| --- | --- | --- | --- | --- | --- | --- |
| Capitalism is, on balance, a force for good in society. | economics | 10 | Pro | 343,521 | $1.261 | [`capitalism/capitalism.md`](capitalism/capitalism.md) |
| A four-day work week should become the global standard | policy | 5 | Pro | 146,555 | $0.566 | [`four-day-work-week/four-day-work-week.md`](four-day-work-week/four-day-work-week.md) |
| Online education is superior to traditional classroom learning | education | 5 | Con | 140,898 | $0.544 | [`online-education/online-education.md`](online-education/online-education.md) |
| Nuclear energy is essential for solving the climate crisis | energy | 5 | Con | 170,851 | $0.652 | [`nuclear-energy/nuclear-energy.md`](nuclear-energy/nuclear-energy.md) |
| Children under 16 should be banned from social media | society/tech | 5 | Pro | 146,356 | $0.564 | [`social-media-ban/social-media-ban.md`](social-media-ban/social-media-ban.md) |

The **Read it** link opens the human-readable transcript + verdict + cost table; the
matching machine-readable event log sits alongside it as `<run_id>/<run_id>.jsonl`. The
**Total tokens** / **Cost** columns are the actual billed figures reported in the
run's `## Cost & tokens` section. For the tidy one-row-per-run dataset
(drift/nudge counts, latency, est. cost) see
[`dataset/runs_summary.csv`](dataset/runs_summary.csv) (documented in
[`dataset/README.md`](dataset/README.md)); the PRD §9 analysis of this run lives in
[`../notebooks/analysis.ipynb`](../notebooks/analysis.ipynb).

The `capitalism` run is a **full 10-round** debate at the **default 150-word** message
limit — a complete exercise of the system's PRD default (PRD §2, §7). It exercises
the entire mechanism — Pro/Con alternation, rebuttal of the opponent's actual words,
the controller drift-check / nudge path, the closing discussion, the debate-derived
verdict, and the token/cost-breakdown table.

## How it was generated

```bash
# Full 10-round debate at the default 150-word limit (no reducing flags):
uv run python scripts/generate_sample_runs.py \
    --run-id capitalism \
    --topic "Capitalism is, on balance, a force for good in society."
```

The generator also supports reduced-cost runs via `--rounds N --max-words W` if a
shorter debate is wanted; the committed sample deliberately uses the full default.

Every model call routes through the Epic-13 API gatekeeper inside the SDK; the
generator adds no direct external calls. Provider key is read from `.env` (never
committed).
