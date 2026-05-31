"""Chart helpers over the 14.2 analyses (task 14.3, issue #99, PRD §9).

PRD §9 wants *interpreted visualizations*, not just numbers. This module turns
the 14.2 analysis outputs (:mod:`agent_debate.core.research.analysis`) into saved
PNG figures — it reuses those pure functions rather than re-aggregating:

* :func:`save_who_wins_chart` — who-wins distribution bar chart.
* :func:`save_agree_disagree_chart` — converged (agree) vs not (disagree).
* :func:`save_nudges_chart` — per-side drift/nudge totals (anti-sycophancy).
* :func:`save_round_tokens_chart` — tokens & latency per round for one run.
* :func:`save_all_figures` — convenience wrapper writing every chart.

No hard-coded paths (the out dir is always a caller argument) and no hard-coded
data — the figures are derived from the supplied summaries/round metrics. The
matplotlib import is **guarded**: it lives inside :func:`_pyplot` so importing
``agent_debate.core`` never fails when the optional ``viz`` extra is absent;
only actually drawing a chart needs it. A non-interactive (Agg) backend is forced
so rendering works headless on CI/Windows. No external API calls — read-only.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agent_debate.core.research._summary import RunSummary
from agent_debate.core.research.analysis import (
    RoundMetric,
    agree_vs_disagree,
    nudges_per_side,
    who_wins,
)

if TYPE_CHECKING:
    from matplotlib.figure import Figure

_DPI = 120
_MISSING = (
    "matplotlib is required to render charts — install the viz extra: "
    "`uv sync --group viz` (or the dev group)."
)


def _pyplot() -> Any:
    """Return the pyplot module with the headless Agg backend forced.

    The import is deferred (not module-level) so ``agent_debate.core`` imports
    fine without the optional ``viz`` extra; only drawing a chart needs it.

    :raises ImportError: With install guidance when matplotlib is absent.
    """
    try:
        import matplotlib
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(_MISSING) from exc
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _save(fig: Figure, out_dir: Path | str, name: str) -> Path:
    """Write ``fig`` as ``<out_dir>/<name>.png`` and close it; return the path."""
    plt = _pyplot()
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    fig.savefig(path, dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def save_who_wins_chart(summaries: Iterable[RunSummary], out_dir: Path | str) -> Path:
    """Save the who-wins distribution as a bar chart; return the PNG path."""
    plt = _pyplot()
    dist = who_wins(summaries)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(list(dist.keys()), list(dist.values()), color="#4c72b0")
    ax.set_title("Who-wins distribution across topics")
    ax.set_xlabel("Winner")
    ax.set_ylabel("Runs")
    return _save(fig, out_dir, "who_wins")


def save_agree_disagree_chart(summaries: Iterable[RunSummary], out_dir: Path | str) -> Path:
    """Save the agree-vs-disagree outcome split as a bar chart; return the path."""
    plt = _pyplot()
    rates = agree_vs_disagree(summaries)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["agree", "disagree"], [rates["agree"], rates["disagree"]], color=["#55a868", "#c44e52"])
    ax.set_title(f"Agree vs disagree (agree rate = {rates['agree_rate']:.0%})")
    ax.set_ylabel("Runs")
    return _save(fig, out_dir, "agree_vs_disagree")


def save_nudges_chart(summaries: Iterable[RunSummary], out_dir: Path | str) -> Path:
    """Save per-side drift/nudge totals as a bar chart (anti-sycophancy evidence)."""
    plt = _pyplot()
    stats = nudges_per_side(summaries)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["pro", "con"], [stats.pro_total, stats.con_total], color="#8172b3")
    ax.set_title(f"Controller nudges per side (total = {stats.total})")
    ax.set_xlabel("Side")
    ax.set_ylabel("Nudges")
    return _save(fig, out_dir, "nudges_per_side")


def save_round_tokens_chart(
    rounds: list[RoundMetric], out_dir: Path | str, *, run_id: str
) -> Path | None:
    """Save per-round tokens (bars) and latency (line) for one run.

    :returns: The PNG path, or ``None`` when there are no rounds to plot.
    """
    if not rounds:
        return None
    plt = _pyplot()
    nums = [r.round for r in rounds]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(nums, [r.tokens for r in rounds], color="#4c72b0", label="tokens")
    ax.set_xlabel("Round")
    ax.set_ylabel("Tokens")
    twin = ax.twinx()
    twin.plot(nums, [r.latency_ms for r in rounds], color="#dd8452", marker="o", label="latency ms")
    twin.set_ylabel("Latency (ms)")
    ax.set_title(f"Tokens & latency per round — {run_id}")
    return _save(fig, out_dir, f"round_tokens_{run_id}")


def save_all_figures(
    summaries: Iterable[RunSummary],
    out_dir: Path | str,
    *,
    rounds: list[RoundMetric] | None = None,
    run_id: str = "",
) -> list[Path]:
    """Write every §9 chart to ``out_dir``; return the saved paths in order.

    The per-round chart is only added when ``rounds`` are supplied.
    """
    rows = list(summaries)
    paths = [
        save_who_wins_chart(rows, out_dir),
        save_agree_disagree_chart(rows, out_dir),
        save_nudges_chart(rows, out_dir),
    ]
    if rounds:
        round_path = save_round_tokens_chart(rounds, out_dir, run_id=run_id)
        if round_path is not None:
            paths.append(round_path)
    return paths


__all__ = [
    "save_agree_disagree_chart",
    "save_all_figures",
    "save_nudges_chart",
    "save_round_tokens_chart",
    "save_who_wins_chart",
]
