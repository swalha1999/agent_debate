"""The per-run summary value object for the runs dataset (task 14.1, PRD §9).

:class:`RunSummary` is one tidy row of the aggregated dataset — a single debate
run folded into outcomes (winner, converged), per-side message + nudge counts,
token/latency totals and reliability (timeout/retry) counts. The folding logic
lives next door in :mod:`agent_debate.core.research._parse`; this module only
holds the immutable shape so it stays well under the line cap.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

#: Sentinel winner for a run whose JSONL carried no ``verdict`` event.
NO_VERDICT = "n/a"


class RunSummary(BaseModel):
    """One row of the aggregated runs dataset (PRD §9 — one debate run).

    Attributes:
        run_id: Identifier of the run (the ``<run_id>.jsonl`` stem).
        topic: Debate motion, read from the ``debate_setup`` system event.
        rounds: Highest 1-based round seen on a message event.
        winner: ``pro`` / ``con`` / ``tie`` from the verdict (else ``n/a``).
        converged: Whether the agents agreed (verdict ``converged`` flag).
        total_tokens: Tokens summed over every ``message`` event.
        est_cost_usd: Total tokens priced at the configured model's input rate.
        pro_messages: Count of ``message`` events from the ``pro`` side.
        con_messages: Count of ``message`` events from the ``con`` side.
        pro_nudges: Count of controller ``nudge`` events aimed at ``pro``.
        con_nudges: Count of controller ``nudge`` events aimed at ``con``.
        total_latency_ms: Latency summed over every ``message`` event.
        avg_latency_ms: Mean per-message latency (``0.0`` when no messages).
        timeouts: Count of ``timeout`` events across the run.
        retries: Count of ``retry`` events across the run.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    topic: str = ""
    rounds: int = Field(ge=0, default=0)
    winner: str = NO_VERDICT
    converged: bool = False
    total_tokens: int = Field(ge=0, default=0)
    est_cost_usd: float = Field(ge=0.0, default=0.0)
    pro_messages: int = Field(ge=0, default=0)
    con_messages: int = Field(ge=0, default=0)
    pro_nudges: int = Field(ge=0, default=0)
    con_nudges: int = Field(ge=0, default=0)
    total_latency_ms: float = Field(ge=0.0, default=0.0)
    avg_latency_ms: float = Field(ge=0.0, default=0.0)
    timeouts: int = Field(ge=0, default=0)
    retries: int = Field(ge=0, default=0)

    @classmethod
    def empty(cls, run_id: str) -> RunSummary:
        """Return a zeroed summary for ``run_id`` (a run with no usable events)."""
        return cls(run_id=run_id)


__all__ = ["NO_VERDICT", "RunSummary"]
