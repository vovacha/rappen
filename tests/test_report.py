"""Cash-flow totals/buckets, trips, and the categorize workflow, through the service layer."""

import pytest

from rappen import service


@pytest.fixture
def ledger(statements):
    service.import_file(statements["revolut"])
    return service


def test_transfers_excluded_by_default(ledger):
    default = ledger.cash_flow()
    included = ledger.cash_flow(include_transfers=True)
    assert included.txn_count > default.txn_count
    assert included.income_chf != default.income_chf
    assert default.buckets == []


def test_category_buckets_nest_children(ledger):
    buckets = {b.name: b for b in ledger.cash_flow(group_by="category").buckets}
    assert "Transfers" not in buckets
    assert "Food" in buckets
    assert {c.name for c in buckets["Food"].children} <= {"Groceries", "Restaurants"}
    assert buckets["Food"].expense_chf == pytest.approx(sum(c.expense_chf for c in buckets["Food"].children), abs=0.02)
    assert "Transfers" in {b.name for b in ledger.cash_flow(group_by="category", include_transfers=True).buckets}


def test_category_filter_covers_children_in_both_views(ledger):
    groceries = ledger.cash_flow(category="Groceries", currency="CHF")
    assert groceries.txn_count == len(ledger.list_transactions(category="Groceries", limit=1000))
    assert groceries.income_chf == 0
    food = ledger.cash_flow(category="Food")
    by_category = {b.name: b for b in ledger.cash_flow(group_by="category").buckets}
    assert food.txn_count == by_category["Food"].txn_count > groceries.txn_count
    assert len(ledger.list_transactions(category="Food", limit=1000)) == food.txn_count


def test_unknown_category_is_rejected(ledger):
    row = ledger.list_transactions(limit=1)[0]
    with pytest.raises(ValueError):
        ledger.set_category([row.id], "Nope")
    with pytest.raises(ValueError, match="Nope"):
        ledger.cash_flow(category="Nope")
    with pytest.raises(ValueError, match="Nope"):
        ledger.list_transactions(category="Nope")


def test_categorize_names_stored_categories_the_yaml_lost(ledger):
    assert ledger.categorize()["unknown_categories"] == []
    renamed = ledger.get_rules().replace("- name: Groceries\n", "- name: Bread\n")
    assert ledger.set_rules(renamed)["unknown_categories"] == ["Groceries"]


def test_dates_must_be_whole_days(ledger):
    for bad in ("2026-8-1", "2026-06-25 10:00:00"):
        with pytest.raises(ValueError):
            ledger.cash_flow(date_from=bad)
    with pytest.raises(ValueError):
        ledger.set_trip("x", "2026-06-01", "2026-06-31")


def test_date_to_is_inclusive(ledger):
    rows = ledger.list_transactions(date_from="2026-06-25", date_to="2026-06-25", limit=1000)
    assert rows and all(r.date.startswith("2026-06-25") for r in rows)


def test_set_trip_refuses_while_the_window_has_uncategorized_rows(ledger):
    with pytest.raises(ValueError, match="uncategorized"):
        ledger.set_trip("June", "2026-06-01", "2026-06-30")   # the Amazon refund has no rule
    assert ledger.cash_flow(trip="*").txn_count == 0


def test_trip_tags_trip_categories_and_lists_the_window(ledger):
    pending = ledger.list_transactions(uncategorized=True, date_from="2026-06-01", date_to="2026-06-30")
    ledger.set_category([t.id for t in pending], "General")
    result = ledger.set_trip("June", "2026-06-01", "2026-06-30")
    rows = result["transactions"]
    trip_categories = {c.name for c in ledger.list_categories() if c.trip}
    tagged = [t for t in rows if t.trip == "June"]
    assert result["tagged"] == len(tagged) > 0
    assert result["skipped"] == len(rows) - len(tagged) > 0
    assert all(t.category in trip_categories for t in tagged)
    assert all(t.category not in trip_categories for t in rows if t.trip is None)
    assert all("2026-06" in t.date for t in rows)
    again = ledger.set_trip("June", "2026-06-01", "2026-06-30")
    assert (again["tagged"], again["skipped"]) == (0, result["skipped"])         # a rerun changes nothing

    by_trip = {b.name: b for b in ledger.cash_flow(group_by="trip").buckets}
    assert set(by_trip) == {"June"}                                            # no bucket for untagged rows
    assert by_trip["June"].txn_count == len(tagged)
    assert ledger.cash_flow(trip="*").txn_count == len(tagged)

    ledger.set_trip_rows([tagged[0].id], None)
    assert ledger.cash_flow(trip="June").txn_count == len(tagged) - 1
    assert ledger.delete_trip("June") == len(tagged) - 1
    assert ledger.cash_flow(trip="*").txn_count == 0


def test_set_trip_rows_requires_existing_trip(ledger):
    with pytest.raises(ValueError):
        ledger.set_trip_rows([1], "nope")


def test_clear_then_categorize_rebuilds(ledger):
    again = ledger.categorize()                                      # a rerun changes nothing
    assert again["categorized_now"] == 0
    assert again["total"] == len(ledger.list_transactions(limit=1000))
    before = again["uncategorized"]
    groceries = ledger.cash_flow(category="Groceries").txn_count
    assert ledger.clear_categories("Groceries") == groceries > 0
    assert ledger.cash_flow(category="Groceries").txn_count == 0
    assert ledger.categorize()["categorized_now"] == groceries
    assert ledger.clear_categories() > groceries
    assert ledger.categorize()["uncategorized"] == before


def test_net_worth_is_the_sum_of_the_holdings(ledger):
    ledger.set_holding("revolut", 1200.5, "all currencies, in CHF")
    ledger.set_holding("pillar3", 10000)
    ledger.set_holding("loan to Jonas", -250)
    assert ledger.net_worth().net_worth_chf == 10950.5
    assert ledger.delete_holding("pillar3") == 1 and ledger.delete_holding("pillar3") == 0
    assert ledger.net_worth().net_worth_chf == 950.5


def test_search_filters_on_description(ledger):
    rows = ledger.list_transactions(search="migros")
    assert rows and all("Migros" in r.description for r in rows)
    assert ledger.list_transactions(search="migros", date_from="2026-06-01") == [r for r in rows if r.date >= "2026-06"]


def test_set_rules_validates_and_fills_blanks(ledger):
    text = ledger.get_rules()
    with pytest.raises(ValueError):
        ledger.set_rules("categories: nope")
    assert ledger.get_rules() == text
    migros = ledger.list_transactions(category="Groceries", limit=1000)
    assert migros and ledger.clear_categories("Groceries") == len(migros)
    moved = text.replace("          - MIGROS\n", "").replace("- name: Restaurants\n        match:\n", "- name: Restaurants\n        match:\n          - MIGROS\n")
    result = ledger.set_rules(moved)
    assert result["categorized_now"] == len(migros)                  # filled the blanks, nothing else
    now = {t.id: t.category for t in ledger.list_transactions(limit=1000)}
    assert {now[m.id] for m in migros if "Migros" in m.description} == {"Restaurants"}
