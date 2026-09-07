"""Command-line interface. Output is JSON so it composes well in scripts and agents."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import service


def _print(value: Any) -> None:
    def encode(v: Any) -> Any:
        if isinstance(v, list):
            return [encode(x) for x in v]
        if isinstance(v, dict):
            return {k: encode(x) for k, x in v.items()}
        return asdict(v) if hasattr(v, "__dataclass_fields__") else v

    print(json.dumps(encode(value), indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rappen", description="Personal finance ledger.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("import", help="Import a statement file; the account is auto-detected.")
    p.add_argument("file")

    p = sub.add_parser("transactions", help="List transactions.")
    p.add_argument("--from", dest="date_from")
    p.add_argument("--to", dest="date_to")
    p.add_argument("--account")
    p.add_argument("--category")
    p.add_argument("--uncategorized", action="store_true")
    p.add_argument("--currency")
    p.add_argument("--direction", choices=["in", "out"])
    p.add_argument("--trip")
    p.add_argument("--search", help="Substring of the description.")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--offset", type=int, default=0)

    p = sub.add_parser("set-category", help="Assign a category to a batch (omit --category to clear).")
    p.add_argument("ids", type=int, nargs="+")
    p.add_argument("--category")

    p = sub.add_parser("cash-flow", help="Income/expense/net in the base currency, optionally bucketed.")
    p.add_argument("--from", dest="date_from")
    p.add_argument("--to", dest="date_to")
    p.add_argument("--group-by", choices=["month", "account", "currency", "category", "trip"])
    p.add_argument("--account")
    p.add_argument("--currency")
    p.add_argument("--category")
    p.add_argument("--trip", help="Trip name, or '*' for any trip.")
    p.add_argument("--include-transfers", action="store_true",
                   help="Include transfer categories (excluded by default).")

    p = sub.add_parser("trips", help="Tag rows with a trip name; list trips with `cash-flow --group-by trip`.")
    ts = p.add_subparsers(dest="action", required=True)
    a = ts.add_parser("set", help="Tag the untagged rows of trip categories in the window.")
    a.add_argument("name"); a.add_argument("date_from"); a.add_argument("date_to")
    a = ts.add_parser("tag", help="Attach rows to an existing trip (omit --trip to detach).")
    a.add_argument("ids", type=int, nargs="+"); a.add_argument("--trip")
    a = ts.add_parser("delete", help="Untag every row of the trip."); a.add_argument("name")

    sub.add_parser("categories", help="List the category taxonomy.")
    sub.add_parser("categorize", help="Apply the config.yaml rules to uncategorized rows.")
    p = sub.add_parser("clear-categories", help="Uncategorize one category (or all rows); pair with categorize.")
    p.add_argument("--category")

    p = sub.add_parser("config", help="Show or replace config.yaml.")
    rs = p.add_subparsers(dest="action", required=True)
    rs.add_parser("get")
    a = rs.add_parser("set", help="Validate FILE, install it as config.yaml, fill uncategorized rows.")
    a.add_argument("file")

    sub.add_parser("net-worth", help="Net worth in the base currency: the sum of the holdings, and the holdings.")
    p = sub.add_parser("holdings", help="Maintain the holdings by hand.")
    hs = p.add_subparsers(dest="action", required=True)
    a = hs.add_parser("set", help="Create or update a holding by name.")
    a.add_argument("name"); a.add_argument("value", type=float, help="In the base currency."); a.add_argument("--description")
    a = hs.add_parser("delete"); a.add_argument("name")

    p = sub.add_parser("subscriptions", help="Manage the manual subscription registry.")
    ss = p.add_subparsers(dest="action", required=True)
    a = ss.add_parser("list")
    a.add_argument("--active", action="store_true", help="Only active subscriptions.")
    a = ss.add_parser("set", help="Create or update a subscription by name.")
    a.add_argument("name")
    a.add_argument("amount", type=float)
    a.add_argument("cadence", choices=["monthly", "yearly"])
    a.add_argument("payment", choices=["apple_store", "paypal", "card"])
    a.add_argument("--currency", help="Defaults to the base currency.")
    a.add_argument("--inactive", action="store_true", help="Mark as cancelled/paused.")
    a.add_argument("--notes")
    a = ss.add_parser("delete"); a.add_argument("name")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.command == "import":
        _print(service.import_file(args.file))
    elif args.command == "transactions":
        _print(service.list_transactions(
            date_from=args.date_from, date_to=args.date_to, account=args.account,
            category=args.category, uncategorized=args.uncategorized,
            currency=args.currency, direction=args.direction, trip=args.trip,
            search=args.search, limit=args.limit, offset=args.offset,
        ))
    elif args.command == "set-category":
        _print({"changed": service.set_category(args.ids, args.category)})
    elif args.command == "cash-flow":
        _print(service.cash_flow(
            group_by=args.group_by, date_from=args.date_from, date_to=args.date_to,
            account=args.account, currency=args.currency, category=args.category,
            trip=args.trip, include_transfers=args.include_transfers,
        ))
    elif args.command == "trips":
        _trips(args)
    elif args.command == "categories":
        _print(service.list_categories())
    elif args.command == "categorize":
        _print(service.categorize())
    elif args.command == "clear-categories":
        _print({"cleared": service.clear_categories(args.category)})
    elif args.command == "config":
        if args.action == "get":
            print(service.get_config(), end="")
        else:
            _print(service.set_config(Path(args.file).read_text(encoding="utf-8")))
    elif args.command == "net-worth":
        _print(service.net_worth())
    elif args.command == "holdings":
        if args.action == "set":
            _print(service.set_holding(args.name, args.value, args.description))
        else:
            _print({"deleted": service.delete_holding(args.name)})
    elif args.command == "subscriptions":
        _subscriptions(args)


def _trips(args: argparse.Namespace) -> None:
    if args.action == "set":
        _print(service.set_trip(args.name, args.date_from, args.date_to))
    elif args.action == "tag":
        _print({"changed": service.set_trip_rows(args.ids, args.trip)})
    elif args.action == "delete":
        _print({"untagged": service.delete_trip(args.name)})


def _subscriptions(args: argparse.Namespace) -> None:
    if args.action == "list":
        _print(service.list_subscriptions(active_only=args.active))
    elif args.action == "set":
        _print(service.set_subscription(
            args.name, args.amount, args.cadence, args.payment,
            currency=args.currency, active=not args.inactive, notes=args.notes,
        ))
    elif args.action == "delete":
        _print({"deleted": service.delete_subscription(args.name)})


if __name__ == "__main__":
    main()
