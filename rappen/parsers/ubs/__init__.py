"""UBS CSV account export: semicolon-separated, a block of account details above the header,
one currency per account, debits already negative. Description1 is the counterparty followed
by its address; Description2 is the channel (debit card, TWINT, e-banking) and Description3
the transaction number and payment reason, so only the counterparty is kept. Card payments
carry a trade time; TWINT and e-banking rows do not and get the synthetic seconds of `stamp`.
"""

from __future__ import annotations

import csv
from itertools import dropwhile
from pathlib import Path

from ...models import ParsedTransaction
from .. import stamp

KIND = "csv"
SIGNATURE = "Account number:;"


def parse(path: str | Path) -> list[ParsedTransaction]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        table = dropwhile(lambda line: not line.startswith("Trade date;"), handle)
        transactions = [
            ParsedTransaction(
                date=f"{row['Trade date']} {row['Trade time']}".strip(),
                description=row["Description1"].split(";")[0].strip(" /"),
                amount=float(row["Debit"] or row["Credit"]),
                currency=row["Currency"],
            )
            for row in csv.DictReader(table, delimiter=";")
        ]
    stamp([t for t in transactions if len(t.date) == len("YYYY-MM-DD")])
    return transactions
