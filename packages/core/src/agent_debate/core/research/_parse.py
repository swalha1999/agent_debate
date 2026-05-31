"""Fold a run's JSONL LOG events into a :class:`RunSummary` (task 14.1, PRD §9).

Reads the per-run event log written by the LOG package (one JSON object per line:
``run_id`` / ``round`` / ``agent`` / ``event_type`` / ``payload`` / ``tokens`` /
``latency_ms``) and tallies outcomes, per-side counts, tokens and latency. Cost is
*estimated*: the JSONL carries only a combined per-message ``tokens`` count (no
input/output split or model id), so we price the total at the configured model's
input rate via :func:`agent_debate.core.pricing.compute_cost` — config-driven, no
hard-coded price. Pricing the dominant input bucket keeps the estimate close.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from agent_debate.core.pricing import PriceTable, compute_cost
from agent_debate.core.research._summary import NO_VERDICT, RunSummary
from agent_debate.core.settings import get_settings

_SETUP_EVENT = "debate_setup"


def _iter_events(lines: Iterable[str]) -> Iterable[dict[str, object]]:
    """Yield each non-blank line parsed as a JSON object (blanks are skipped)."""
    for line in lines:
        text = line.strip()
        if text:
            yield json.loads(text)


def _winner_side(payload: dict[str, object]) -> str:
    """Map a verdict ``winner`` value to the ``pro``/``con``/``tie`` side label."""
    winner = payload.get("winner")
    return str(winner) if isinstance(winner, str) else NO_VERDICT


def parse_run(
    run_id: str,
    lines: Iterable[str],
    *,
    price_table: PriceTable | None = None,
) -> RunSummary:
    """Fold one run's JSONL ``lines`` into a tidy :class:`RunSummary`.

    :param run_id: Identifier reported on the summary (the file stem).
    :param lines: Iterable of JSONL event strings (the run's event log).
    :param price_table: Price table for the cost estimate; the repo-root config
        table is loaded when ``None`` (the model id comes from settings).
    """
    acc = _Accumulator()
    for event in _iter_events(lines):
        acc.consume(event)
    model = get_settings().debater_model
    cost = compute_cost(model, acc.total_tokens, 0, price_table)
    return acc.finish(run_id, cost)


def is_debate_run(lines: Iterable[str]) -> bool:
    """Return whether ``lines`` describe an actual debate (has a setup or verdict).

    The runs directory also holds package LOG chatter files (``api.jsonl`` …) whose
    lines are plain debug records, not :class:`~agent_debate.log.LogEvent` debate
    events. Those carry neither a ``debate_setup`` system event nor a ``verdict``,
    so this filter cleanly excludes them from the dataset.
    """
    for event in _iter_events(lines):
        event_type = event.get("event_type")
        if event_type == "verdict":
            return True
        payload = event.get("payload")
        if isinstance(payload, dict) and payload.get("event") == _SETUP_EVENT:
            return True
    return False


class _Accumulator:
    """Mutable tally of a single run's events, frozen into a :class:`RunSummary`."""

    def __init__(self) -> None:
        self.topic = ""
        self.rounds = 0
        self.winner = NO_VERDICT
        self.converged = False
        self.total_tokens = 0
        self.messages = {"pro": 0, "con": 0}
        self.nudges = {"pro": 0, "con": 0}
        self.total_latency = 0.0
        self.message_count = 0
        self.timeouts = 0
        self.retries = 0

    def consume(self, event: dict[str, object]) -> None:
        """Route one event to the matching tally by its ``event_type``."""
        handler = _HANDLERS.get(str(event.get("event_type")))
        if handler is not None:
            handler(self, event)

    def finish(self, run_id: str, cost: float) -> RunSummary:
        """Freeze the running tally into the immutable summary row."""
        avg = self.total_latency / self.message_count if self.message_count else 0.0
        return RunSummary(
            run_id=run_id,
            topic=self.topic,
            rounds=self.rounds,
            winner=self.winner,
            converged=self.converged,
            total_tokens=self.total_tokens,
            est_cost_usd=cost,
            pro_messages=self.messages["pro"],
            con_messages=self.messages["con"],
            pro_nudges=self.nudges["pro"],
            con_nudges=self.nudges["con"],
            total_latency_ms=self.total_latency,
            avg_latency_ms=avg,
            timeouts=self.timeouts,
            retries=self.retries,
        )


def _on_message(acc: _Accumulator, event: dict[str, object]) -> None:
    """Tally a ``message`` event: per-side count, tokens, latency and round."""
    side = str(event.get("agent"))
    if side in acc.messages:
        acc.messages[side] += 1
    tokens = event.get("tokens")
    if isinstance(tokens, int):
        acc.total_tokens += tokens
    latency = event.get("latency_ms")
    if isinstance(latency, (int, float)):
        acc.total_latency += float(latency)
        acc.message_count += 1
    round_no = event.get("round")
    if isinstance(round_no, int):
        acc.rounds = max(acc.rounds, round_no)


def _on_nudge(acc: _Accumulator, event: dict[str, object]) -> None:
    """Tally a ``nudge`` against the side it targets (payload ``side`` or agent)."""
    payload = event.get("payload")
    side = payload.get("side") if isinstance(payload, dict) else None
    target = str(side if side is not None else event.get("agent"))
    if target in acc.nudges:
        acc.nudges[target] += 1


def _on_system(acc: _Accumulator, event: dict[str, object]) -> None:
    """Capture the debate topic from the ``debate_setup`` system event."""
    payload = event.get("payload")
    if isinstance(payload, dict) and payload.get("event") == _SETUP_EVENT:
        acc.topic = str(payload.get("topic", ""))


def _on_verdict(acc: _Accumulator, event: dict[str, object]) -> None:
    """Capture the winner and convergence flag from the ``verdict`` event."""
    payload = event.get("payload")
    if isinstance(payload, dict):
        acc.winner = _winner_side(payload)
        acc.converged = bool(payload.get("converged", False))


def _on_timeout(acc: _Accumulator, _event: dict[str, object]) -> None:
    """Increment the run's timeout counter."""
    acc.timeouts += 1


def _on_retry(acc: _Accumulator, _event: dict[str, object]) -> None:
    """Increment the run's retry counter."""
    acc.retries += 1


_HANDLERS = {
    "message": _on_message,
    "nudge": _on_nudge,
    "system": _on_system,
    "verdict": _on_verdict,
    "timeout": _on_timeout,
    "retry": _on_retry,
}

__all__ = ["is_debate_run", "parse_run"]
