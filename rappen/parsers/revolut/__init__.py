"""Revolut CSV export, any mix of currencies. Started Date is the timestamp (what the app
shows, stable across settlement); the fee is folded into the amount. Only COMPLETED rows
are real: PENDING ones arrive settled in the next overlapping export, REVERTED/DECLINED
never happened."""

from __future__ import annotations

import csv
from pathlib import Path

from ...models import ParsedTransaction

KIND = "csv"
SIGNATURE = "Started Date"


def parse(path: str | Path) -> list[ParsedTransaction]:
    with open(path, newline="", encoding="utf-8") as handle:
        return [
            ParsedTransaction(
                date=row["Started Date"],
                description=row["Description"],
                amount=float(row["Amount"]) - float(row["Fee"]),
                currency=row["Currency"],
            )
            for row in csv.DictReader(handle)
            if row["State"] == "COMPLETED"
        ]
