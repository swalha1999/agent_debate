"""Unit tests for the per-model price table + cost helper (TASKS.md 15.1, #101).

Epic 15 converts the token counts task 6.7 captures into a USD cost. This task
ships the *price* surface: a versioned ``config/model_prices.json`` mapping model
id -> input/output USD per 1M tokens, typed Pydantic models + a loader, a
``get_model_price`` lookup (with a ``default`` fallback) and ``compute_cost``
that prices a token count from the table. Wiring it into
:class:`DebateResult.cost_usd` is task 15.2 — here we only prove the table,
loader and cost maths.

Like the rate-limit loader tests, these prove the "0 hard-coded prices"
guideline (§5.2 / §7.2): the loader reads the real ``config/model_prices.json``
*and* an explicit temp file with custom prices, so every cost demonstrably comes
from the file rather than from Python.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_debate.core.pricing import (
    DEFAULT_MODEL,
    MODEL_PRICES_FILENAME,
    ModelPrice,
    PriceTable,
    compute_cost,
    get_model_price,
    load_price_table,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_PRICES_PATH = REPO_ROOT / "config" / "model_prices.json"

#: Models the system actually uses (.env.example / constants) — every one must
#: have an explicit price entry in the shipped table.
KNOWN_MODELS = (
    "anthropic:claude-opus-4-8",
    "anthropic:claude-sonnet-4-6",
    "anthropic:claude-haiku-4-5-20251001",
)


def test_loader_reads_real_config_version() -> None:
    """The default loader resolves the repo-root file and reads version 1.00."""
    table = load_price_table()
    assert isinstance(table, PriceTable)
    assert table.version == "1.00"


def test_real_table_has_known_models_and_default() -> None:
    """Every model we use plus the ``default`` fallback is present + typed."""
    table = load_price_table()
    for name in (*KNOWN_MODELS, DEFAULT_MODEL):
        assert isinstance(table.models[name], ModelPrice)


def test_known_model_prices_match_file() -> None:
    """``get_model_price`` returns the exact prices stored in the file."""
    raw = json.loads(MODEL_PRICES_PATH.read_text(encoding="utf-8"))
    expected = raw["model_prices"]["models"]["anthropic:claude-opus-4-8"]
    price = get_model_price("anthropic:claude-opus-4-8")
    assert price.input_per_1m == expected["input_per_1m"]
    assert price.output_per_1m == expected["output_per_1m"]


def test_get_model_price_falls_back_to_default() -> None:
    """An unknown model falls back to the ``default`` price entry."""
    table = load_price_table()
    fallback = get_model_price("unknown:model", table)
    assert fallback == table.models[DEFAULT_MODEL]


def test_missing_file_raises_clear_error(tmp_path: Path) -> None:
    """A missing config path raises ``FileNotFoundError`` naming the path."""
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError, match=str(missing)):
        load_price_table(missing)


def test_malformed_file_raises_value_error(tmp_path: Path) -> None:
    """Invalid JSON raises a clear ``ValueError`` naming the file."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="model_prices.json"):
        load_price_table(bad)


def test_negative_price_rejected(tmp_path: Path) -> None:
    """A negative per-1M price is rejected by schema validation."""
    custom = tmp_path / "neg.json"
    payload = {
        "model_prices": {
            "version": "1.00",
            "models": {"default": {"input_per_1m": -1.0, "output_per_1m": 1.0}},
        }
    }
    custom.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="model_prices.json"):
        load_price_table(custom)


def _custom_table(tmp_path: Path) -> PriceTable:
    """Write + load a table with deliberately round custom prices."""
    custom = tmp_path / "custom.json"
    payload = {
        "model_prices": {
            "version": "9.99",
            "models": {
                "default": {"input_per_1m": 1.0, "output_per_1m": 2.0},
                "anthropic:claude-opus-4-8": {
                    "input_per_1m": 10.0,
                    "output_per_1m": 40.0,
                },
            },
        }
    }
    custom.write_text(json.dumps(payload), encoding="utf-8")
    return load_price_table(custom)


def test_compute_cost_uses_file_prices(tmp_path: Path) -> None:
    """Cost = in/1e6*input_per_1m + out/1e6*output_per_1m from the FILE."""
    table = _custom_table(tmp_path)
    # 2M input @ $10/1M + 0.5M output @ $40/1M = 20 + 20 = 40.
    cost = compute_cost("anthropic:claude-opus-4-8", 2_000_000, 500_000, table)
    assert cost == pytest.approx(40.0)


def test_compute_cost_unknown_model_uses_default(tmp_path: Path) -> None:
    """An unknown model is priced via the table's ``default`` entry."""
    table = _custom_table(tmp_path)
    # 1M input @ $1/1M + 1M output @ $2/1M = 3.
    cost = compute_cost("who:knows", 1_000_000, 1_000_000, table)
    assert cost == pytest.approx(3.0)


def test_compute_cost_zero_tokens_is_zero(tmp_path: Path) -> None:
    """No tokens means no cost regardless of the price entry."""
    table = _custom_table(tmp_path)
    assert compute_cost("anthropic:claude-opus-4-8", 0, 0, table) == 0.0


def test_filename_constant_matches_real_file() -> None:
    """The exported filename constant names the shipped data file."""
    assert MODEL_PRICES_FILENAME == "model_prices.json"
    assert MODEL_PRICES_PATH.name == MODEL_PRICES_FILENAME
