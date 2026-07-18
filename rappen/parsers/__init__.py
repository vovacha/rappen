"""One package per bank, discovered by name. Each carries the KIND of its export ('pdf' or
'csv') and a SIGNATURE (text found in the fingerprint of that kind), parse(path) ->
list[ParsedTransaction], its tests and an anonymised statement; the package name is the
account."""

from __future__ import annotations

import importlib
import pkgutil
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType

import pdfplumber

from ..models import ParsedTransaction


def load() -> dict[str, ModuleType]:
    return {
        info.name: importlib.import_module(f"{__name__}.{info.name}")
        for info in pkgutil.iter_modules(__path__) if info.ispkg
    }


def fingerprint(path: str | Path) -> tuple[str, str]:
    """The file's KIND and what a SIGNATURE of that kind is matched against: the text of a
    PDF's first page, else the file's head."""
    with open(path, "rb") as handle:
        head = handle.read(64)
    if head.startswith(b"%PDF"):
        with pdfplumber.open(path) as pdf:
            return "pdf", pdf.pages[0].extract_text() or ""
    return "csv", head.decode("utf-8", errors="ignore")


def stamp(rows: list[ParsedTransaction]) -> list[ParsedTransaction]:
    """Sources that print dates without times: rows arrive with a 'YYYY-MM-DD' date and leave
    with a timestamp. Only identical rows on one day get successive seconds, so a parser change
    that adds or reorders other rows leaves the dedup key of the rest untouched."""
    seen: dict[tuple, int] = defaultdict(int)
    for t in rows:
        key = (t.date, t.description, t.amount, t.currency)
        moment = datetime.strptime(t.date, "%Y-%m-%d") + timedelta(seconds=seen[key])
        seen[key] += 1
        t.date = moment.strftime("%Y-%m-%d %H:%M:%S")
    return rows
