"""MCP server exposing the service API as tools. Run with: python -m rappen.mcp_server"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import service

mcp = FastMCP("rappen")


def _dump(value: Any) -> Any:
    if isinstance(value, list):
        return [_dump(v) for v in value]
    if isinstance(value, dict):
        return {k: _dump(v) for k, v in value.items()}
    return asdict(value) if hasattr(value, "__dataclass_fields__") else value


@mcp.tool()
def import_file(path: str) -> dict:
    """Import a bank export; the bank is detected from the file and is the account. An export
    of a bank without a parser is rejected with the list of known banks. Returns the counts and
    the new rows (capped at 200), each with the category the rules gave it or null."""
    return _dump(service.import_file(path))


@mcp.tool()
def list_transactions(
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    category: str | None = None,
    uncategorized: bool = False,
    currency: str | None = None,
    direction: str | None = None,
    trip: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List transactions with optional filters, newest first. `account` is a bank, as named by
    an import result or by `cash_flow(group_by='account')`; `category` a category name,
    covering its children; `direction` 'in' or 'out'; `uncategorized=True` returns only rows
    with no category; `trip` a trip name ('*' = any); `search` a substring of the description.
    Use `cash_flow` for totals — this list caps at `limit` rows and is for inspecting rows."""
    return _dump(service.list_transactions(
        date_from=date_from, date_to=date_to, account=account,
        category=category, uncategorized=uncategorized, currency=currency,
        direction=direction, trip=trip, search=search, limit=limit, offset=offset,
    ))


@mcp.tool()
def cash_flow(
    date_from: str | None = None,
    date_to: str | None = None,
    group_by: str | None = None,
    account: str | None = None,
    currency: str | None = None,
    category: str | None = None,
    trip: str | None = None,
    include_transfers: bool = False,
) -> dict:
    """Income, expense and net in the base currency (named in the result) over a period
    (dates inclusive), plus buckets by
    `group_by`: 'month', 'account', 'currency', 'category' (parents with children nested,
    largest expense first) or 'trip' (tagged rows only); None gives totals only. `category`
    filters to one category and its children; `trip` to one trip by name ('*' = any trip).
    Transfer categories are excluded unless `include_transfers=True`. Runs in SQLite — use this
    for any question that ends in a number."""
    return _dump(service.cash_flow(
        group_by=group_by, date_from=date_from, date_to=date_to, account=account,
        currency=currency, category=category, trip=trip, include_transfers=include_transfers,
    ))


@mcp.tool()
def set_category(ids: list[int], category: str | None = None) -> int:
    """Assign a category (by name) to a batch of transactions in one call, or pass
    category=None to clear them. Returns how many rows changed. Group a batch by
    intended category and call this once per category."""
    return service.set_category(ids, category)


@mcp.tool()
def list_categories() -> list[dict]:
    """List all categories: name, parent, trip (true = tagged by set_trip) and transfer
    (true = money moved, not earned or spent; excluded from cash_flow)."""
    return _dump(service.list_categories())


@mcp.tool()
def categorize() -> dict:
    """Assign categories.yaml rules to every uncategorized transaction (never overwrites a
    stored category). Returns coverage stats and `unknown_categories`: names stored on rows
    that the yaml no longer has. Imports and set_rules already do this; run it after
    clear_categories."""
    return service.categorize()


@mcp.tool()
def get_rules() -> str:
    """The current categories.yaml (taxonomy + rules) as text."""
    return service.get_rules()


@mcp.tool()
def set_rules(text: str) -> dict:
    """Replace categories.yaml with `text` (the whole file the user sent). It is validated
    first; a broken file is rejected and the old one kept. The new rules then fill every
    uncategorized row; stored categories are never overwritten. Returns the category count and
    coverage stats."""
    return service.set_rules(text)


@mcp.tool()
def clear_categories(category: str | None = None) -> int:
    """Uncategorize every transaction in `category`, or ALL transactions when None. Returns
    the count cleared. Follow with categorize() to let the current rules fill them again; rows
    that were set by hand must be set again."""
    return service.clear_categories(category)


@mcp.tool()
def set_trip(name: str, date_from: str, date_to: str) -> dict:
    """Tag every still-untagged row of a trip category (food, transport, accommodation...) in
    the inclusive window with the trip name. Refuses while the window has uncategorized rows.
    Returns `tagged` (rows tagged by this call), `skipped` (rows of the window still without a
    trip) and every row of the window (capped at 200) with `trip` set or null. A trip is only
    its name on rows: list them with `cash_flow(group_by='trip')`. Use `set_trip_rows` to add
    pre-paid bookings or remove strays."""
    return _dump(service.set_trip(name, date_from, date_to))


@mcp.tool()
def set_trip_rows(ids: list[int], trip: str | None = None) -> int:
    """Attach transactions to an existing trip by name, or detach them with trip=None.
    Returns rows changed."""
    return service.set_trip_rows(ids, trip)


@mcp.tool()
def delete_trip(name: str) -> int:
    """Untag every transaction of the trip; returns the count."""
    return service.delete_trip(name)


@mcp.tool()
def net_worth() -> dict:
    """Net worth in the base currency: the sum of the hand-maintained holdings (bank balances, pillar 2/3,
    deposits, crypto and stocks, loans out, debts), plus the holdings themselves."""
    return _dump(service.net_worth())


@mcp.tool()
def set_holding(name: str, value: float, description: str | None = None) -> dict:
    """Create or update a holding by name. `value` is in the base currency; positive = asset
    or receivable, negative = debt."""
    return _dump(service.set_holding(name, value, description))


@mcp.tool()
def delete_holding(name: str) -> int:
    """Delete a holding by name; returns the count."""
    return service.delete_holding(name)


@mcp.tool()
def list_subscriptions(active_only: bool = False) -> list[dict]:
    """List the hand-maintained subscription registry (recurring commitments). Each row:
    name, amount, currency, cadence ('monthly'/'yearly'), payment ('apple_store'/'paypal'/
    'card'), active, notes. These are declared values, not derived from transactions."""
    return _dump(service.list_subscriptions(active_only=active_only))


@mcp.tool()
def set_subscription(
    name: str,
    amount: float,
    cadence: str,
    payment: str,
    currency: str | None = None,
    active: bool = True,
    notes: str | None = None,
) -> dict:
    """Create or update a subscription by name. `amount` is the per-charge price (positive);
    `cadence` is 'monthly' or 'yearly'; `payment` is 'apple_store', 'paypal', or 'card';
    `currency` defaults to the base currency."""
    return _dump(service.set_subscription(
        name, amount, cadence, payment, currency=currency, active=active, notes=notes,
    ))


@mcp.tool()
def delete_subscription(name: str) -> int:
    """Delete a subscription from the registry by name; returns the count."""
    return service.delete_subscription(name)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
