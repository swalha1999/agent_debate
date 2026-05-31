"""Configuration for the security sanitisation gatekeeper (PRD §5.7, task 7.1).

The guideline forbids hard-coded values scattered through the code (§7.2): every
threshold and pattern the sanitiser relies on lives here once, as a named
constant, and is referenced (never re-inlined) by
:mod:`agent_debate.core.security.sanitiser` and the normalise helpers. Each
value documents *why* it exists and where it comes from.

These are defence-in-depth heuristics, not a perfect parser: the injection
pattern list neutralises the *common* prompt-injection phrasings seen in the
wild (user topics, web-search snippets, model output) before that text can
re-enter a prompt as an apparent instruction.
"""

from __future__ import annotations

#: Maximum length (characters) untrusted text is capped to before it re-enters a
#: prompt (PRD §5.7: "web-search queries length-capped"). A length cap bounds the
#: blast radius of a hostile payload and the token cost of echoing it back. Kept
#: here as the single source of truth; every entry point accepts a ``max_length``
#: override so callers (e.g. a future Settings field) can tighten it per context.
DEFAULT_MAX_UNTRUSTED_LEN = 4000

#: Maximum length (characters) the user-supplied **debate topic** may have
#: (task 7.2 input validation, PRD §5.7). Unlike :data:`DEFAULT_MAX_UNTRUSTED_LEN`
#: (a *sanitiser* truncation cap), this is a *validation* cap: a topic over this
#: length is **rejected** with a clear error, not silently truncated. A topic is
#: a short proposition, so the cap is deliberately tight to surface abuse early.
MAX_TOPIC_LEN = 500

#: Maximum length (characters) a **web-search query** may have before it is
#: rejected (task 7.2; PRD §5.7: "web-search queries length-capped"). Queries are
#: short keyword strings, so this is tighter still; over-length input is rejected.
MAX_QUERY_LEN = 256

#: Replacement token substituted for each neutralised injection match. Chosen to
#: be visibly inert: it reads as redaction metadata, never as an instruction, so
#: a downstream model treats it as data. Single source of truth for the marker.
NEUTRALISED_MARKER = "[redacted: untrusted-instruction]"

#: ``agent`` label stamped on the sanitiser's log events (a name, not a value).
LOG_AGENT = "security"

#: ``event_type`` emitted when sanitisation neutralises something — the LOG
#: schema's ``system`` kind makes the action observable in the run log (§5.8).
LOG_EVENT_TYPE = "system"

#: Case-insensitive regex fragments matching the common prompt-injection phrasings
#: untrusted text must not be able to smuggle in as instructions (PRD §5.7). Each
#: match is replaced with :data:`NEUTRALISED_MARKER`. Ordered roughly by family:
#: override phrases, role/system markers, and identity-reassignment openers. This
#: is the single, named place to extend coverage — do not inline new patterns.
INJECTION_PATTERNS: tuple[str, ...] = (
    # "ignore/disregard/forget … (previous|prior|above|earlier) … instructions"
    r"(?:ignore|disregard|forget|override)\b[^\n]*?"
    r"\b(?:previous|prior|above|preceding|earlier|all)\b[^\n]*?"
    r"\b(?:instruction|instructions|prompt|prompts|rule|rules|context)\b",
    # "disregard/ignore the above" (no explicit 'instructions' noun)
    r"(?:disregard|ignore|forget)\b[^\n]*?\bthe\s+above\b",
    # Conversation role markers that could fake a new turn / system block.
    # Normalisation collapses newlines to spaces, so anchor on a word boundary
    # rather than line-start: "system:" / "assistant:" anywhere is suspicious.
    r"\b(?:system|assistant|user|developer)\s*:",
    r"(?:<\s*/?\s*(?:system|assistant|user|im_start|im_end)[^>]*>)",
    # Identity-reassignment openers ("you are now …", "act as …", "pretend …").
    r"\byou\s+are\s+now\b",
    r"\b(?:act|behave)\s+as\s+(?:if|though|a|an|the)\b",
    r"\bpretend\s+(?:to\s+be|that|you)\b",
    # Direct attempts to extract the wrapper / system prompt.
    r"\breveal\b[^\n]*?\b(?:system\s+prompt|instructions|prompt)\b",
    r"\b(?:print|repeat|show|output)\b[^\n]*?\b(?:system\s+prompt|your\s+instructions)\b",
)

__all__ = [
    "DEFAULT_MAX_UNTRUSTED_LEN",
    "INJECTION_PATTERNS",
    "LOG_AGENT",
    "LOG_EVENT_TYPE",
    "MAX_QUERY_LEN",
    "MAX_TOPIC_LEN",
    "NEUTRALISED_MARKER",
]
