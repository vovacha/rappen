"""Every SQL query the app runs. One function per operation; rows map to dataclasses."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from .models import Holding, Subscription, Transaction

Conn = sqlite3.Connection


def _transaction(row: sqlite3.Row) -> Transaction:
    return Transaction(
        id=row["id"],
        account=row["account"],
        date=row["date"],
        description=row["description"],
        amount=row["amount"],
        currency=row["currency"],
        category=row["category"],
        trip=row["trip"],
    )


# --- transactions -----------------------------------------------------------

def _day(value: str | None) -> str | None:
    """Dates are whole days, 'YYYY-MM-DD'; anything else would silently match nothing."""
    if value is None:
        return None
    try:
        valid = len(value) == 10 and bool(datetime.strptime(value, "%Y-%m-%d"))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"not a date (YYYY-MM-DD): {value!r}")
    return value


def _marks(values: list) -> str:
    return ",".join("?" * len(values))


def _where(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    currency: str | None = None,
    categories: list[str] | None = None,
    uncategorized: bool = False,
    direction: str | None = None,
    trip: str | None = None,
    search: str | None = None,
) -> tuple[str, list[object]]:
    """`date_to` is an inclusive day; `categories` is a list of names (the service expands a
    parent to its children); `trip` is a trip name, or '*' for any trip; `search` is a
    substring of the description."""
    clauses: list[str] = []
    params: list[object] = []
    for column, value in (
        ("date >= ?", _day(date_from)),
        ("date <= ?", _day(date_to) and date_to + " 23:59:59"),
        ("account = ?", account),
        ("currency = ?", currency),
        ("upper(description) LIKE ?", f"%{search.upper()}%" if search else None),
    ):
        if value is not None:
            clauses.append(column)
            params.append(value)
    if categories is not None:
        clauses.append(f"category IN ({_marks(categories)})")
        params.extend(categories)
    if uncategorized:
        clauses.append("category IS NULL")
    if direction == "in":
        clauses.append("amount > 0")
    elif direction == "out":
        clauses.append("amount < 0")
    if trip == "*":
        clauses.append("trip IS NOT NULL")
    elif trip is not None:
        clauses.append("trip = ?")
        params.append(trip)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def insert_transactions(conn: Conn, rows: list[Transaction]) -> list[Transaction]:
    """Insert rows not already present (see the UNIQUE key). Returns the ones inserted, with ids."""
    inserted = []
    for t in rows:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO transactions (account, date, description, amount, currency, category) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (t.account, t.date, t.description, t.amount, t.currency, t.category),
        )
        if cursor.rowcount:
            t.id = cursor.lastrowid
            inserted.append(t)
    return inserted


def list_transactions(
    conn: Conn,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    categories: list[str] | None = None,
    uncategorized: bool = False,
    currency: str | None = None,
    direction: str | None = None,
    trip: str | None = None,
    search: str | None = None,
    limit: int | None = 100,
    offset: int = 0,
) -> list[Transaction]:
    where, params = _where(
        date_from=date_from, date_to=date_to, account=account, currency=currency,
        categories=categories, uncategorized=uncategorized, direction=direction, trip=trip,
        search=search,
    )
    page = "LIMIT ? OFFSET ?" if limit is not None else ""
    params.extend([limit, offset] if limit is not None else [])
    rows = conn.execute(
        f"SELECT * FROM transactions {where} ORDER BY date DESC, id DESC {page}", params
    ).fetchall()
    return [_transaction(r) for r in rows]


_BUCKETS = {
    None:       "'total'",
    "month":    "substr(date, 1, 7)",
    "account":  "account",
    "currency": "currency",
    "category": "category",
    "trip":     "trip",
}


def totals(
    conn: Conn, *, group_by: str | None = None, excluded: list[str] = (), **filters
) -> list[sqlite3.Row]:
    """Income/expense/count per (bucket, currency); the service folds currencies to the base one.
    `excluded` categories (transfer=true) are left out; uncategorized rows always count."""
    if group_by not in _BUCKETS:
        raise ValueError(f"unknown group_by {group_by!r}; known: {sorted(k for k in _BUCKETS if k)}")
    where, params = _where(**filters)
    if excluded:
        keep = f"(category IS NULL OR category NOT IN ({_marks(excluded)}))"
        where = f"{where} AND {keep}" if where else f"WHERE {keep}"
        params.extend(excluded)
    return conn.execute(
        f"""
        SELECT {_BUCKETS[group_by]} AS bucket, currency,
               SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS income,
               SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS expense,
               COUNT(*) AS txn_count
        FROM transactions {where}
        GROUP BY bucket, currency
        """,
        params,
    ).fetchall()


def tag_window(conn: Conn, trip: str, date_from: str, date_to: str, categories: list[str]) -> int:
    """Tag the untagged rows of the given categories in the window with the trip."""
    _day(date_from), _day(date_to)
    return conn.execute(
        f"""
        UPDATE transactions SET trip = ?
        WHERE trip IS NULL AND date >= ? AND date <= ? AND category IN ({_marks(categories)})
        """,
        (trip, date_from, date_to + " 23:59:59", *categories),
    ).rowcount


def has_trip(conn: Conn, trip: str) -> bool:
    return conn.execute("SELECT 1 FROM transactions WHERE trip = ? LIMIT 1", (trip,)).fetchone() is not None


def set_trip(conn: Conn, ids: list[int], trip: str | None) -> int:
    if not ids:
        return 0
    return conn.execute(
        f"UPDATE transactions SET trip = ? WHERE id IN ({_marks(ids)})",
        [trip, *ids],
    ).rowcount


def delete_trip(conn: Conn, trip: str) -> int:
    return conn.execute("UPDATE transactions SET trip = NULL WHERE trip = ?", (trip,)).rowcount


def set_category(conn: Conn, ids: list[int], category: str | None) -> int:
    """Assign `category` to many transactions at once (None clears). Returns rows changed."""
    if not ids:
        return 0
    return conn.execute(
        f"UPDATE transactions SET category = ? WHERE id IN ({_marks(ids)})",
        [category, *ids],
    ).rowcount


def clear_categories(conn: Conn, category: str | None) -> int:
    """Uncategorize one category, or every row when `category` is None."""
    where = "category = ?" if category is not None else "category IS NOT NULL"
    params = (category,) if category is not None else ()
    return conn.execute(f"UPDATE transactions SET category = NULL WHERE {where}", params).rowcount


def stored_categories(conn: Conn) -> list[str]:
    rows = conn.execute("SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL").fetchall()
    return [r[0] for r in rows]


def stored_currencies(conn: Conn) -> list[str]:
    rows = conn.execute("SELECT DISTINCT currency FROM transactions").fetchall()
    return [r[0] for r in rows]


def coverage(conn: Conn) -> tuple[int, int]:
    """(total transactions, uncategorized transactions)."""
    total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    uncategorized = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE category IS NULL"
    ).fetchone()[0]
    return total, uncategorized


# --- holdings ---------------------------------------------------------------

def _holding(row: sqlite3.Row) -> Holding:
    return Holding(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        value=row["value"],
        updated_at=row["updated_at"],
    )


def list_holdings(conn: Conn) -> list[Holding]:
    rows = conn.execute("SELECT * FROM holdings ORDER BY name").fetchall()
    return [_holding(r) for r in rows]


def set_holding(conn: Conn, name: str, value: float, description: str | None, now: str) -> Holding:
    conn.execute(
        """
        INSERT INTO holdings (name, description, value, updated_at)
        VALUES (:name, :description, :value, :now)
        ON CONFLICT (name) DO UPDATE SET
            description = :description,
            value       = :value,
            updated_at  = :now
        """,
        {"name": name, "description": description, "value": value, "now": now},
    )
    row = conn.execute("SELECT * FROM holdings WHERE name = ?", (name,)).fetchone()
    return _holding(row)


def delete_holding(conn: Conn, name: str) -> int:
    return conn.execute("DELETE FROM holdings WHERE name = ?", (name,)).rowcount


# --- subscriptions ----------------------------------------------------------

def _subscription(row: sqlite3.Row) -> Subscription:
    return Subscription(
        id=row["id"],
        name=row["name"],
        amount=row["amount"],
        currency=row["currency"],
        cadence=row["cadence"],
        payment=row["payment"],
        active=bool(row["active"]),
        notes=row["notes"],
    )


def list_subscriptions(conn: Conn, *, active_only: bool = False) -> list[Subscription]:
    where = "WHERE active = 1" if active_only else ""
    rows = conn.execute(f"SELECT * FROM subscriptions {where} ORDER BY name").fetchall()
    return [_subscription(r) for r in rows]


def get_subscription(conn: Conn, name: str) -> Subscription | None:
    row = conn.execute("SELECT * FROM subscriptions WHERE name = ?", (name,)).fetchone()
    return _subscription(row) if row else None


def set_subscription(
    conn: Conn,
    name: str,
    amount: float,
    currency: str,
    cadence: str,
    payment: str,
    active: bool,
    notes: str | None,
) -> Subscription:
    conn.execute(
        """
        INSERT INTO subscriptions (name, amount, currency, cadence, payment, active, notes)
        VALUES (:name, :amount, :currency, :cadence, :payment, :active, :notes)
        ON CONFLICT (name) DO UPDATE SET
            amount   = :amount,
            currency = :currency,
            cadence  = :cadence,
            payment  = :payment,
            active   = :active,
            notes    = :notes
        """,
        {
            "name": name, "amount": amount, "currency": currency, "cadence": cadence,
            "payment": payment, "active": int(active), "notes": notes,
        },
    )
    return get_subscription(conn, name)


def delete_subscription(conn: Conn, name: str) -> int:
    return conn.execute("DELETE FROM subscriptions WHERE name = ?", (name,)).rowcount
