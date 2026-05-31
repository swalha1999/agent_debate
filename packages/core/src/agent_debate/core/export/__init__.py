"""Readable run export — render a :class:`DebateResult` as ``runs/<run_id>.md`` (12.5).

PRD §10/§11 + TASKS.md 12.5: alongside the machine-readable per-run event log
(``runs/<run_id>.jsonl``, written by the LOG package) the teacher reviews a
*readable* ``runs/<run_id>.md`` carrying the transcript, the controller nudges, the
verdict and the cost-breakdown table. This subpackage owns that rendering. The cost
table reuses :func:`~agent_debate.core.pricing.format_cost_table` verbatim — no
pricing or markdown is duplicated. Re-exports the public surface.
"""

from __future__ import annotations

from agent_debate.core.export.markdown import render_run_markdown, write_run_markdown

__all__ = ["render_run_markdown", "write_run_markdown"]
