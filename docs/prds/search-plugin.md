# Sub-PRD — Pluggable Search Provider

**Parent:** `../PRD.md` · **Status:** v1.0 — implemented · **Last updated:** 2026-06-01
**Mechanism:** the swappable web-search plug-in (web search is a MUST).

> Required by guideline §2.3 + §12 (plugin architecture / extension points).

## 1. Purpose

Give debaters a mandatory `web_search` capability while keeping the search vendor
**replaceable with one config change** — no engine/agent/skill edits.

## 2. Interface

```python
class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class SearchProvider(Protocol):
    name: str
    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]: ...
```

## 3. Selection & registry

- Providers register under a name; the active one is chosen by `SEARCH_BACKEND`
  (`duckduckgo` | `tavily` | `bing` | …).
- Keys (when needed) via `SEARCH_API_KEY`. DuckDuckGo needs none.

## 4. Providers

- **Default:** `DuckDuckGoSearchProvider` (free, no key, via `ddgs`).
- **Drop-in:** implement `SearchProvider` + register → e.g. `TavilySearchProvider`.

## 5. Integration

- The `web_search` skill calls the **active provider via the API gatekeeper**
  (rate-limited) and passes results through the **security gatekeeper** (sanitised
  against prompt-injection) before returning them to the model.

## 6. Resilience

Timeout, retry/backoff, and graceful empty-result handling (search can be flaky).

## 7. Acceptance criteria

- [ ] `SEARCH_BACKEND=duckduckgo` returns clean `SearchResult`s.
- [ ] Switching backend is a one-line config change (proven with a stub second provider).
- [ ] Results are rate-limited (gatekeeper) and sanitised (security) before use.
- [ ] Empty/error paths handled without crashing the debate.
