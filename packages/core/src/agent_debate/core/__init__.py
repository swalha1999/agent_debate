"""agent_debate SDK (``agent_debate.core``) — skeleton (TASKS.md 0.2 / 0.3).

This is the heart of the system (PRD §5.1): the debate engine, agents, skills,
controller, API gatekeeper and search plug-ins. Only the empty package shell
exists for now; later tasks add the real modules.

``core`` depends on ``log`` (issue #3): it re-exports ``log_version`` by
importing across the edge, proving the dependency resolves at runtime.
"""

from __future__ import annotations

from agent_debate.core._version import __version__
from agent_debate.core.gatekeeper import (
    DEFAULT_SERVICE,
    ApiGatekeeper,
    QueueFullError,
    QueueStatus,
    RateLimitConfig,
    RateLimitExceededError,
    ServiceLimits,
    load_rate_limit_config,
)
from agent_debate.core.models import ResolvedModels, resolve_model, resolve_models
from agent_debate.core.search import (
    DEFAULT_MAX_RESULTS,
    DuckDuckGoSearchProvider,
    ResilientSearchProvider,
    SearchProvider,
    SearchResult,
    TavilySearchProvider,
    UnknownSearchBackendError,
    available_search_backends,
    create_search_provider,
    register_search_provider,
)
from agent_debate.core.settings import Settings, get_settings
from agent_debate.core.skills import (
    Argument,
    ArgumentRequest,
    DebateSide,
    OpponentAnalysis,
    OpponentAnalysisRequest,
    analyze_opponent_argument,
    build_argument,
)
from agent_debate.core.validation import MissingApiKeyError, validate_required_keys
from agent_debate.log import log_version

#: Version of the core SDK surface — aliases the canonical ``__version__``
#: (``_version.py``) so the literal "1.00" is defined in exactly one place
#: (guideline §8.1). Smoke tests that predate task 0.13 still read this name.
LIBRARY_VERSION = __version__

#: Public alias used by dependents that re-export this package's version.
core_version = __version__

__all__ = [
    "DEFAULT_MAX_RESULTS",
    "DEFAULT_SERVICE",
    "LIBRARY_VERSION",
    "ApiGatekeeper",
    "Argument",
    "ArgumentRequest",
    "DebateSide",
    "DuckDuckGoSearchProvider",
    "MissingApiKeyError",
    "OpponentAnalysis",
    "OpponentAnalysisRequest",
    "QueueFullError",
    "QueueStatus",
    "RateLimitConfig",
    "RateLimitExceededError",
    "ResilientSearchProvider",
    "ResolvedModels",
    "SearchProvider",
    "SearchResult",
    "ServiceLimits",
    "Settings",
    "TavilySearchProvider",
    "UnknownSearchBackendError",
    "__version__",
    "analyze_opponent_argument",
    "available_search_backends",
    "build_argument",
    "core_version",
    "create_search_provider",
    "get_settings",
    "load_rate_limit_config",
    "register_search_provider",
    "log_version",
    "resolve_model",
    "resolve_models",
    "validate_required_keys",
]
