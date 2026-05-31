"""agent_debate SDK (``agent_debate.core``) — skeleton (TASKS.md 0.2 / 0.3).

This is the heart of the system (PRD §5.1): the debate engine, agents, skills,
controller, API gatekeeper and search plug-ins. Only the empty package shell
exists for now; later tasks add the real modules.

``core`` depends on ``log`` (issue #3): it re-exports ``log_version`` by
importing across the edge, proving the dependency resolves at runtime.
"""

from __future__ import annotations

from agent_debate.core import _engine_public, skills
from agent_debate.core._agents_public import *  # noqa: F403 — re-export shim (PRD §3.2)
from agent_debate.core._engine_public import *  # noqa: F403 — re-export shim (PRD §3.2)
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
from agent_debate.core.pricing import (
    DEFAULT_MODEL,
    MODEL_PRICES_FILENAME,
    ModelPrice,
    PriceTable,
    compute_cost,
    get_model_price,
    load_price_table,
)
from agent_debate.core.search import (
    DEFAULT_MAX_RESULTS,
    DuckDuckGoSearchProvider,
    GatekeptSearchProvider,
    ResilientSearchProvider,
    SearchProvider,
    SearchResult,
    TavilySearchProvider,
    UnknownSearchBackendError,
    available_search_backends,
    create_search_provider,
    register_search_provider,
)
from agent_debate.core.security import (
    DEFAULT_MAX_UNTRUSTED_LEN,
    INJECTION_PATTERNS,
    MAX_QUERY_LEN,
    MAX_TOPIC_LEN,
    NEUTRALISED_MARKER,
    InvalidInputError,
    SearchQueryInput,
    SecurityGatekeeper,
    TopicInput,
    normalise_text,
    sanitize_search_result,
    sanitize_untrusted_text,
    validate_search_query,
    validate_topic,
)
from agent_debate.core.settings import Settings, get_settings
from agent_debate.core.skills import *  # noqa: F403 — re-export shim (PRD §3.2)
from agent_debate.core.validation import MissingApiKeyError, validate_required_keys
from agent_debate.log import log_version

#: Version of the core SDK surface — aliases the canonical ``__version__``
#: (``_version.py``) so the literal "1.00" is defined in exactly one place
#: (guideline §8.1). Smoke tests that predate task 0.13 still read this name.
LIBRARY_VERSION = __version__

#: Public alias used by dependents that re-export this package's version.
core_version = __version__

__all__ = [
    "ADVERSARIAL_RELAY_TEMPLATE",
    "ANTI_CONCESSION_RULE",
    "DEFAULT_MAX_RESULTS",
    "DEFAULT_MAX_UNTRUSTED_LEN",
    "DEFAULT_MODEL",
    "DEFAULT_SERVICE",
    "INJECTION_PATTERNS",
    "LIBRARY_VERSION",
    "MAX_QUERY_LEN",
    "MAX_TOPIC_LEN",
    "MODEL_PRICES_FILENAME",
    "ModelPrice",
    "PriceTable",
    "NEUTRALISED_MARKER",
    "compute_cost",
    "get_model_price",
    "load_price_table",
    "WordLimitResult",
    "AgentContext",
    "ApiGatekeeper",
    "CONTROLLER_SKILLS",
    "DebateContexts",
    "DEBATER_SKILLS",
    "DuckDuckGoSearchProvider",
    "GatekeptSearchProvider",
    "InvalidInputError",
    "MissingApiKeyError",
    "QueueFullError",
    "QueueStatus",
    "RateLimitConfig",
    "RateLimitExceededError",
    "ResilientSearchProvider",
    "ResolvedModels",
    "SearchProvider",
    "SearchQueryInput",
    "SearchResult",
    "SecurityGatekeeper",
    "ServiceLimits",
    "Settings",
    "TavilySearchProvider",
    "TopicInput",
    "Turn",
    "UnknownSearchBackendError",
    "__version__",
    "anchor_turn",
    "available_search_backends",
    "build_adversarial_relay",
    "build_controller_system_prompt",
    "build_debater_system_prompt",
    "build_side_anchor",
    "count_words",
    "create_con_debater",
    "create_controller",
    "core_version",
    "create_debate_contexts",
    "create_debater",
    "create_pro_debater",
    "create_search_provider",
    "enforce_word_limit",
    "relay_opponent_turn",
    "get_settings",
    "load_rate_limit_config",
    "normalise_text",
    "sanitize_search_result",
    "sanitize_untrusted_text",
    "register_search_provider",
    "log_version",
    "resolve_model",
    "resolve_models",
    "validate_required_keys",
    "validate_search_query",
    "validate_topic",
    *skills.__all__,  # Epic-4 skills surface (build_argument, web_search, …)
    *_engine_public.__all__,  # Epic-6 engine surface (CostTotals, DebateConfig, …)
]
