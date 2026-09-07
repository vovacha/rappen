"""Import one statement file: the bank is sniffed from the file and is the account."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

from . import config, parsers, repository
from .models import ImportResult, ParsedTransaction, Transaction


def _detect_source(path: str | Path) -> str:
    kind, fingerprint = parsers.fingerprint(path)
    banks = parsers.load()
    matches = [name for name, bank in banks.items() if bank.KIND == kind and bank.SIGNATURE in fingerprint]
    if len(matches) != 1:
        problem = f"could be {' or '.join(matches)}" if matches else "not an export of a known bank"
        raise ValueError(f"{path}: {problem} ({', '.join(sorted(banks))})")
    return matches[0]


def _transaction(account: str, p: ParsedTransaction, classify: Callable[[str, float], str | None]) -> Transaction:
    amount = round(p.amount, 2)
    return Transaction(
        id=None, account=account, date=p.date, description=p.description, amount=amount,
        currency=p.currency, category=classify(p.description, amount),
    )


def import_file(conn: sqlite3.Connection, path: str | Path) -> ImportResult:
    account = _detect_source(path)
    cfg = config.load()
    rows = [_transaction(account, p, cfg.classify) for p in parsers.load()[account].parse(path)]
    unknown = {t.currency for t in rows} - set(cfg.rates)
    if unknown:
        raise ValueError(f"{path}: no rate in config.yaml for {sorted(unknown)}; nothing imported")
    new = repository.insert_transactions(conn, rows)
    dates = sorted(t.date for t in rows)
    return ImportResult(
        account=account,
        parsed=len(rows),
        inserted=len(new),
        duplicates=len(rows) - len(new),
        date_from=dates[0] if dates else None,
        date_to=dates[-1] if dates else None,
        transactions=new,
    )
