import shutil
from pathlib import Path

import pytest

from rappen import config, parsers

STATEMENTS = {name: next(Path(bank.__file__).parent.glob("statement.*")) for name, bank in parsers.load().items()}


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """A fresh home per test with the example config; the DB is created on first use."""
    monkeypatch.setenv("RAPPEN_HOME", str(tmp_path))
    shutil.copy(config.EXAMPLE, tmp_path / "config.yaml")
    return tmp_path


@pytest.fixture(scope="session")
def statements() -> dict[str, Path]:
    """Every bank's anonymised export, by account name."""
    return STATEMENTS


@pytest.fixture
def conn():
    from rappen import db

    with db.session() as connection:
        yield connection
