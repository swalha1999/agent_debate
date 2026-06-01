# Sub-PRD — API Gatekeeper (Rate Limiting & Overflow)

**Parent:** `../PRD.md` · **Status:** v1.0 — implemented · **Last updated:** 2026-06-01
**Mechanism:** the centralized manager for all external API calls.

> Required by guideline §5 (and §2.3). Distinct from the **security** gatekeeper
> (PRD §5.7), which sanitises untrusted text. This one governs **rate/throughput**.

## 1. Purpose

A single chokepoint that every external call — **LLM provider and search provider** —
passes through, enforcing rate limits, queueing overflow, retrying transient failures,
and logging everything for monitoring.

## 2. Requirements (from §5)

- **No direct API calls** may bypass the gatekeeper.
- **Rate limits enforced before each call.**
- **Overflow is queued, never dropped or crashed.**
- **All calls are logged** for monitoring.

## 3. Interface

```python
class ApiGatekeeper:
    def __init__(self, config: RateLimitConfig): ...
    def execute(self, api_call, *args, **kwargs): ...   # check → queue? → retry → log
    def get_queue_status(self) -> QueueStatus: ...       # depth + stats
```

## 4. Rate-limit config — from file, not code (§5.2)

`config/rate_limits.json`, versioned starting at `1.00`:

```json
{
  "rate_limits": {
    "version": "1.00",
    "services": {
      "default":   { "requests_per_minute": 30, "requests_per_hour": 500, "concurrent_max": 5, "retry_after_seconds": 30, "max_retries": 3 },
      "anthropic": { "requests_per_minute": 30, "requests_per_hour": 500, "concurrent_max": 5, "retry_after_seconds": 30, "max_retries": 3 },
      "search":    { "requests_per_minute": 20, "requests_per_hour": 300, "concurrent_max": 3, "retry_after_seconds": 15, "max_retries": 2 }
    }
  }
}
```

## 5. Overflow queue (§5.3)

- **FIFO** queue for pending requests, **max depth** from config.
- **Backpressure** signal when the queue is full.
- **Drain** mechanism processes requests as rate windows reset.

## 6. Acceptance criteria

- [ ] Every LLM/search call is routed through `execute`; no bypass exists (test-enforced).
- [ ] Rate limits read from `config/rate_limits.json` (0 hard-coded).
- [ ] Exceeding a limit queues the request (FIFO) instead of dropping/crashing.
- [ ] Transient failures retried with backoff per config.
- [ ] Every call logged with service, latency, outcome.
- [ ] `get_queue_status()` reports depth + stats.

## 7. Edge cases

Queue full (backpressure), sustained overflow + drain, repeated transient failures up
to `max_retries`, concurrent-max saturation, config hot values out of range.
