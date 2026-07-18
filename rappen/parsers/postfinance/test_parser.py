from pathlib import Path

import pytest

from rappen.parsers import postfinance


@pytest.fixture(scope="module")
def rows():
    return postfinance.parse(Path(__file__).parent / "statement.pdf")


def test_running_balance_reconciles(rows):
    """Opening balance plus every signed amount equals the printed closing balance, which
    proves the column-based signs and the thousands separators at once."""
    assert len(rows) == 14
    assert {t.currency for t in rows} == {"CHF"}
    assert round(3221.00 + sum(t.amount for t in rows), 2) == 5257.08


def test_same_day_rows_and_page_breaks(rows):
    first, second = rows[:2]
    assert first.date == second.date == "2026-06-01 00:00:00"       # distinct rows share the day
    row = next(t for t in rows if t.amount == -350.00)
    assert row.description.endswith("SBB CFF FFS BERN (CH)")          # details continue past the header
