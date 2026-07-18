from __future__ import annotations

import os
from pathlib import Path

# Units of CHF per one unit of the currency, for aggregates only; transactions stay native.
RATES: dict[str, float] = {
    "CHF": 1.0,
    "EUR": 0.94,
    "USD": 0.80,
    "UAH": 0.019,
    "CZK": 0.038,
}

_REPO = Path(__file__).resolve().parents[1]
EXAMPLE_RULES = _REPO / "categories.example.yaml"


def home() -> Path:
    """Where the personal data lives (rappen.db, categories.yaml): $RAPPEN_HOME, else the checkout."""
    return Path(os.environ.get("RAPPEN_HOME") or _REPO)


def database_path() -> Path:
    return home() / "rappen.db"


def rules_path() -> Path:
    return home() / "categories.yaml"
