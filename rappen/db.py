from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import database_path

_SCHEMA = Path(__file__).resolve().parent / "schema.sql"

# schema.sql is always the current schema, which a fresh database gets whole. A database from
# an earlier version is brought up to it by the steps below, one SQL script per change since the
# first release, in order, appended to and never edited; `PRAGMA user_version` records how many
# a database has had. A step runs before schema.sql, so it sees the old schema.
MIGRATIONS: list[str] = []


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(path) if path is not None else database_path())
    conn.row_factory = sqlite3.Row
    conn.create_function("upper", 1, str.upper, deterministic=True)   # SQLite's own folds ASCII only
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'transactions'").fetchone()
    if exists:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        for step in MIGRATIONS[version:]:
            conn.executescript(step)
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    conn.execute(f"PRAGMA user_version = {len(MIGRATIONS)}")
    conn.commit()


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
