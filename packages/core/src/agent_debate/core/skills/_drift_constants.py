"""Named constants for the deepened drift detector (TASKS.md 8.1, issue #60).

Split out of :mod:`agent_debate.core.constants` so that module stays under the
150-line guideline (split, don't compress) and the §3 drift lexicon lives next to
its logic in :mod:`agent_debate.core.skills._drift_logic`. Every phrase set, weight
and the capture threshold are named here — no literals are scattered through the
detector (guideline §7.2). The cross-cutting PRD §7 config defaults remain in
:mod:`agent_debate.core.constants`; these are detector-internal tuning values.
"""

from __future__ import annotations

#: §3 "conceding the core claim" — explicit concession phrases. Their presence is
#: the strongest single text signal that the agent has given up its side.
DRIFT_CONCEDE_PHRASES: tuple[str, ...] = (
    "i concede",
    "i was wrong",
    "i accept that",
    "i accept the",
    "i withdraw",
    "i can't argue with that",
    "i cannot argue with that",
    "the opponent has the stronger",
    "the opponent is correct",
    "you have convinced me",
)

#: §3 "adopting the opponent's framing/conclusion" — agreement markers signalling
#: the agent now endorses the opponent rather than rebutting it.
DRIFT_AGREEMENT_PHRASES: tuple[str, ...] = (
    "you're right",
    "you are right",
    "i agree",
    "fair point",
    "good point",
    "that's true",
    "that is true",
    "i must agree",
)

#: §3 "hedging away from the assigned side" — tentative markers that soften the
#: agent's commitment and lean toward the opponent's view.
DRIFT_HEDGE_PHRASES: tuple[str, ...] = (
    "perhaps the opponent",
    "maybe they have a point",
    "maybe the opponent",
    "it's true that",
    "it is true that",
    "i suppose the opponent",
    "they may have a point",
    "there may be some merit",
)

#: Rebuttal/counter markers — when present they show the agent is still arguing
#: AGAINST the opponent, so a high-overlap message is a rebuttal, not a restating.
DRIFT_REBUTTAL_MARKERS: tuple[str, ...] = (
    "however",
    "but ",
    "this does not hold",
    "fails",
    "wrong because",
    "on the contrary",
    "i disagree",
    "rebut",
    "counter",
    "does not follow",
    "flawed",
)

#: Token overlap ratio (shared content words / opponent content words) at/above
#: which an opponent-context message counts as "restating the opponent" — but only
#: when no rebuttal marker is present (§3 restating-without-rebuttal).
DRIFT_OVERLAP_THRESHOLD = 0.6

#: Tokens shorter than this are treated as stop-words/noise and ignored when
#: measuring opponent overlap, so the ratio reflects content words, not glue words.
DRIFT_MIN_OVERLAP_TOKEN_LEN = 4

#: Per-signal weights combined into the drift confidence (a transparent additive
#: scheme — not magic numbers). Concession is the heaviest single signal; the
#: clamped sum is the confidence. Order: concede, agreement, hedge, restating.
DRIFT_WEIGHT_CONCEDE = 0.8
DRIFT_WEIGHT_AGREEMENT = 0.55
DRIFT_WEIGHT_HEDGE = 0.5
DRIFT_WEIGHT_RESTATING = 0.7

#: Confidence at/above which ``assess_drift`` marks the agent ``captured``. A single
#: configurable threshold so capture sensitivity is tuned in one place (§7.2).
DRIFT_CAPTURE_THRESHOLD = 0.5

#: Human-readable labels for each fired signal, woven into the assessment reason so
#: the explanation names which §3 signal(s) tripped (single source of truth).
DRIFT_SIGNAL_LABEL_CONCEDE = "conceded the core claim"
DRIFT_SIGNAL_LABEL_AGREEMENT = "adopted the opponent's framing/conclusion"
DRIFT_SIGNAL_LABEL_HEDGE = "hedged away from its assigned side"
DRIFT_SIGNAL_LABEL_RESTATING = "restated the opponent without rebuttal"

#: Reason templates for the deepened detector. ``DRIFT_REASON_DETECTED`` lists the
#: fired signal labels; ``DRIFT_REASON_ON_SIDE`` is the clean (on-side) explanation.
DRIFT_REASON_DETECTED = "Agent {labels}."
DRIFT_REASON_ON_SIDE = "Agent still defends its assigned side; no drift signal fired."

__all__ = [
    "DRIFT_AGREEMENT_PHRASES",
    "DRIFT_CAPTURE_THRESHOLD",
    "DRIFT_CONCEDE_PHRASES",
    "DRIFT_HEDGE_PHRASES",
    "DRIFT_MIN_OVERLAP_TOKEN_LEN",
    "DRIFT_OVERLAP_THRESHOLD",
    "DRIFT_REASON_DETECTED",
    "DRIFT_REASON_ON_SIDE",
    "DRIFT_REBUTTAL_MARKERS",
    "DRIFT_SIGNAL_LABEL_AGREEMENT",
    "DRIFT_SIGNAL_LABEL_CONCEDE",
    "DRIFT_SIGNAL_LABEL_HEDGE",
    "DRIFT_SIGNAL_LABEL_RESTATING",
    "DRIFT_WEIGHT_AGREEMENT",
    "DRIFT_WEIGHT_CONCEDE",
    "DRIFT_WEIGHT_HEDGE",
    "DRIFT_WEIGHT_RESTATING",
]
