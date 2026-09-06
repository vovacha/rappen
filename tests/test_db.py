"""The migration mechanism, with a made-up step: the real list is empty until the schema changes."""

from rappen import db, service

RENAME_BACK = "ALTER TABLE holdings RENAME COLUMN value TO value_chf"
RENAME = "ALTER TABLE holdings RENAME COLUMN value_chf TO value"


def _version(conn) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def test_an_old_database_is_migrated_once(monkeypatch):
    with db.session() as conn:                                   # a database from before the step
        conn.executescript(RENAME_BACK)
        assert _version(conn) == 0
    monkeypatch.setattr(db, "MIGRATIONS", [RENAME])
    with db.session() as conn:
        assert _version(conn) == 1
    assert service.set_holding("revolut", 10).value == 10
    with db.session() as conn:                                   # a second connection does not rerun it
        assert _version(conn) == 1


def test_a_fresh_database_skips_the_migrations(monkeypatch):
    monkeypatch.setattr(db, "MIGRATIONS", ["ALTER TABLE holdings RENAME COLUMN nope TO value"])
    with db.session() as conn:
        assert _version(conn) == 1
    assert service.set_holding("revolut", 10).value == 10
