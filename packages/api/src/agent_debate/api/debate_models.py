"""Request/response models for the debate endpoints (task 10.2, issue #69).

PRD §6: ``POST /debates`` takes a topic (+ optional per-run overrides) and
``GET /debates/{id}`` returns status/result. These Pydantic models are the
validated HTTP contract. The topic field reuses the 7.2
:func:`~agent_debate.core.validate_topic` validator (length cap, charset,
non-empty), so an abusive/oversized topic is rejected at the boundary and
FastAPI surfaces it as a ``422`` with a clear message — no inline magic.
"""

from __future__ import annotations

from agent_debate.api.debate_store import DebateStatus
from agent_debate.core import DebateResult, validate_topic
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DebateRequest(BaseModel):
    """Body of ``POST /debates``: a validated topic + optional overrides.

    Attributes:
        topic: The debate topic (validated via the 7.2 trusted-boundary rules).
        rounds: Optional override for debate rounds per side.
        max_words: Optional override for the per-message word limit.
        model: Optional ``provider:model`` override for the debaters.
        search_backend: Optional search backend plug-in selector.
    """

    model_config = ConfigDict(extra="forbid")

    topic: str
    rounds: int | None = Field(default=None, gt=0)
    max_words: int | None = Field(default=None, gt=0)
    model: str | None = Field(default=None, min_length=1)
    search_backend: str | None = Field(default=None, min_length=1)

    @field_validator("topic")
    @classmethod
    def _check_topic(cls, value: str) -> str:
        """Apply the 7.2 topic validation (length/charset/non-empty)."""
        return validate_topic(value)

    def overrides(self) -> dict[str, object]:
        """Return only the supplied config overrides, mapped to settings keys."""
        mapping = {
            "rounds": self.rounds,
            "max_words": self.max_words,
            "debater_model": self.model,
            "search_backend": self.search_backend,
        }
        return {key: value for key, value in mapping.items() if value is not None}


class DebateStarted(BaseModel):
    """Response of ``POST /debates``: the new ``run_id`` and initial status."""

    run_id: str
    status: DebateStatus


class DebateState(BaseModel):
    """Response of ``GET /debates/{id}``: status and the result when done."""

    run_id: str
    status: DebateStatus
    result: DebateResult | None = None
    error: str | None = None


__all__ = ["DebateRequest", "DebateStarted", "DebateState"]
