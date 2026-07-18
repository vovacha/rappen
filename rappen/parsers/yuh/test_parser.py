from pathlib import Path

from rappen.parsers import yuh

STATEMENT = Path(__file__).parent / "statement.csv"


def test_rows_and_currencies():
    rows = yuh.parse(STATEMENT)
    assert len(rows) == 16  # 17 rows: a reward, a rejected order and a stock buy carry no cash; 2 rows have two legs
    assert {t.currency for t in rows} == {"CHF", "EUR", "USD"}
    assert not any(word in t.description for t in rows for word in ("declined", "bonus", "Apple"))


def test_exchange_has_two_legs():
    rows = yuh.parse(STATEMENT)
    legs = {(t.amount, t.currency) for t in rows if t.description == "Exchange United States dollars"}
    assert legs == {(2734.31, "CHF"), (-3000.0, "USD")}           # sold 3000 USD for CHF
    auto = {(t.amount, t.currency) for t in rows if t.description == "Autoexchange Swiss francs"}
    assert auto == {(-582.83, "CHF"), (584.86, "EUR")}            # both legs in DEBIT/CREDIT


def test_card_refund_is_positive_and_names_are_unquoted():
    rows = yuh.parse(STATEMENT)
    assert any(t.description == "Sixt Car Rental" and t.amount == 9.27 for t in rows)
    assert not any('"' in t.description for t in rows)


def test_identical_rows_get_successive_seconds():
    rows = yuh.parse(STATEMENT)
    sanitas = [t.date for t in rows if t.description.startswith("Transfer to Sanitas")]
    assert sanitas == ["2024-05-06 00:00:00", "2024-05-06 00:00:01"]
    twenties = {t.date for t in rows if t.amount == -20.0}
    assert twenties == {"2024-05-22 00:00:00"}                    # different rows, same second
