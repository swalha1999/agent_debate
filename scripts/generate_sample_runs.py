#!/usr/bin/env python
"""Generate sample debate runs and commit them under ``runs/`` (TASKS.md 12.5).

Runs one or more debates through the SDK :class:`~agent_debate.core.DebateEngine`
— which writes the machine-readable per-run event log ``runs/<run_id>.jsonl`` via
the LOG package — and then renders the readable companion ``runs/<run_id>.md``
(transcript + nudges + verdict + cost table) via
:func:`~agent_debate.core.write_run_markdown`. This is the evidence the teacher
reviews (PRD §11, §10).

Every model call routes through the Epic-13 API gatekeeper inside the engine; this
script adds no direct external calls. Rounds / word-limit / topics are CLI args (no
hard-coded debate parameters) so a cheap, reduced-rounds sample run is one flag away
from the full 10-round default the system supports.

Usage (from the repo root, with ANTHROPIC_API_KEY in ``.env``)::

    uv run python scripts/generate_sample_runs.py --rounds 4 --max-words 120 \
        --topic "..." --topic "..." --topic "..."

A stable ``--run-id`` (or auto uuid4) names BOTH output files. Output is via the
stdlib logger — this build-time tool predates needing the structured LOG surface
for its own console chatter (the debate itself logs through LOG).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid

from agent_debate.core import DebateEngine, Settings, get_settings, write_run_markdown
from agent_debate.log import DEFAULT_RUNS_DIR

# The pretty console LOG sink prints debate text that may contain emoji/non-Latin
# characters; on a legacy Windows code page (e.g. cp1255) ``print`` raises
# UnicodeEncodeError. Force UTF-8 on the streams so a real run never dies on a
# console-encoding quirk (the JSONL/Markdown files are UTF-8 already).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(message)s")
_LOG = logging.getLogger("generate_sample_runs")


def _load_key_from_env_file() -> None:
    """Bridge the ``.env`` provider key into ``os.environ`` for pydantic-ai.

    A blank/absent ``ANTHROPIC_API_KEY`` *process* variable otherwise shadows the
    ``.env`` value (env wins over env_file in pydantic-settings), leaving the
    Anthropic provider — which reads ``ANTHROPIC_API_KEY`` from the environment —
    without a key. We clear the blank shadow, let :class:`Settings` read ``.env``,
    and export the resolved key. No key is ever hard-coded; it stays in ``.env``.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        get_settings.cache_clear()
    key = get_settings().anthropic_api_key
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key


def _resolve_settings(rounds: int | None, max_words: int | None) -> Settings:
    """Return process settings with only the supplied debate knobs overridden."""
    _load_key_from_env_file()
    base = get_settings()
    overrides: dict[str, object] = {}
    if rounds is not None:
        overrides["rounds"] = rounds
    if max_words is not None:
        overrides["max_words"] = max_words
    return base.model_copy(update=overrides) if overrides else base


def _generate_one(engine: DebateEngine, topic: str, run_id: str) -> None:
    """Run one debate (writes the JSONL) then render the readable ``.md`` beside it."""
    _LOG.info("Running debate run_id=%s topic=%r", run_id, topic)
    result = engine.run(topic, run_id=run_id)
    md_path = write_run_markdown(result, run_id=run_id, runs_dir=DEFAULT_RUNS_DIR)
    cost = result.totals.cost_usd
    winner = result.verdict.winner if result.verdict is not None else "n/a"
    _LOG.info(
        "Done run_id=%s winner=%s tokens=%d cost=$%.6f md=%s",
        run_id,
        winner,
        result.totals.total_tokens,
        cost,
        md_path,
    )


def _parse_args() -> argparse.Namespace:
    """Parse the topics + reduced-rounds knobs (all debate params come from here)."""
    parser = argparse.ArgumentParser(description="Generate sample debate runs under runs/.")
    parser.add_argument(
        "--topic", action="append", required=True, help="A debate topic (repeatable)."
    )
    parser.add_argument("--rounds", type=int, default=None, help="Rounds per side (else config).")
    parser.add_argument("--max-words", type=int, default=None, help="Word limit per message.")
    parser.add_argument("--run-id", default=None, help="Run id for a single topic (else uuid4).")
    return parser.parse_args()


def main() -> None:
    """Generate every requested sample run, writing the JSONL + Markdown pair each."""
    args = _parse_args()
    settings = _resolve_settings(args.rounds, args.max_words)
    engine = DebateEngine(settings=settings)
    for index, topic in enumerate(args.topic):
        run_id = args.run_id if args.run_id and len(args.topic) == 1 else uuid.uuid4().hex[:12]
        _generate_one(engine, topic, run_id)
        _LOG.info("Completed %d/%d", index + 1, len(args.topic))


if __name__ == "__main__":
    main()
