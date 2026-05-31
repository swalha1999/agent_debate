"""Per-model price config models + loader (task 15.1, issue #101).

Epic 15 turns the token counts task 6.7 captures into a USD cost. This module is
its *config* surface: typed Pydantic models mirroring ``config/model_prices.json``
and a loader that reads them, plus :func:`get_model_price` which looks a model up
(falling back to the ``default`` entry for unknown models). The actual token →
cost arithmetic lives next door in :mod:`agent_debate.core.pricing._cost`.

"0 hard-coded prices" (guideline §5.2 / §7.2): no price value (15.0, 75.0, …) is
baked into Python — every number is read from the file. The only literals here
are the config file *name* (one named constant) and the fallback model *key*
``"default"`` — both identifiers, not price values. Prices are public list
prices, not secrets.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_debate.log import get_logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError

_LOG = get_logger("pricing.config")

#: Repo-root-relative location of the versioned price data file. The *path* is
#: the one acceptable constant — it names the file, not a price.
MODEL_PRICES_FILENAME = "model_prices.json"
_CONFIG_DIRNAME = "config"

#: Model key used when a requested model has no explicit entry. A key name, not a
#: price value.
DEFAULT_MODEL = "default"

#: This file lives at ``packages/core/src/agent_debate/core/pricing/`` — six
#: parents up is the repo root, so the data file resolves regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parents[6]


class ModelPrice(BaseModel):
    """Per-model prices — USD per 1,000,000 tokens, read from the config file.

    Both fields are required (no default *values*, so nothing bakes a price into
    code) and non-negative (a zero price is valid, e.g. a free/preview model).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_per_1m: float = Field(ge=0.0)
    output_per_1m: float = Field(ge=0.0)


class PriceTable(BaseModel):
    """Parsed view of ``config/model_prices.json`` (the ``model_prices`` body).

    Mirrors the file shape minus the top-level ``model_prices`` wrapper, which
    :func:`load_price_table` unwraps before validation. An optional ``note``
    carries the file's as-of/confirm-against-provider caveat.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    note: str | None = None
    models: dict[str, ModelPrice]

    def get_model_price(self, model: str) -> ModelPrice:
        """Return ``model``'s price, falling back to the ``default`` entry.

        Models without an explicit entry inherit the ``default`` price rather
        than failing, so an unpriced/new model still yields a usable cost.
        """
        return self.models.get(model, self.models[DEFAULT_MODEL])


def _default_path() -> Path:
    """Resolve ``config/model_prices.json`` at the repo root (cwd-independent)."""
    return _REPO_ROOT / _CONFIG_DIRNAME / MODEL_PRICES_FILENAME


def load_price_table(path: Path | None = None) -> PriceTable:
    """Load, parse and validate the per-model price table from ``path``.

    :param path: explicit JSON file; defaults to the repo-root
        ``config/model_prices.json`` resolved robustly (not from cwd).
    :raises FileNotFoundError: if the file does not exist (message names it).
    :raises ValueError: if the JSON is malformed or fails schema validation.
    """
    config_path = path if path is not None else _default_path()
    if not config_path.is_file():
        raise FileNotFoundError(f"model_prices.json not found: {config_path}")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        table = PriceTable.model_validate(raw["model_prices"])
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
        raise ValueError(f"invalid model_prices.json at {config_path}: {exc}") from exc
    _LOG.debug(
        "price_table_loaded",
        version=table.version,
        models=sorted(table.models),
        path=str(config_path),
    )
    return table


def get_model_price(model: str, table: PriceTable | None = None) -> ModelPrice:
    """Return ``model``'s :class:`ModelPrice`, loading the default table if needed.

    :param model: the ``provider:model`` (or bare model) id to price.
    :param table: a pre-loaded :class:`PriceTable`; when ``None`` the repo-root
        ``config/model_prices.json`` is loaded. Unknown models fall back to the
        ``default`` entry (see :meth:`PriceTable.get_model_price`).
    """
    resolved = table if table is not None else load_price_table()
    return resolved.get_model_price(model)


__all__ = [
    "DEFAULT_MODEL",
    "MODEL_PRICES_FILENAME",
    "ModelPrice",
    "PriceTable",
    "get_model_price",
    "load_price_table",
]
