"""Embed a per-run round-tokens chart into that run's Markdown transcript.

A debate run is committed as a pair: the machine-readable ``<run_id>.jsonl``
event log and the readable ``<run_id>.md`` transcript, both inside
``runs/<run_id>/``. This module renders a tokens-per-round chart beside the
transcript and splices an image section into the ``.md`` so the readable
artifact is self-contained.

:func:`embed_round_chart_section` is **idempotent**: the section is inserted
when missing and replaced (not duplicated) when already present. The image
reference is a bare filename — a same-folder relative path — since the PNG sits
next to the ``.md``. No external API calls; this only reads/writes local files.
"""

from __future__ import annotations

import re

#: Heading that marks the embedded chart section in a run's Markdown transcript.
SECTION_HEADING = "## Round-by-round token usage"

#: Matches an existing chart section (heading through the image line and any
#: trailing blank lines) so a re-run replaces it instead of appending a copy.
_SECTION_RE = re.compile(
    r"\n*" + re.escape(SECTION_HEADING) + r"\n+!\[[^\]]*\]\([^)]*\)\n*",
    re.DOTALL,
)


def round_chart_section(image_filename: str) -> str:
    """Return the Markdown chart section referencing ``image_filename``.

    :param image_filename: Bare PNG filename (a same-folder relative path).
    :returns: The ``## Round-by-round token usage`` section text.
    """
    return f"{SECTION_HEADING}\n\n![Round-by-round token usage]({image_filename})\n"


def embed_round_chart_section(markdown: str, image_filename: str) -> str:
    """Return ``markdown`` with the chart section inserted or replaced.

    Idempotent: if a section already exists it is swapped for the fresh one, so
    running twice never duplicates it. Otherwise the section is appended.

    :param markdown: The current transcript Markdown.
    :param image_filename: Bare PNG filename (a same-folder relative path).
    :returns: The updated Markdown text.
    """
    section = round_chart_section(image_filename)
    if _SECTION_RE.search(markdown):
        return _SECTION_RE.sub("\n\n" + section, markdown, count=1).rstrip() + "\n"
    return markdown.rstrip() + "\n\n" + section


__all__ = ["SECTION_HEADING", "embed_round_chart_section", "round_chart_section"]
