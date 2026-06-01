"""Named constants for the deterministic verdict scorer (TASKS.md 8.3, issue #62).

Split out of :mod:`agent_debate.core.constants` so that module stays under the
150-line guideline (split, don't compress) and the §3.2 verdict lexicon lives next
to its logic in :mod:`agent_debate.core.skills._verdict_logic`. Every signal phrase
set, criterion weight, the tie margin and the summary/rationale templates are named
here — no literals are scattered through the scorer (guideline §7.2).

The verdict is judged on **argumentation / rebuttal quality / engagement** only —
explicitly **not** factual correctness (PRD §3: no fact-checking / truth
verification). None of these signals inspect whether a claim is *true*; they
measure how the side *argued*.
"""

from __future__ import annotations

#: The three named scoring criteria the verdict is judged on (PRD §3.2 step 4).
#: Argument quality, rebuttal quality, engagement — never factual correctness.
VERDICT_CRITERION_ARGUMENTATION = "argumentation"
VERDICT_CRITERION_REBUTTAL = "rebuttal"
VERDICT_CRITERION_ENGAGEMENT = "engagement"

#: Phrases marking a REBUTTAL — the side is countering rather than restating. Reused
#: from the drift lexicon's rebuttal markers (single source) plus debate connectives.
VERDICT_REBUTTAL_MARKERS: tuple[str, ...] = (
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
    "false",
    "mistaken",
)

#: Phrases marking ENGAGEMENT — the side is responding to the opponent (referring
#: to "your point", "the opponent", "you claim") rather than monologuing.
VERDICT_ENGAGEMENT_MARKERS: tuple[str, ...] = (
    "your point",
    "your claim",
    "your argument",
    "the opponent",
    "you said",
    "you claim",
    "you argue",
    "as you",
    "that claim",
)

#: Phrases marking AGREEMENT / CONVERGENCE — both sides exhibiting these is the
#: signal that the agents converged/agreed (PRD §3.2 step 4). Argument-quality
#: signal, NOT a truth check.
VERDICT_AGREEMENT_MARKERS: tuple[str, ...] = (
    "i agree",
    "you're right",
    "you are right",
    "fair point",
    "i concede",
    "i accept that",
    "good point",
    "that is true",
)

#: Per-criterion DIFFERENTIAL weights combined into a side's total score (transparent
#: additive scheme — not magic numbers). Deliberately distinct, non-integer values so
#: an exact numeric tie between two non-identical transcripts is near-impossible (HW2
#: §8.4: differential 80%/70%-style scoring is explicitly permitted). Each present turn
#: earns the argumentation base; each rebuttal / engagement marker hit adds its weight.
VERDICT_WEIGHT_ARGUMENTATION = 1.0
VERDICT_WEIGHT_REBUTTAL = 1.5
VERDICT_WEIGHT_ENGAGEMENT = 0.75

#: Minimum number of turns (per side) that must carry an agreement marker for the
#: debate to be reported as converged — both sides must show it.
VERDICT_CONVERGENCE_MIN_SIDES = 2

#: Template for the auto-generated debate SUMMARY; ``{turns}`` is the turn count,
#: ``{result}`` the human-readable outcome line, ``{converged}`` the agreement note.
VERDICT_SUMMARY_TEMPLATE = (
    "Debate of {turns} turns. {result} {converged} Judged on argumentation, "
    "rebuttal quality and engagement — not factual correctness."
)

#: Result clause for a decisive outcome; ``{winner}`` is the winning side label. A
#: verdict is ALWAYS decisive — there is no tie clause (HW2 §8.4: ties are forbidden).
VERDICT_RESULT_WIN = "The {winner} side argued more effectively and wins."

#: Deterministic FINAL fallback side for the (now vanishingly rare) case where two
#: transcripts are byte-for-byte symmetric and every tie-breaker is equal. Picking a
#: fixed side keeps the verdict decisive and reproducible — never a tie, never random.
VERDICT_DECISIVE_FALLBACK_SIDE = "pro"

#: Clause appended to the rationale when the outcome was settled by the tie-breaker
#: cascade rather than the raw weighted total; ``{criterion}`` names the deciding step.
VERDICT_TIEBREAK_NOTE = " Scores were level on total; decided on {criterion}."

#: Converged / not-converged notes appended to the summary.
VERDICT_CONVERGED_NOTE = "The agents converged toward agreement."
VERDICT_NOT_CONVERGED_NOTE = "The agents stayed opposed."

#: Reasoning template naming the per-side criterion totals behind the outcome.
VERDICT_REASONING_TEMPLATE = (
    "Pro scored {pro} and Con scored {con} on argumentation/rebuttal/engagement; winner = {winner}."
)

__all__ = [
    "VERDICT_AGREEMENT_MARKERS",
    "VERDICT_CONVERGED_NOTE",
    "VERDICT_CONVERGENCE_MIN_SIDES",
    "VERDICT_CRITERION_ARGUMENTATION",
    "VERDICT_CRITERION_ENGAGEMENT",
    "VERDICT_CRITERION_REBUTTAL",
    "VERDICT_DECISIVE_FALLBACK_SIDE",
    "VERDICT_ENGAGEMENT_MARKERS",
    "VERDICT_NOT_CONVERGED_NOTE",
    "VERDICT_REASONING_TEMPLATE",
    "VERDICT_REBUTTAL_MARKERS",
    "VERDICT_RESULT_WIN",
    "VERDICT_SUMMARY_TEMPLATE",
    "VERDICT_TIEBREAK_NOTE",
    "VERDICT_WEIGHT_ARGUMENTATION",
    "VERDICT_WEIGHT_ENGAGEMENT",
    "VERDICT_WEIGHT_REBUTTAL",
]
