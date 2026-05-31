# Aggregated runs dataset

`runs_summary.csv` is the tidy, **one-row-per-run** dataset for the PRD §9 results
analysis (TASKS.md 14.1, issue #97). It is produced by reading every
`runs/<run_id>.jsonl` LOG event log and folding it into outcomes, per-side
drift/nudge counts, token/cost and latency totals.

Regenerate it (no API calls — it only reads the committed run files):

```bash
uv run python scripts/aggregate_runs.py
# or, explicitly:
uv run python scripts/aggregate_runs.py --runs-dir runs --out runs/dataset/runs_summary.csv
```

Non-debate LOG chatter files in `runs/` (`api.jsonl`, `models.jsonl`, …) carry no
`debate_setup` or `verdict` event and are skipped, so only real debates appear.

## Columns

| Column | Meaning |
| --- | --- |
| `run_id` | Run identifier (the `<run_id>.jsonl` file stem). |
| `topic` | Debate motion, from the `debate_setup` system event. |
| `rounds` | Highest 1-based round seen on a message event. |
| `winner` | `pro` / `con` / `tie` from the verdict (`n/a` if none). |
| `converged` | Whether the agents agreed (verdict `converged` flag). |
| `total_tokens` | Tokens summed over every `message` event. |
| `est_cost_usd` | **Estimated** cost: `total_tokens` priced at the configured debater model's input rate (`config/model_prices.json`). The JSONL has no input/output split or per-model id, so this is an approximation, not the billed cost — the exact per-model cost lives in each `<run_id>.md`. |
| `pro_messages` / `con_messages` | `message` events per side. |
| `pro_nudges` / `con_nudges` | Controller anti-sycophancy `nudge` events per side (drift/capture frequency, PRD §9). |
| `total_latency_ms` / `avg_latency_ms` | Latency summed / averaged over messages with a recorded latency. |
| `timeouts` / `retries` | Reliability counts across the run. |

## Schema source of truth

The column list, parsing and CSV writer live in
`packages/core/src/agent_debate/core/research/`. The dataset is stdlib-CSV only — no
data-frame dependency was added (parquet would have required pulling in
`pandas`/`pyarrow`, which are not workspace deps).
