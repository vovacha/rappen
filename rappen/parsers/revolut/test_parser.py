from pathlib import Path

from rappen.parsers import revolut

STATEMENT = Path(__file__).parent / "statement.csv"


def test_only_completed_rows():
    rows = revolut.parse(STATEMENT)
    assert len(rows) == 17  # 21 rows: 2 PENDING, 1 REVERTED, 1 DECLINED are skipped
    assert {t.currency for t in rows} == {"CHF", "EUR", "USD"}


def test_fee_is_folded_into_amount():
    amounts = {t.amount for t in revolut.parse(STATEMENT)}
    assert -50.23 in amounts  # Amount -49.73 minus Fee 0.50


def test_started_date_is_used_as_timestamp():
    first = revolut.parse(STATEMENT)[0]
    assert first.date == "2026-04-30 13:51:55"
    assert first.description == "SBB CFF FFS"
