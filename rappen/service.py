"""The application's core API. MCP tools and the CLI both call these functions and
nothing else; each opens a database session, so callers never touch SQL or connections.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from . import config, db, importer, repository
from .models import (
    Bucket, CashFlow, Category, Holding, ImportResult, NetWorth, Subscription, Transaction,
)


_MAX_ROWS = 200   # rows a mutation lists back; a routine month or trip fits, an initial setup does not


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def import_file(path: str | Path) -> ImportResult:
    with db.session() as conn:
        result = importer.import_file(conn, path)
    result.transactions = result.transactions[:_MAX_ROWS]
    return result


def list_transactions(*, category: str | None = None, **filters) -> list[Transaction]:
    categories = config.load().family(category) if category is not None else None
    with db.session() as conn:
        return repository.list_transactions(conn, categories=categories, **filters)


def cash_flow(
    *, group_by: str | None = None, category: str | None = None, trip: str | None = None,
    include_transfers: bool = False, **filters
) -> CashFlow:
    """Income/expense/net in the base currency for the filtered rows, plus one bucket per `group_by` value
    (month, account, currency, category, trip). Category buckets are top-level parents with
    their children nested; trip buckets are only trips. Transfer categories are excluded
    unless `include_transfers`."""
    cfg = config.load()
    excluded = [] if include_transfers else cfg.names(transfer=True)
    categories = cfg.family(category) if category is not None else None
    if group_by == "trip" and trip is None:
        trip = "*"
    with db.session() as conn:
        rows = repository.totals(conn, group_by=group_by, excluded=excluded, categories=categories,
                                 trip=trip, **filters)
    unrated = {r["currency"] for r in rows} - set(cfg.rates)
    if unrated:
        raise ValueError(f"no rate in config.yaml for {sorted(unrated)}, which the ledger holds rows in")

    def label(key: object) -> str:
        return key or "uncategorized" if group_by == "category" else str(key)

    sums: dict[object, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    children: dict[object, dict[object, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0]))
    total = [0.0, 0.0, 0]
    for r in rows:
        rate = cfg.rates[r["currency"]]
        add = (r["income"] * rate, r["expense"] * rate, r["txn_count"])
        key = r["bucket"]
        if group_by == "category" and key:
            top = cfg.top_level(key)
            if top != key:
                _accumulate(children[top][key], add)
            key = top
        _accumulate(sums[key], add)
        _accumulate(total, add)

    buckets = [
        _bucket(label(key), acc, [_bucket(label(ck), cacc) for ck, cacc in sorted(children[key].items(), key=lambda kv: -kv[1][1])])
        for key, acc in sums.items()
    ]
    buckets.sort(key=lambda b: (-b.expense, b.name) if group_by in ("category", "trip") else b.name)
    if group_by is None:
        buckets = []
    return CashFlow(*_money(total), currency=cfg.currency, buckets=buckets)


def _accumulate(acc: list, add: tuple) -> None:
    acc[0] += add[0]
    acc[1] += add[1]
    acc[2] += add[2]


def _money(acc: list) -> tuple[float, float, float, int]:
    return round(acc[0], 2), round(acc[1], 2), round(acc[0] - acc[1], 2), acc[2]


def _bucket(name: str, acc: list, children: list[Bucket] | None = None) -> Bucket:
    return Bucket(name, *_money(acc), children=children or [])


def categorize() -> dict:
    """Assign the config.yaml rules to every uncategorized transaction; never overwrites a
    stored category. Clear first (clear_categories) to redo one."""
    cfg = config.load()
    classify = cfg.classify
    with db.session() as conn:
        pending = repository.list_transactions(conn, uncategorized=True, limit=None)
        buckets: dict[str, list[int]] = defaultdict(list)
        for t in pending:
            name = classify(t.description, t.amount)
            if name:
                buckets[name].append(t.id)
        categorized = sum(repository.set_category(conn, ids, name) for name, ids in buckets.items())
        total, uncategorized = repository.coverage(conn)
        stored = repository.stored_categories(conn)
    return {
        "total": total,
        "categorized_now": categorized,
        "uncategorized": uncategorized,
        "coverage_pct": round(100 * (total - uncategorized) / total, 1) if total else 0.0,
        "unknown_categories": sorted(set(stored) - set(cfg.names())),   # stored, but not in the yaml
    }


def get_config() -> str:
    return config.text()


def set_config(text: str) -> dict:
    """Replace config.yaml (validated first, and against the currencies the ledger holds)
    and fill uncategorized rows with the new rules. Stored categories are never overwritten."""
    compiled = config.Config(text)
    with db.session() as conn:
        unrated = set(repository.stored_currencies(conn)) - set(compiled.rates)
    if unrated:
        raise ValueError(f"no rate for {sorted(unrated)}, which the ledger holds rows in; nothing changed")
    config.save(text)
    return {"categories": len(compiled.categories), **categorize()}


def clear_categories(category: str | None = None) -> int:
    with db.session() as conn:
        return repository.clear_categories(conn, category)


def set_category(ids: list[int], category: str | None = None) -> int:
    if category is not None and category not in config.load().names():
        raise ValueError(f"unknown category {category!r}")
    with db.session() as conn:
        return repository.set_category(conn, ids, category)


def list_categories() -> list[Category]:
    return config.load().categories


def set_trip(name: str, date_from: str, date_to: str) -> dict:
    """Tag the untagged rows of trip categories in the window, then list every row in the
    window so the caller sees what was tagged and what was not. Refuses while the window has
    uncategorized rows: they must be categorized first, then the tagging is right by construction."""
    trip_categories = config.load().names(trip=True)
    with db.session() as conn:
        window = dict(date_from=date_from, date_to=date_to, limit=None)
        pending = repository.list_transactions(conn, uncategorized=True, **window)
        if pending:
            raise ValueError(f"{len(pending)} uncategorized rows between {date_from} and {date_to}; "
                             "categorize them first")
        tagged = repository.tag_window(conn, name, date_from, date_to, trip_categories)
        rows = repository.list_transactions(conn, **window)
    skipped = sum(1 for r in rows if r.trip is None)
    return {"tagged": tagged, "skipped": skipped, "transactions": rows[:_MAX_ROWS]}


def set_trip_rows(ids: list[int], trip: str | None = None) -> int:
    with db.session() as conn:
        if trip is not None and not repository.has_trip(conn, trip):
            raise ValueError(f"no trip named {trip!r}; create it with set_trip first")
        return repository.set_trip(conn, ids, trip)


def delete_trip(name: str) -> int:
    with db.session() as conn:
        return repository.delete_trip(conn, name)


def net_worth() -> NetWorth:
    """The sum of the hand-maintained holdings; nothing is derived from transactions."""
    with db.session() as conn:
        holdings = repository.list_holdings(conn)
    return NetWorth(total=round(sum(h.value for h in holdings), 2), currency=config.load().currency, holdings=holdings)


def set_holding(name: str, value: float, description: str | None = None) -> Holding:
    with db.session() as conn:
        return repository.set_holding(conn, name, value, description, _now())


def delete_holding(name: str) -> int:
    with db.session() as conn:
        return repository.delete_holding(conn, name)


def list_subscriptions(active_only: bool = False) -> list[Subscription]:
    with db.session() as conn:
        return repository.list_subscriptions(conn, active_only=active_only)


def set_subscription(
    name: str,
    amount: float,
    cadence: str,
    payment: str,
    currency: str | None = None,
    active: bool = True,
    notes: str | None = None,
) -> Subscription:
    """`currency` defaults to the base currency."""
    with db.session() as conn:
        return repository.set_subscription(
            conn, name, amount, currency or config.load().currency, cadence, payment, active, notes
        )


def delete_subscription(name: str) -> int:
    with db.session() as conn:
        return repository.delete_subscription(conn, name)
