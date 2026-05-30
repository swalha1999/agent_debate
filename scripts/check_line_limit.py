#!/usr/bin/env python
"""Enforce the 150-line-per-file guideline (PRD §3.2, TASKS.md 0.10).

Walks ``packages/**/*.py`` and counts *code* lines per file — excluding blank
lines, comment-only lines and triple-quoted docstring/string bodies — then
exits non-zero, listing every file whose code-line count exceeds the threshold.
Splitting (helpers/mixins/constants/models) is the mandated remedy, not
compression, so the count deliberately ignores comments and docstrings that
*aid* readability rather than penalising them.

The counting is token-accurate: Python's :mod:`tokenize` yields the line span
of every comment and string token, so we mark those source lines as non-code
and treat every remaining non-blank line as code. The threshold is a single
named constant (:data:`DEFAULT_MAX_LINES`) overridable on the command line, so
no magic number is scattered through the code (guideline §7.2). Output goes via
the stdlib ``logging`` module — the workspace LOG surface is still a skeleton at
this scaffold stage, so this build-time tool uses stdlib logging directly.
"""

from __future__ import annotations

import argparse
import logging
import tokenize
from pathlib import Path

#: Default maximum code lines per file (guideline §3.2). Single source of truth;
#: overridable via ``--max-lines`` so the threshold is never hard-coded inline.
DEFAULT_MAX_LINES = 150

#: Glob, relative to the repo root, for the source tree the gate covers.
PACKAGES_GLOB = "packages/**/*.py"

_LOG = logging.getLogger("check_line_limit")


#: Token types that carry no executable code on their own line. Everything
#: else (NAME, OP, NUMBER, KEYWORD, …) marks its line as real code.
_NON_CODE_TOKENS = frozenset(
    {
        tokenize.COMMENT,
        tokenize.STRING,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
    }
)


def count_code_lines(path: Path) -> int:
    """Return the number of code lines in ``path``.

    A physical line counts as code only when it bears at least one token that
    is *not* a comment, a string/docstring body, or pure layout (newline,
    indent/dedent). Tokenizing makes this exact: a line like ``x = "lit"`` is
    counted (it has a NAME/OP), while every interior line of a multi-line
    docstring carries only the STRING token and is excluded.
    """
    code_lines: set[int] = set()
    with path.open("rb") as handle:
        for tok in tokenize.tokenize(handle.readline):
            if tok.type in _NON_CODE_TOKENS:
                continue
            code_lines.add(tok.start[0])
    return len(code_lines)


def find_offenders(root: Path, max_lines: int) -> list[tuple[Path, int]]:
    """Return ``(path, code_lines)`` for every file over ``max_lines``."""
    offenders: list[tuple[Path, int]] = []
    for path in sorted(root.glob(PACKAGES_GLOB)):
        count = count_code_lines(path)
        if count > max_lines:
            offenders.append((path, count))
    return offenders


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repo root to scan (default: the repository containing this script).",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help=f"Maximum code lines per file (default: {DEFAULT_MAX_LINES}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Scan the tree and return a process exit code (0 = pass, 1 = offenders)."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args(argv)
    offenders = find_offenders(args.root, args.max_lines)
    if not offenders:
        _LOG.info("Line-limit check passed: no file exceeds %d code lines.", args.max_lines)
        return 0
    _LOG.error("Files exceeding %d code lines (guideline §3.2):", args.max_lines)
    for path, count in offenders:
        _LOG.error("  %s — %d code lines", path, count)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
