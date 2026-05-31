"""Provider registry + factory — the swappable web-search selector (task 3.2).

``docs/prds/search-plugin.md`` §3 + PRD §5.5: providers register under a *name*
and the **active** one is chosen by config (``SEARCH_BACKEND``), so swapping the
search vendor is a **one-line config change** with no engine/agent/skill/factory
edits. This module is that mechanism:

* :func:`register_search_provider` — a class decorator recording a
  :class:`~agent_debate.core.search.base.SearchProvider` implementation under its
  registry key. A new vendor (task 3.3's DuckDuckGo, a drop-in Tavily, …) becomes
  selectable purely by decorating it — the factory never names a concrete class.
* :func:`create_search_provider` — the factory: it reads
  :pyattr:`Settings.search_backend`, looks the key up in the registry (no
  hard-coded selection branch) and constructs the provider, passing
  :pyattr:`Settings.search_api_key` to providers whose constructor accepts one.
* :func:`available_search_backends` — the sorted registered names, surfaced in
  the unknown-backend error and to callers enumerating options.

The factory makes **no network call** — it only *constructs* the provider; the
provider's :meth:`search` is what later routes external requests through the API
gatekeeper (Epic 13). Selection is a pure registry lookup keyed by the config
value, so "no hard-coded values" holds: the active backend comes from
:class:`Settings`, and which class that resolves to is data, not code.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from agent_debate.core.search.base import SearchProvider
from agent_debate.core.search.errors import UnknownSearchBackendError
from agent_debate.core.search.gatekept import GatekeptSearchProvider
from agent_debate.log import get_logger

if TYPE_CHECKING:
    from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
    from agent_debate.core.settings import Settings

_LOG = get_logger("search.registry")

_ProviderT = TypeVar("_ProviderT", bound=type[SearchProvider])

#: Name -> provider class. Populated by :func:`register_search_provider`; the
#: factory's *only* selection input, so adding a backend never edits the factory.
_REGISTRY: dict[str, type[SearchProvider]] = {}

#: Constructor parameter a provider exposes when it needs ``SEARCH_API_KEY``.
_API_KEY_PARAM = "api_key"


def register_search_provider(name: str) -> Callable[[_ProviderT], _ProviderT]:
    """Return a class decorator registering a provider under ``name``.

    Args:
        name: The registry key (the ``SEARCH_BACKEND`` value selecting it).

    Returns:
        The decorator, which records the class and returns it unchanged.

    Raises:
        ValueError: If ``name`` is already registered — duplicate keys fail loudly
            instead of silently shadowing an existing provider.
    """

    def decorator(provider_cls: _ProviderT) -> _ProviderT:
        if name in _REGISTRY:
            raise ValueError(
                f"search backend {name!r} is already registered to {_REGISTRY[name].__name__!r}"
            )
        _REGISTRY[name] = provider_cls
        _LOG.debug("search_provider_registered", backend=name, provider=provider_cls.__name__)
        return provider_cls

    return decorator


def available_search_backends() -> list[str]:
    """Return the registered backend names in sorted order."""
    return sorted(_REGISTRY)


def create_search_provider(
    settings: Settings, *, gatekeeper: Gatekeeper | None = None
) -> SearchProvider:
    """Construct the active :class:`SearchProvider` from ``settings``.

    The active backend is ``settings.search_backend`` (config, never hard-coded);
    its class is resolved via a pure registry lookup. Providers whose constructor
    accepts an ``api_key`` parameter receive ``settings.search_api_key``; keyless
    providers are constructed with no arguments. No network call is made here.

    When a ``gatekeeper`` is supplied the active provider is wrapped in a
    :class:`~agent_debate.core.search.gatekept.GatekeptSearchProvider` so its live
    external call routes through :meth:`ApiGatekeeper.execute` (task 13.6 — no
    bypass). Omitting it returns the bare provider (backward-compatible default).

    Args:
        settings: The runtime :class:`Settings` carrying ``SEARCH_BACKEND`` and
            the optional ``SEARCH_API_KEY``.
        gatekeeper: The API gatekeeper to route the provider's external call
            through; when ``None`` the bare provider is returned unchanged.

    Returns:
        A freshly constructed provider instance for the active backend, wrapped in
        the gatekeeper router when one is supplied.

    Raises:
        UnknownSearchBackendError: If ``search_backend`` is not registered; the
            error names the requested key and lists the available backends.
    """
    backend = settings.search_backend
    try:
        provider_cls = _REGISTRY[backend]
    except KeyError:
        raise UnknownSearchBackendError(backend, available_search_backends()) from None

    provider = _construct(provider_cls, settings.search_api_key)
    _LOG.debug("search_provider_created", backend=backend, provider=provider_cls.__name__)
    if gatekeeper is None:
        return provider
    return GatekeptSearchProvider(provider, gatekeeper=gatekeeper)


def _construct(provider_cls: type[SearchProvider], api_key: str | None) -> SearchProvider:
    """Instantiate ``provider_cls``, passing ``api_key`` only if it accepts one."""
    if _API_KEY_PARAM in inspect.signature(provider_cls).parameters:
        return provider_cls(api_key=api_key)  # type: ignore[call-arg]
    return provider_cls()


__all__ = [
    "available_search_backends",
    "create_search_provider",
    "register_search_provider",
]
