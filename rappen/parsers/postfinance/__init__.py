"""Parse a PostFinance PDF account statement.

The statement is a table with columns Date | Text | Credit | Debit | Value | Balance,
but the text has no ruling lines and a single transaction spans several rows (the
counterparty name, address and references follow on their own lines). Two facts make
it parseable:

  * Credit vs debit is encoded purely by horizontal position, not by sign. We read
    word coordinates and classify each amount by the column it right-aligns to.
  * A real transaction row is the only kind of row that has both an amount (in the
    credit or debit column) and a value date. That test excludes the opening/closing
    "Account balance" lines and the "Total" line.

PostFinance prints only a date; see `stamp` for the synthetic seconds.
The first page names the bank, which is how the file is recognised, and its
"IBAN ... CHF" line gives the account currency.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pdfplumber

from ...models import ParsedTransaction
from .. import stamp

KIND = "pdf"
SIGNATURE = "PostFinance"    # the brand; "Ltd", "AG" or "SA" follows it by statement language

# Column bounds in points: amounts by their right edge (x1), everything else by its left (x0).
_CREDIT_DEBIT_SPLIT = 394.0   # midpoint between the credit (354.3) and debit (433.7) right edges
_AMOUNT_X0_MIN = 300.0        # amounts (incl. thousands groups) start right of the text column
_BALANCE_X0_MIN = 500.0       # the balance column is further right again; only used to bound debits
_TEXT_X0_MIN = 120.0          # text starts right of the booking-date column
_TEXT_X1_MAX = 300.0
_VALUE_DATE_X0_MIN = 440.0
_CONTENT_X0_MIN = 40.0        # drop pre-printed form codes in the far-left margin (x0 ~ 15)

_DATE = re.compile(r"^\d{2}\.\d{2}\.\d{2}$")          # dd.mm.yy (booking or value date)
_NUMBER = re.compile(r"^\d[\d']*(?:\.\d{2})?$")        # amount fragment, possibly a thousands group
_CURRENCY = re.compile(r"IBAN\s+[A-Z]{2}[\dA-Z ]{5,}?\s+(CHF|EUR|USD)")


def _cluster_lines(words: list[dict]) -> list[list[dict]]:
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda w: w["top"]):
        if lines and word["top"] - lines[-1][0]["top"] < 3:
            lines[-1].append(word)
        else:
            lines.append([word])
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def _is_noise(texts: list[str]) -> bool:
    return " ".join(texts).startswith(("Date ", "IBAN", "Account number", "Page "))


def _merge_number(fragments: list[dict]) -> float:
    return float("".join(f["text"] for f in fragments).replace("'", ""))


def _signed_amount(line: list[dict]) -> float | None:
    numbers = [w for w in line if _NUMBER.match(w["text"])]
    credit = [w for w in numbers if _AMOUNT_X0_MIN < w["x1"] < _CREDIT_DEBIT_SPLIT]
    debit = [w for w in numbers if _CREDIT_DEBIT_SPLIT <= w["x1"] < _BALANCE_X0_MIN]
    if credit and not debit:
        return _merge_number(credit)
    if debit and not credit:
        return -_merge_number(debit)
    return None  # neither, or a Total line with both columns filled


def _value_date(line: list[dict]) -> bool:
    return any(_DATE.match(w["text"]) and w["x0"] > _VALUE_DATE_X0_MIN for w in line)


def _booking_date(line: list[dict]) -> str | None:
    for w in line:
        if _DATE.match(w["text"]) and w["x0"] < _TEXT_X0_MIN:
            return w["text"]
    return None


def _text(line: list[dict]) -> str:
    return " ".join(w["text"] for w in line if w["x0"] >= _TEXT_X0_MIN and w["x1"] <= _TEXT_X1_MAX)


def _is_detail(line: list[dict]) -> bool:
    return all(_TEXT_X0_MIN <= w["x0"] and w["x1"] <= _TEXT_X1_MAX for w in line)


def parse(path: str | Path) -> list[ParsedTransaction]:
    transactions: list[ParsedTransaction] = []
    current: ParsedTransaction | None = None
    booking: str | None = None

    with pdfplumber.open(path) as pdf:
        match = _CURRENCY.search(pdf.pages[0].extract_text() or "")
        if match is None:
            raise ValueError(f"{path}: no 'IBAN ... <currency>' line on the first page")
        currency = match.group(1)
        for page in pdf.pages:
            words = [w for w in page.extract_words(x_tolerance=1) if w["x0"] > _CONTENT_X0_MIN]
            for line in _cluster_lines(words):
                if _is_noise([w["text"] for w in line]):
                    continue  # page header; a transaction's details may continue past it

                amount = _signed_amount(line)
                if amount is not None and _value_date(line):
                    booking = _booking_date(line) or booking
                    current = ParsedTransaction(
                        date=datetime.strptime(booking, "%d.%m.%y").strftime("%Y-%m-%d"),
                        description=_text(line),
                        amount=amount,
                        currency=currency,
                    )
                    transactions.append(current)
                elif current is not None and _is_detail(line):
                    current.description = f"{current.description} {_text(line)}".strip()
                else:
                    current = None

    return stamp(transactions)
