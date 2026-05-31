"""Render a :class:`CostBreakdown` as a markdown cost table (task 15.2, PRD §10).

The docs/result surface a per-run (or aggregate) cost table: one row per model
(``input tokens | output tokens | $input | $output | $total``) plus an overall
total row. This module is the pure renderer — no pricing logic, no I/O — so the
same :class:`~agent_debate.core.pricing.breakdown.CostBreakdown` feeds the API,
CLI and the docs cost report unchanged.
"""

from __future__ import annotations

from agent_debate.core.pricing.breakdown import CostBreakdown, ModelCostRow

#: Column headers, in render order. Identifiers (not data), kept in one place.
_HEADERS = ("Model", "Input tokens", "Output tokens", "$ Input", "$ Output", "$ Total")

#: Label for the grand-total row.
_OVERALL_LABEL = "Overall"

#: USD values are rendered to this many decimal places (cents-and-below).
_USD_DECIMALS = 6


def _usd(value: float) -> str:
    """Format a USD figure with a leading ``$`` and fixed precision."""
    return f"${value:.{_USD_DECIMALS}f}"


def _row_cells(row: ModelCostRow) -> tuple[str, ...]:
    """The six rendered cells of one per-model row."""
    return (
        row.model,
        str(row.input_tokens),
        str(row.output_tokens),
        _usd(row.input_cost),
        _usd(row.output_cost),
        _usd(row.total_cost),
    )


def _overall_cells(breakdown: CostBreakdown) -> tuple[str, ...]:
    """The six rendered cells of the grand-total row."""
    input_cost = sum(r.input_cost for r in breakdown.rows)
    output_cost = sum(r.output_cost for r in breakdown.rows)
    return (
        _OVERALL_LABEL,
        str(breakdown.input_tokens),
        str(breakdown.output_tokens),
        _usd(input_cost),
        _usd(output_cost),
        _usd(breakdown.total_cost),
    )


def _line(cells: tuple[str, ...]) -> str:
    """Join ``cells`` into one ``| a | b | … |`` markdown table row."""
    return "| " + " | ".join(cells) + " |"


def format_cost_table(breakdown: CostBreakdown) -> str:
    """Render ``breakdown`` as a markdown cost table (per-model rows + overall).

    Columns: model, input tokens, output tokens, $input, $output, $total. A final
    ``Overall`` row carries the grand totals. Prices are whatever priced the
    breakdown (config-driven), never recomputed here.
    """
    separator = tuple("---" for _ in _HEADERS)
    lines = [_line(_HEADERS), _line(separator)]
    lines.extend(_line(_row_cells(row)) for row in breakdown.rows)
    lines.append(_line(_overall_cells(breakdown)))
    return "\n".join(lines)


__all__ = ["format_cost_table"]
