from pathlib import Path

from rappen.parsers import ubs

STATEMENT = Path(__file__).parent / "statement.csv"


def test_rows_reconcile_and_keep_only_the_counterparty():
    rows = ubs.parse(STATEMENT)
    assert len(rows) == 9
    assert {t.currency for t in rows} == {"CHF"}
    assert round(sum(t.amount for t in rows), 2) == 548.60          # one credit, eight debits
    assert [t.amount for t in rows if t.amount > 0] == [1000.0]
    assert {t.description for t in rows} >= {"SWISSCOM (SCHWEIZ) AG", "SBB MOBILE", "Peter Meier", "VOLG Laden"}
    assert not any(";" in t.description or "Transaction no" in t.description for t in rows)


def test_card_rows_keep_their_time_and_the_rest_are_stamped():
    rows = ubs.parse(STATEMENT)
    dates = {(t.description, t.amount): t.date for t in rows}
    assert dates[("Tierarztpraxis Muster", -286.10)] == "2026-09-04 15:11:31"   # debit card: trade time
    assert dates[("SBB MOBILE", -12.80)] == "2026-09-02 00:00:00"              # TWINT: no time
    assert dates[("Peter Meier", 1000.0)] == "2026-09-05 00:00:00"             # e-banking: no time
    tickets = sorted(t.date for t in rows if t.description.startswith("SBB CFF") and t.amount == -14.10)
    assert tickets == ["2026-09-04 09:04:03", "2026-09-04 14:57:54"]           # same day and amount, told apart by time
