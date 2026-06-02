# Debate results — interpreted visualizations (PRD §9, task 14.3)

These charts visualize the four PRD §9 analyses over the committed sample runs
(`runs/dataset/runs_summary.csv`, **n = 5** debates — the full 10-round
`capitalism` run, the 5-round `four-day-work-week` policy run, the 5-round
`online-education` education debate, the 5-round `nuclear-energy` energy
debate, and the 5-round `social-media-ban` society/tech debate). They are
regenerated from the durable `runs/<run_id>.jsonl` logs by reusing the 14.2
analysis functions (`agent_debate.core.research.analysis`) — no aggregation is
re-implemented here.

Regenerate with the `viz` extra (matplotlib):

```bash
uv sync --group viz
uv run --group viz python scripts/generate_figures.py
```

PRD §9 asks for *interpretation*, not just numbers, with an eye on whether the
anti-sycophancy design holds. Each chart below is read in that light. The
empirical basis is n = 5 runs (an economics topic at 10 rounds, a policy
topic at 5 rounds, an education topic at 5 rounds, an energy topic at 5
rounds, and a society/tech topic at 5 rounds), so these illustrate tendencies
across five debates rather than statistical trends across many.

## 1. Who-wins distribution

![Who-wins distribution](who_wins.png)

The five committed runs split **pro 3 / con 2**: `capitalism`, `four-day-work-week`,
and `social-media-ban` were won by **pro**; `online-education` and `nuclear-energy`
were won by **con**.
With only five runs this is a small sample — it does not establish a structural
favourite for either side. The verdict mechanism itself (side-anchoring +
independent contexts, §5, plus the controller's debate-derived judgement) is
what guards against one persona dominating; that logic is exercised by the
engine tests, not inferred from a five-run chart.

## 2. Agree vs disagree

![Agree vs disagree](agree_vs_disagree.png)

**0 % convergence across all five runs** — all debates ended in disagreement
(`converged = False`). This is the *expected* result for an adversarial debate
format: Pro and Con are anchored to opposing sides and instructed not to
capitulate, so genuine agreement should be rare. A high agree rate here would
be a red flag for sycophancy/capture (one side rolling over). Zero convergence
across all five runs is consistent with the format holding the adversarial tension
it was designed for, not a defect.

## 3. Controller nudges per side (anti-sycophancy evidence)

![Nudges per side](nudges_per_side.png)

**0 nudges on both sides across all five runs.** The controller's drift/nudge
mechanism (§8) corrects a debater that gets captured by its opponent and
abandons its assigned side. In none of the five runs did it have to intervene: the side
anchors held on their own. That is the headline anti-sycophancy result — the
design keeps each agent on-side *without* needing the safety net. This does
not mean the nudge path is untested: the staged-drift detection/correction
logic is exercised directly by the engine tests (task 8.4); all five real runs
simply did not trip it. With n = 5 we read this as "the anchoring held on
all topics tested", not as proof the controller never nudges.

## 4. Tokens & latency per round

![Tokens and latency per round](round_tokens_capitalism.png)

For the longest debate (`capitalism`, 10 rounds), per-round **tokens rise from
~14k in round 0 to ~51k by round 9**, with latency tracking it (round 0 ≈ near
zero to round 9 ≈ 99 s). The growth is the cost signature PRD §10 predicts:
every turn re-sends the side anchor plus the adversarial relay of the opponent's
last message *and* the lengthening transcript, so input tokens grow faster than
linearly in round count. The practical implication is direct — **cost scales
super-linearly with `ROUNDS`**, so lowering `ROUNDS`/`MAX_WORDS` (or routing
debaters to a cheaper model) is the cheapest lever, and a `BUDGET_USD` cap flags
a runaway long debate early. This is why the 10-round capitalism run cost ~$1.03;
the cost model (notebook §6) projects a 3-round / 120-word debate at only ~$0.31,
illustrating how steeply cost scales with `ROUNDS`.
