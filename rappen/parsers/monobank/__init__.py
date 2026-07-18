"""Monobank CSV statement, exported with English column names: comma-separated, full
timestamps. A card in UAH, but a row is what was paid where it was paid: the operation amount
and currency, so a purchase abroad keeps the merchant's currency and the UAH column is the
bank's conversion. Commission and cashback columns are ignored: neither has been filled in two
years of exports. Every row is settled; a reversal is a "Cancellation." row with a positive
amount."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from ...models import ParsedTransaction

KIND = "csv"
SIGNATURE = "Date and time"


def parse(path: str | Path) -> list[ParsedTransaction]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return [
            ParsedTransaction(
                date=datetime.strptime(row["Date and time"], "%d.%m.%Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S"),
                description=row["Description"],
                amount=float(row["Operation amount"]),
                currency=row["Operation currency"],
            )
            for row in csv.DictReader(handle)
        ]
