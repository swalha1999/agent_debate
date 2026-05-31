"""Unit tests for post-generation word-limit enforcement (TASKS.md 5.7, issue #44).

PRD §5.2 / §7: each debate message must stay within the configured word limit
(``MAX_WORDS``). The *prompt* side (system prompt + per-turn anchor) already
instructs ``<= max_words``; THIS module verifies it **after** generation — if a
message exceeds ``max_words`` it is trimmed to exactly ``max_words`` words and a
violation event is logged via the LOG package.

Written TDD-first (red before green). ``max_words`` is supplied as a parameter
(config-driven from :class:`~agent_debate.core.Settings`, never hard-coded), and
the word-counting rule (split on whitespace) is asserted directly.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_debate.core.agents import count_words, enforce_word_limit
from agent_debate.core.constants import WORD_LIMIT_LOG_EVENT_TYPE


def test_count_words_splits_on_whitespace() -> None:
    """Word count = number of whitespace-separated tokens (any whitespace run)."""
    assert count_words("one two three") == 3
    assert count_words("  leading\tand\ntrailing  ") == 3
    assert count_words("single") == 1


def test_count_words_empty_is_zero() -> None:
    """Empty / whitespace-only text has zero words."""
    assert count_words("") == 0
    assert count_words("   \t\n ") == 0


def test_within_limit_returned_unchanged_no_violation() -> None:
    """A message under the limit is returned verbatim with ``violated=False``."""
    text = "one two three four five"
    result = enforce_word_limit(text, max_words=10)
    assert result.text == text
    assert result.violated is False
    assert result.original_words == 5


def test_exactly_at_limit_not_violated() -> None:
    """A message of exactly ``max_words`` words is not a violation (edge case)."""
    text = "a b c d e"
    result = enforce_word_limit(text, max_words=5)
    assert result.text == text
    assert result.violated is False


def test_empty_string_not_violated() -> None:
    """An empty message is within any limit and is returned unchanged."""
    result = enforce_word_limit("", max_words=5)
    assert result.text == ""
    assert result.violated is False
    assert result.original_words == 0


def test_over_limit_is_trimmed_to_max_words() -> None:
    """An over-limit message is trimmed to EXACTLY ``max_words`` words."""
    text = "one two three four five six seven"
    result = enforce_word_limit(text, max_words=3)
    assert count_words(result.text) == 3
    assert result.text == "one two three"
    assert result.violated is True
    assert result.original_words == 7


def test_violation_logged_as_chosen_event_type(tmp_path: Path) -> None:
    """An over-limit message logs the chosen event type with the limit payload."""
    runs_dir = Path(str(tmp_path))
    enforce_word_limit(
        "one two three four five",
        max_words=2,
        run_id="run-5-7",
        runs_dir=runs_dir,
    )
    lines = (runs_dir / "run-5-7.jsonl").read_text().splitlines()
    events = [json.loads(line) for line in lines]
    violations = [e for e in events if e["event_type"] == WORD_LIMIT_LOG_EVENT_TYPE]
    assert violations, "expected a word-limit violation event"
    payload = violations[0]["payload"]
    assert payload["violation"] == "word_limit"
    assert payload["words"] == 5
    assert payload["limit"] == 2
    assert payload["trimmed"] is True


def test_within_limit_logs_no_violation(tmp_path: Path) -> None:
    """A within-limit message must NOT emit any violation event."""
    runs_dir = Path(str(tmp_path))
    enforce_word_limit(
        "one two",
        max_words=5,
        run_id="run-5-7-clean",
        runs_dir=runs_dir,
    )
    log_file = runs_dir / "run-5-7-clean.jsonl"
    if not log_file.exists():
        return
    events = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert not [e for e in events if e["event_type"] == WORD_LIMIT_LOG_EVENT_TYPE]


def test_no_run_id_skips_logging_but_still_trims(tmp_path: Path) -> None:
    """Without a ``run_id`` the helper still trims; it just does not log."""
    result = enforce_word_limit("a b c d", max_words=2)
    assert result.text == "a b"
    assert result.violated is True
    assert not list(Path(str(tmp_path)).glob("*.jsonl"))
