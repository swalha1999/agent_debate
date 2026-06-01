"""Runs research/analysis surface — aggregate saved runs into a dataset (task 14.1).

PRD §9 treats the debate system as our experiment: saved ``runs/<run_id>.jsonl``
LOG event logs are folded into a tidy one-row-per-run dataset (outcomes, per-side
drift/nudge counts, tokens, latency) for the §9 results analysis. This package is
the reusable core: :func:`parse_run` / :func:`aggregate_runs` build the
:class:`RunSummary` rows and :func:`write_dataset` serialises them to CSV. The thin
CLI lives in ``scripts/aggregate_runs.py``. No external API calls — read-only.
"""

from __future__ import annotations

from agent_debate.core.research._aggregate import RUN_GLOB, aggregate_runs
from agent_debate.core.research._dataset import (
    DATASET_COLUMNS,
    summary_to_row,
    write_dataset,
)
from agent_debate.core.research._parse import parse_run
from agent_debate.core.research._summary import NO_VERDICT, RunSummary
from agent_debate.core.research.analysis import (
    NudgeStats,
    RoundMetric,
    TopicMetric,
    agree_vs_disagree,
    nudges_per_side,
    round_metrics,
    tokens_latency_per_topic,
    who_wins,
)
from agent_debate.core.research.params import (
    DEFAULT_OUTPUT_FRACTION,
    EmpiricalPoint,
    GridCell,
    ModelCostChoice,
    TokenModel,
    empirical_points,
    fit_token_model,
    model_choice_table,
    project_grid,
)
from agent_debate.core.research.viz import (
    save_agree_disagree_chart,
    save_all_figures,
    save_nudges_chart,
    save_round_tokens_chart,
    save_who_wins_chart,
)

__all__ = [
    "DATASET_COLUMNS",
    "DEFAULT_OUTPUT_FRACTION",
    "NO_VERDICT",
    "RUN_GLOB",
    "EmpiricalPoint",
    "GridCell",
    "ModelCostChoice",
    "NudgeStats",
    "RoundMetric",
    "RunSummary",
    "TokenModel",
    "TopicMetric",
    "aggregate_runs",
    "agree_vs_disagree",
    "empirical_points",
    "fit_token_model",
    "model_choice_table",
    "nudges_per_side",
    "parse_run",
    "project_grid",
    "round_metrics",
    "save_agree_disagree_chart",
    "save_all_figures",
    "save_nudges_chart",
    "save_round_tokens_chart",
    "save_who_wins_chart",
    "summary_to_row",
    "tokens_latency_per_topic",
    "who_wins",
    "write_dataset",
]
