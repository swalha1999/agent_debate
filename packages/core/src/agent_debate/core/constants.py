"""Default configuration values — the single source of truth (PRD §7, §7.2).

The guideline forbids hard-coded values scattered through the code (§7.2): the
PRD §7 defaults live here once and are referenced by :mod:`agent_debate.core.
settings`. Every name maps one-to-one to a row of the PRD §7 configuration
table so the two stay verifiably in sync.
"""

from __future__ import annotations

#: Default model for both debaters when no per-side override is given (PRD §7).
DEFAULT_DEBATER_MODEL = "anthropic:claude-sonnet-4-6"

#: Default model for the controller / judge agent (PRD §7).
DEFAULT_CONTROLLER_MODEL = "anthropic:claude-opus-4-8"

#: Rounds per agent (PRD §7).
DEFAULT_ROUNDS = 10

#: Word limit per debate message (PRD §7).
DEFAULT_MAX_WORDS = 150

#: Per-turn timeout in seconds (PRD §7).
DEFAULT_TURN_TIMEOUT_S = 60

#: Retries on timeout/error (PRD §7).
DEFAULT_MAX_RETRIES = 2

#: Selects the ``SearchProvider`` plug-in; DuckDuckGo needs no key (PRD §7).
DEFAULT_SEARCH_BACKEND = "duckduckgo"

#: Connective phrase the ``build_argument`` skill uses to introduce its rebuttal
#: when an opponent point is supplied (anti-sycophancy: the debater must rebut,
#: not concede — ``docs/prds/anti-sycophancy.md`` §2). Kept here, not inlined.
REBUTTAL_LEAD_IN = "The opponent argued: "

#: Suffix appended after the quoted opponent point in the rebuttal link, steering
#: the debater to answer rather than parrot it (anti-sycophancy §3).
REBUTTAL_LEAD_OUT = " — this does not hold, because:"

#: Template the ``build_argument`` skill uses to phrase the closing line; ``{side}``
#: is the assigned stance and ``{claim}`` the central claim. Single source so the
#: conclusion wording is never duplicated inline.
CONCLUSION_TEMPLATE = "Therefore, the {side} side maintains that {claim}"

#: Delimiters the ``analyze_opponent_argument`` skill splits the opponent's last
#: message on to extract its key claims (one per sentence). Kept here, not inlined,
#: so the parsing rule lives in one place (guideline §7.2).
CLAIM_SPLIT_DELIMITERS = ".!?"

#: Concession/agreement phrases the deterministic baseline of ``assess_drift``
#: scans the message text for (lower-cased substring match). Their presence is a
#: drift signal: the agent is adopting the opponent's conclusion or conceding the
#: core claim rather than rebutting (anti-sycophancy §3). Kept here, not inlined,
#: so Epic 8 (8.1) can extend the detector from one source of truth.
DRIFT_CONCESSION_PHRASES: tuple[str, ...] = (
    "you're right",
    "you are right",
    "i agree",
    "i concede",
    "i was wrong",
    "fair point",
    "good point",
    "i accept that",
    "the opponent has the stronger",
    "i can't argue with that",
)

#: Confidence assigned by ``assess_drift`` when the controller LLM supplies explicit
#: drift ``signals`` (a strong, caller-asserted indication) — anti-sycophancy §3.
DRIFT_SIGNAL_CONFIDENCE = 0.9

#: Confidence assigned when the deterministic concession-phrase heuristic fires.
DRIFT_PHRASE_CONFIDENCE = 0.6

#: Confidence assigned when no drift signal fires (the agent looks on-side). Low,
#: because the baseline is intentionally shallow until Epic 8 (8.1) deepens it.
DRIFT_CLEAR_CONFIDENCE = 0.1

#: Reason text emitted by ``assess_drift`` for each outcome (single source of truth).
DRIFT_REASON_SIGNALS = "Controller flagged drift signals: {signals}."
DRIFT_REASON_PHRASE = "Message contains a concession/agreement phrase: {phrase!r}."
DRIFT_REASON_CLEAR = "No concession or drift signal detected; agent appears on-side."

#: Template for the private correction text a ``nudge`` carries (anti-sycophancy §4).
#: ``{side}`` is the captured agent's side and ``{reason}`` the drift reason. The
#: nudge re-anchors the side and is logged + surfaced but never a debate turn.
NUDGE_CORRECTION_TEMPLATE = (
    "Private correction for the {side} side: {reason} "
    "Hold your assigned side and rebut the opponent — do not concede."
)

#: The outcome label ``render_verdict`` uses when neither side outscores the other
#: (anti-sycophancy §4: the controller declares a debate-derived outcome, never a
#: pre-held stance). Kept here so the literal is defined once.
VERDICT_TIE = "tie"

#: Rationale template ``render_verdict`` uses for a score-tallied verdict; ``{winner}``
#: is the derived outcome and ``{pro}``/``{con}`` the per-side totals.
VERDICT_RATIONALE_TEMPLATE = "Verdict {winner}: tallied from the transcript (pro={pro}, con={con})."

#: ``event_type`` used when a generated message exceeds the word limit and is
#: trimmed (TASKS.md 5.7). The LOG schema has no ``"violation"`` type, so a policy
#: violation is recorded as a ``system`` event (its payload names the violation).
WORD_LIMIT_LOG_EVENT_TYPE = "system"

#: ``agent`` label recorded on the word-limit violation event (a name, not a value).
WORD_LIMIT_LOG_AGENT = "word_limit"

#: Stable ``payload["violation"]`` tag identifying a word-limit breach in the log.
WORD_LIMIT_VIOLATION_TAG = "word_limit"

#: ``event_type`` recorded when the debate setup step prepares a run (task 6.2).
#: The LOG schema has no dedicated "setup" type, so it is a ``system`` event whose
#: payload carries the topic + the side assignment (orchestration §3.1).
SETUP_LOG_EVENT_TYPE = "system"

#: ``agent`` label recorded on the setup event — the controller owns the setup step
#: (it receives the topic and assigns the sides). A name, not a stance.
SETUP_LOG_AGENT = "controller"

#: ``payload["event"]`` tag identifying the debate-setup record in the run log.
SETUP_EVENT_TAG = "debate_setup"

#: ``event_type`` recorded for each debate turn the loop emits (orchestration §3.2).
LOOP_MESSAGE_EVENT_TYPE = "message"

#: ``event_type`` recorded when the controller nudges a captured agent (§3.2 / §4).
LOOP_NUDGE_EVENT_TYPE = "nudge"

#: ``agent`` label recorded on a controller nudge event (the controller issues it).
LOOP_NUDGE_LOG_AGENT = "controller"

#: ``service`` key the loop selects for the API gatekeeper when routing a debater's
#: model call — the gatekeeper falls back to ``default`` when unconfigured (§13).
LOOP_MODEL_SERVICE = "anthropic"

#: ``event_type`` for each per-turn model call that exceeds ``turn_timeout_s`` and
#: is cancelled before a retry (orchestration §4, the LOG schema's ``timeout`` kind).
TURN_TIMEOUT_EVENT_TYPE = "timeout"

#: ``event_type`` for each scheduled retry of a timed-out/transient turn call (§4).
TURN_RETRY_EVENT_TYPE = "retry"

#: ``event_type`` informing the controller a turn was abandoned after exhausting
#: retries. The LOG schema has no "failed" kind, so it is a ``system`` event whose
#: payload carries the ``turn_failed`` tag the controller/loop reacts to (§4).
TURN_FAILED_EVENT_TYPE = "system"

#: Stable ``payload["turn_failed"]`` tag marking the abandoned-turn record (§4).
TURN_FAILED_TAG = "model_call"

#: Placeholder content recorded in the transcript for a turn abandoned after the
#: timeout/retry budget was exhausted (a marker, not a debater message).
TURN_FAILED_CONTENT = "[turn failed: model call exhausted timeout + retries]"

#: Maps a ``provider:model`` prefix (the part before ``:``) to the environment
#: variable that must hold that provider's API key. The single source of truth
#: for startup key validation (task 2.3) — extend this dict to cover a new
#: provider. Providers absent from this map are treated leniently (not blocked),
#: because their key requirements are not yet modelled here.
PROVIDER_KEY_ENV_VARS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}

__all__ = [
    "CLAIM_SPLIT_DELIMITERS",
    "CONCLUSION_TEMPLATE",
    "DEFAULT_CONTROLLER_MODEL",
    "DEFAULT_DEBATER_MODEL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MAX_WORDS",
    "DEFAULT_ROUNDS",
    "DEFAULT_SEARCH_BACKEND",
    "DEFAULT_TURN_TIMEOUT_S",
    "DRIFT_CLEAR_CONFIDENCE",
    "DRIFT_CONCESSION_PHRASES",
    "DRIFT_PHRASE_CONFIDENCE",
    "DRIFT_REASON_CLEAR",
    "DRIFT_REASON_PHRASE",
    "DRIFT_REASON_SIGNALS",
    "DRIFT_SIGNAL_CONFIDENCE",
    "LOOP_MESSAGE_EVENT_TYPE",
    "LOOP_MODEL_SERVICE",
    "LOOP_NUDGE_EVENT_TYPE",
    "LOOP_NUDGE_LOG_AGENT",
    "NUDGE_CORRECTION_TEMPLATE",
    "PROVIDER_KEY_ENV_VARS",
    "REBUTTAL_LEAD_IN",
    "REBUTTAL_LEAD_OUT",
    "SETUP_EVENT_TAG",
    "SETUP_LOG_AGENT",
    "SETUP_LOG_EVENT_TYPE",
    "TURN_FAILED_CONTENT",
    "TURN_FAILED_EVENT_TYPE",
    "TURN_FAILED_TAG",
    "TURN_RETRY_EVENT_TYPE",
    "TURN_TIMEOUT_EVENT_TYPE",
    "VERDICT_RATIONALE_TEMPLATE",
    "VERDICT_TIE",
    "WORD_LIMIT_LOG_AGENT",
    "WORD_LIMIT_LOG_EVENT_TYPE",
    "WORD_LIMIT_VIOLATION_TAG",
]
