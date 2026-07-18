from pathlib import Path

from rappen.parsers import monobank

STATEMENT = Path(__file__).parent / "statement.csv"


def test_rows_have_timestamps_and_their_own_currency():
    rows = monobank.parse(STATEMENT)
    assert len(rows) == 12
    assert {t.currency for t in rows} == {"UAH", "CHF", "USD", "EUR", "CZK"}
    assert rows[0].date == "2026-08-31 11:04:58"
    assert rows[0].description == "From: MONOBANK"


def test_foreign_purchase_keeps_the_merchant_currency():
    legs = {t.description: (t.amount, t.currency) for t in monobank.parse(STATEMENT)}
    assert legs["MIGROLINO"] == (-13.95, "CHF")               # not the -683.76 UAH the card was charged
    assert legs["STATNI PODNIK DOKUM"] == (-1900.0, "CZK")
    assert legs["From EUR card"] == (30.0, "EUR")
    assert legs["Cancellation. YouTube"] == (10.0, "UAH")

