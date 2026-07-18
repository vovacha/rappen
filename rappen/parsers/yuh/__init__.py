"""Yuh CSV export: semicolon-separated, one file for all currencies, dates without times,
names wrapped in doubled quotes. A row can move money in two currencies at once:

  * Autoexchange fills DEBIT and CREDIT with the two legs.
  * "Exchange X" puts one leg in CREDIT (negative when buying X) and the other in
    QUANTITY/ASSET. The fee column is already inside the rate, so it is ignored.

Investment orders, rewards (Swissqoin) and rejected orders are dropped; stocks and crypto
belong in holdings.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from ...models import ParsedTransaction
from .. import stamp

KIND = "csv"
SIGNATURE = "ACTIVITY TYPE"


_SKIP = {"PAYMENT_ORDER_REJECTED", "INVEST_ORDER_EXECUTED", "REWARD_RECEIVED"}


def _legs(row: dict[str, str]) -> list[tuple[float, str]]:
    if row["ACTIVITY TYPE"] in _SKIP:
        return []
    legs = [(float(row[col]), row[f"{col} CURRENCY"]) for col in ("DEBIT", "CREDIT") if row[col]]
    if row["ASSET"]:
        (credit, _), = legs
        quantity = float(row["QUANTITY"])
        legs.append((-quantity if credit > 0 else quantity, row["ASSET"]))
    return legs


def parse(path: str | Path) -> list[ParsedTransaction]:
    transactions: list[ParsedTransaction] = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            day = datetime.strptime(row["DATE"], "%d/%m/%Y").strftime("%Y-%m-%d")
            description = row["ACTIVITY NAME"].strip('"')
            for amount, currency in _legs(row):
                transactions.append(ParsedTransaction(day, description, amount, currency))
    return stamp(transactions)
