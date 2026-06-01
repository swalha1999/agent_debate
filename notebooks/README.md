# notebooks/

Results-analysis notebooks for the debate experiment (PRD §9). All reusable
logic lives in the **tested** core module
[`agent_debate.core.research`](../packages/core/src/agent_debate/core/research) —
the notebooks stay thin (import the module, call pure functions, show tables), so
the analyses are covered by the unit tests rather than by hand-checking cells.

## `analysis.ipynb` (task 14.2)

Presents the four PRD §9 analyses over the committed `runs/<run_id>.jsonl` event
logs (aggregated by task 14.1 into `runs/dataset/runs_summary.csv`):

1. **Who-wins distribution** — counts of runs won per side (pro / con / tie).
2. **Agree-vs-disagree rate** — how often the agents converged (`converged` flag).
3. **Drift / nudge frequency per side** — how often the controller had to nudge a
   captured debater back to its assigned side. This is the direct evidence the
   anti-sycophancy design works (the committed sample run needed **0** nudges;
   the staged-drift detection path itself is exercised by the engine tests, 8.4).
4. **Tokens & latency** — per topic (run-level) and per round (parsed from the
   JSONL, since the run summary only carries run-level totals).

The notebook presents the analyses as **tables / printed summaries**. Charts are
the separate task **14.3**: `matplotlib`/`pandas` are not workspace dependencies,
so 14.2 deliberately stays dependency-free (stdlib + the core module only) and
leaves visualisation to 14.3.

### How to run

From the repo root, execute it in place (Jupyter is pulled in on the fly via
`uv run --with`, so no permanent dependency is added):

```bash
# Execute and write the results back into the notebook:
uv run --with jupyter --with nbclient jupyter nbconvert \
    --to notebook --execute --inplace notebooks/analysis.ipynb

# …or open it interactively:
uv run --with jupyter jupyter lab notebooks/analysis.ipynb
```

The runs directory is **not** hard-coded: the first cell resolves it from the LOG
package's `DEFAULT_RUNS_DIR` anchored to the repo root, so the notebook works
regardless of the kernel's working directory.

> The notebook is committed with **cleared outputs** (no embedded run output) so
> the repo never carries stale numbers or accidental secrets. Re-run it to
> regenerate the tables. After regenerating the dataset, refresh the CSV first:
>
> ```bash
> python scripts/aggregate_runs.py
> ```
