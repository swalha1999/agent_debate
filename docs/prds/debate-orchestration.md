# Sub-PRD — Debate Orchestration

**Parent:** `../PRD.md` · **Status:** Draft v0.1 · **Last updated:** 2026-05-30
**Mechanism:** the engine that runs a full Pro-vs-Con debate.

> Required by guideline §2.3 (dedicated PRD per central mechanism).

## 1. Purpose

Drive a deterministic, observable debate between the Pro and Con agents, moderated
by the Controller, producing a structured `DebateResult`.

## 2. Inputs / outputs

- **Input:** `DebateConfig` (rounds, max_words, models, timeout, retries) + a topic.
- **Output:** `DebateResult` = ordered transcript, per-turn tool calls, controller
  nudges, closing discussion, final verdict, token/cost + latency totals.

## 3. Flow

1. **Setup** — controller receives/sets the topic, privately assigns Pro = FOR and
   Con = AGAINST, hides its own stance.
2. **Debate loop** — `round = 1..ROUNDS` (default 10), alternating:
   - Pro turn → `assess_drift(Pro)` → nudge if captured (not a debate turn).
   - Con turn (must rebut Pro's latest) → `assess_drift(Con)` → nudge if captured.
3. **Closing discussion** — a freer exchange before judgement.
4. **Verdict** — controller writes summary + agree/disagree + who won (no fact-check).

Result: exactly **10 Pro + 10 Con** messages, each ≤ `MAX_WORDS`.

## 4. Timeout & retry (kill + recall)

- Every model call wrapped with `TURN_TIMEOUT_S`.
- On timeout/transient error: **cancel** the call, **retry** up to `MAX_RETRIES` with
  backoff. After exhaustion, mark the turn failed and inform the controller.
- All calls flow through the **API gatekeeper** (`prds/api-gatekeeper.md`).

## 5. Word-limit enforcement

- Stated in the system prompt **and** verified post-generation (trim + log violation).

## 6. Events (for streaming + logging)

`message | tool_call | nudge | timeout | retry | verdict | system`, each tagged with
`run_id`, `round`, `agent`. Consumed live by CLI/API/UI.

## 7. Acceptance criteria

- [ ] 10-vs-10 alternating messages within word limit.
- [ ] Each Con/Pro message rebuts the opponent's previous message.
- [ ] Timeout triggers cancel + retry; exhausted retry handled gracefully.
- [ ] Streamed events are ordered and complete.

## 8. Edge cases

Empty/failed search mid-turn; model returns over-limit text; a debater fails all
retries; controller nudge on every round; zero-content message.
