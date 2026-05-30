# Improvements to Keep in Mind

> Distilled from the Assignment 1 feedback report and the lecturer's software
> guidelines. Only the points that apply to **this** project (`agent_debate`)
> are kept — the ML/signal-specific notes from the previous assignment were
> dropped because they don't apply here.

These are the things we lost points on or that the guidelines emphasise. Treat
them as a standing checklist for the debate system.

## Planning & documentation
- [ ] Ship a **PRD up front** (see `PRD.md`): the problem, the goals, the design — written *before* the code, so a new team member understands the vision without asking us.
- [ ] Keep docs current as the design evolves; document the *why* behind technical decisions, not just the *what*.
- [ ] README must let any developer install and run the project with zero prior knowledge.

## Configuration & security
- [ ] Config must be **portable**: it should set up cleanly in a completely different environment by someone who has never seen it. No hardcoded paths or environment assumptions.
- [ ] **No secrets in the repo.** API keys (LLM provider keys, etc.) come from environment / `.env`, never committed. Ship a `.env.example`.
- [ ] We need a real **gatekeeper / security layer** — validate and sanitise anything that crosses a trust boundary (user input, tool output, web-search results fed back to the model). Don't let untrusted text drive privileged actions.

## Costs & resource awareness
- [ ] Document and reason about **what the system costs to operate** (LLM token usage per debate, per round) and how that scales. Word limits per agent directly bound this — make the cost model explicit.

## Extensibility
- [ ] Design for change: clean separation of concerns so a new provider, a new agent skill, or a new UI can be added without breaking what already works. This is why we use a provider-agnostic LLM layer (no ecosystem lock-in).

## Quality standards
- [ ] Establish **automated quality tooling** beyond manual review: linter + formatter (`ruff`), type checks, and tests wired into CI / pre-commit.
- [ ] **Testing**: rigorous tests across meaningful scenarios including edge cases (timeouts, agent going off-track, empty/failed web search, malformed model output).

## Output clarity (UI / logs / visualization)
- [ ] Make behaviour legible at a glance: the **log system** and **UI/CLI** must clearly show, for each round, who said what, the controller's nudges, and the final verdict — layered so the relationship between arguments is obvious.
- [ ] Don't collapse everything into one overloaded view; separate the streams (per-agent transcript, controller actions, system logs).

## Process
- [ ] Maintain disciplined **version control** with a visible development history, including the AI-assisted workflow.
