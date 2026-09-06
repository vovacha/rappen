from __future__ import annotations

import os
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parent
_CHECKOUT = _PACKAGE.parent if (_PACKAGE.parent / "pyproject.toml").exists() else None
EXAMPLE_RULES = _PACKAGE / "categories.example.yaml"


def home() -> Path:
    """Where the personal data lives (rappen.db, categories.yaml): $RAPPEN_HOME, else the
    checkout, else ~/.rappen for an installed package. Created on first use, so there is no
    setup step."""
    path = Path(os.environ.get("RAPPEN_HOME") or _CHECKOUT or Path.home() / ".rappen")
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return home() / "rappen.db"


def rules_path() -> Path:
    return home() / "categories.yaml"
