# Sub-PRD — Anti-Sycophancy & Drift Detection

**Parent:** `../PRD.md` · **Status:** v1.0 — implemented · **Last updated:** 2026-06-01
**Mechanism:** preventing one agent from "controlling" the other.

> Required by guideline §2.3. This is the project's core technical risk: LLMs are
> trained to be agreeable and drift toward the last speaker (sycophancy).

## 1. Problem

If both debaters share a conversation or are framed as cooperative, the model tends
to concede to whoever spoke last. We must keep both agents firmly on their assigned
sides without letting either capture the other.

## 2. Mechanisms

1. **Separate contexts + adversarial relay.** Debaters never share a chat thread. The
   opponent's message is injected as *"Your opponent argued: «…». Rebut it."* — not as
   an agreeable peer turn.
2. **Side anchoring every turn.** Re-inject the agent's side (FOR/AGAINST) + an
   explicit "do not concede merely because the opponent is convincing" instruction.
   *Delivery (as implemented — see PRD §5.4):* the engine always runs each debater
   with the agent's **own** `message_history`, and pydantic-ai does **not** re-inject
   a configured `system_prompt` once a history is supplied. So the agent's full
   system prompt — its side label, the rules, its named skills **and the topic** —
   is stored on its isolated `AgentContext` and embedded as the leading
   `SystemPromptPart` of the first request (exactly once), keeping each agent's
   anchor isolated to its own thread. This is what guarantees side/topic anchoring
   actually reaches the model on every turn rather than being silently dropped.
3. **Controller drift detection.** After each message, `assess_drift` classifies:
   still defending its side, or starting to agree with / restate the opponent?
4. **Private nudge.** If captured, the controller sends a private correction; it is
   logged + shown in the UI but **does not** count as a debate turn.
5. **No shared scratchpad.** Agents cannot read each other's private reasoning.
6. **Cross-provider option.** Roles may use different models/providers to reduce the
   chance of one "agreeing" with the other (config-driven; default same-provider).

## 3. Drift signal

`assess_drift` returns `{captured: bool, reason: str, confidence: float}`. Heuristics:
adopting opponent's framing/conclusion, conceding the core claim, hedging away from
the assigned side, or restating the opponent without rebuttal.

## 4. Acceptance criteria

- [ ] Debaters never share context; relay framing is adversarial.
- [ ] Side anchoring present on every turn.
- [ ] A **staged drift fixture** (force an agent to parrot the opponent) is detected and
      nudged back ≥ 1 time.
- [ ] Nudges are logged + surfaced, not counted as debate turns.
- [ ] Controller never reveals its own stance.

## 5. Metrics (feeds §9 research)

Per-side capture/nudge counts per debate; correlation with model/word-limit.
