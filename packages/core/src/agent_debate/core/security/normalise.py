"""Unicode/whitespace/control-char normalisation for untrusted text (task 7.1).

This is the *normalise* half of the security gatekeeper (PRD §5.7): before any
injection-pattern matching runs, untrusted text is folded to a canonical form so
an attacker cannot hide an instruction behind compatibility code points,
zero-width characters or control bytes. Pure text processing — no network, no
config values (the patterns/thresholds live in
:mod:`agent_debate.core.security.constants`).

Order matters and is deliberate:

1. **NFKC** folds compatibility forms (e.g. fullwidth ``ｉｇｎｏｒｅ`` → ``ignore``)
   so disguised keywords reassemble before matching.
2. **Zero-width / invisible removal** deletes characters whose only purpose in
   untrusted text is to split a keyword so a naive matcher misses it.
3. **Control-character stripping** drops C0/C1 control bytes (keeping only the
   whitespace we then normalise), so terminal-escape / NUL tricks cannot survive.
4. **Whitespace collapse** turns any run of whitespace (incl. newlines/tabs) into
   a single space and trims the ends, yielding a stable single-line form.
"""

from __future__ import annotations

import re
import unicodedata

#: Zero-width / invisible code points stripped outright (they carry no meaning in
#: untrusted prose and are a classic keyword-splitting injection trick). Named
#: here so the set is explicit, not a scattered magic string.
_ZERO_WIDTH_CHARS = (
    "​"  # zero-width space
    "‌"  # zero-width non-joiner
    "‍"  # zero-width joiner
    "⁠"  # word joiner
    "﻿"  # zero-width no-break space / BOM
    "­"  # soft hyphen
)

#: Translation table that deletes every zero-width char above in one pass.
_ZERO_WIDTH_TABLE = {ord(ch): None for ch in _ZERO_WIDTH_CHARS}

#: Matches any run of whitespace (Unicode-aware) for collapsing to a single space.
_WHITESPACE_RUN = re.compile(r"\s+")


def _strip_control_chars(text: str) -> str:
    r"""Remove C0/C1 control characters, keeping only normal whitespace.

    Unicode category ``C`` covers control/format/surrogate/private-use chars;
    we drop them all *except* the whitespace forms (tab/newline/CR) that the
    later whitespace-collapse step folds into single spaces. This kills NUL,
    BEL and terminal-escape (``\x1b``) tricks without mangling plain text.
    """
    return "".join(
        ch for ch in text if ch in "\t\n\r" or not unicodedata.category(ch).startswith("C")
    )


def normalise_text(text: str) -> str:
    """Return ``text`` folded to a canonical, injection-resistant form.

    Applies, in order: NFKC unicode normalisation, zero-width/invisible removal,
    control-character stripping and whitespace collapse (see module docstring).
    Pure and deterministic; makes no network call and reads no config.
    """
    folded = unicodedata.normalize("NFKC", text)
    folded = folded.translate(_ZERO_WIDTH_TABLE)
    folded = _strip_control_chars(folded)
    return _WHITESPACE_RUN.sub(" ", folded).strip()


__all__ = ["normalise_text"]
