from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import database_path

_SCHEMA = Path(__file__).resolve().parents[1] / "schema.sql"


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(path) if path is not None else database_path())
    conn.row_factory = sqlite3.Row
    conn.create_function("upper", 1, str.upper, deterministic=True)   # SQLite's own folds ASCII only
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    return conn


@contextmanager
def session(path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """A connection that commits on success, rolls back on error, and always closes."""
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
