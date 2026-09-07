"""config.yaml: owner, base currency and rates, and the category taxonomy with the rules that
assign it (format in CONFIG.md). It lives in the home directory next to rappen.db; `load()`
reads it on every call, so an updated file needs no restart."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from .models import Category

EXAMPLE = Path(__file__).resolve().parent / "config.example.yaml"


def home() -> Path:
    """Where the personal data lives (rappen.db, config.yaml): ~/.rappen, or $RAPPEN_HOME.
    Created on first use, so there is no setup step."""
    location = Path(os.environ.get("RAPPEN_HOME") or Path.home() / ".rappen")
    location.mkdir(parents=True, exist_ok=True)
    return location


def database_path() -> Path:
    return home() / "rappen.db"


def path() -> Path:
    return home() / "config.yaml"


# config.yaml carries `version`: 1 plus the number of format changes below, one sentence per
# change saying what to edit, appended to and never edited. An older file is rejected with the
# sentences since its version and the agent applies them; nothing rewrites the yaml.
CHANGES: list[str] = []

_OWNER_PRIORITY = 100
_FLAGS = {"trip": False, "transfer": False}
_KEYS = {"name", "children", "match", *_FLAGS}
_PATTERN_KEYS = {"pattern", "not", "sign", "min_amount", "max_amount", "owner_mention"}
_TOP_KEYS = {"version", "owner", "currency", "rates", "categories"}

Predicate = Callable[[str, float], bool]


@dataclass
class _Rule:
    category: str
    priority: int
    predicate: Predicate


def _matcher(pattern: str) -> tuple[Callable[[str], bool], int]:
    """Whole-word match; a `*` at either end relaxes that boundary (GASTR* -> Gastronomie, *BAR -> Mühlibar)."""
    head = "" if pattern.startswith("*") else r"(?<!\w)"
    tail = "" if pattern.endswith("*") else r"(?!\w)"
    needle = pattern.strip("*").upper()
    if not needle:
        raise ValueError(f"empty pattern {pattern!r}")
    regex = re.compile(head + re.escape(needle) + tail)
    return (lambda desc: regex.search(desc) is not None), len(needle)


def _guard(spec: dict) -> Callable[[float], bool]:
    sign = spec.get("sign")
    lo = spec.get("min_amount")
    hi = spec.get("max_amount")

    def ok(amount: float) -> bool:
        if sign == "out" and amount >= 0:
            return False
        if sign == "in" and amount <= 0:
            return False
        if lo is not None and abs(amount) < lo:
            return False
        if hi is not None and abs(amount) >= hi:
            return False
        return True

    return ok


def _compile(pattern: object, owners: list[Callable[[str], bool]]) -> _Rule:
    if isinstance(pattern, str):
        match, priority = _matcher(pattern)
        return _Rule("", priority, lambda desc, amt: match(desc))
    if isinstance(pattern, dict):
        if unknown := set(pattern) - _PATTERN_KEYS:
            raise ValueError(f"{pattern!r}: unknown key {sorted(unknown)}")
        guard = _guard(pattern)
        if pattern.get("owner_mention"):
            return _Rule("", _OWNER_PRIORITY,
                         lambda desc, amt: guard(amt) and any(m(desc) for m in owners))
        if pattern.get("pattern"):
            match, priority = _matcher(str(pattern["pattern"]))
            block = _matcher(str(pattern["not"]))[0] if pattern.get("not") else None
            return _Rule("", priority,
                         lambda desc, amt: match(desc) and not (block and block(desc)) and guard(amt))
    raise ValueError(f"not a rule: {pattern!r}")


def _check(node: object, parent: str | None) -> None:
    if not isinstance(node, dict) or not isinstance(node.get("name"), str):
        raise ValueError(f"a category needs a `name`: {node!r}")
    if unknown := set(node) - _KEYS:
        raise ValueError(f"{node['name']}: unknown key {sorted(unknown)}")
    for key, kind in (("trip", bool), ("transfer", bool), ("match", list), ("children", list)):
        if key in node and not isinstance(node[key], kind):
            raise ValueError(f"{node['name']}: `{key}` must be a {kind.__name__}")
    if parent is not None and "children" in node:
        raise ValueError(f"{node['name']}: categories go two levels deep at most")


def _flatten(nodes: list, parent: str | None, inherited: dict):
    for node in nodes:
        _check(node, parent)
        flags = {k: node.get(k, inherited[k]) for k in inherited}
        yield Category(node["name"], parent, **flags), node.get("match", [])
        yield from _flatten(node.get("children", []), node["name"], flags)


def _check_version(version: object) -> None:
    current = 1 + len(CHANGES)
    if version == current:
        return
    if isinstance(version, int) and 0 < version < current:
        steps = "\n".join(f"  {n}: {change}" for n, change in enumerate(CHANGES[version - 1:], version + 1))
        raise ValueError(f"config.yaml is format {version}; this rappen reads format {current}. "
                         f"Apply these, then set_config:\n{steps}")
    raise ValueError(f"config.yaml needs `version: {current}`")


def _money(doc: dict) -> tuple[str, dict[str, float]]:
    """The base currency totals are in, and one unit of each other currency in it."""
    currency = doc.get("currency")
    rates = doc.get("rates", {})
    if not isinstance(currency, str) or not currency:
        raise ValueError("`currency` must name the currency totals are in")
    if not isinstance(rates, dict) or not all(
        isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
        for k, v in rates.items()
    ):
        raise ValueError("`rates` must map currency codes to positive numbers")
    return currency, {**{k: float(v) for k, v in rates.items()}, currency: 1.0}


class Config:
    def __init__(self, text: str):
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise ValueError(f"invalid yaml: {e}") from None
        if not isinstance(doc, dict):
            raise ValueError(f"config.yaml needs the top-level keys {sorted(_TOP_KEYS)}")
        _check_version(doc.get("version"))
        if not isinstance(doc.get("categories"), list):
            raise ValueError("config.yaml needs a top-level `categories:` list")
        if unknown := set(doc) - _TOP_KEYS:
            raise ValueError(f"unknown top-level key {sorted(unknown)}; known: {sorted(_TOP_KEYS)}")
        owner = doc.get("owner")
        if not isinstance(owner, list) or not owner or not all(isinstance(n, str) and n.strip() for n in owner):
            raise ValueError("`owner` must list your name as banks print it")
        owners = [_matcher(n)[0] for n in owner]
        self.currency, self.rates = _money(doc)
        self.categories: list[Category] = []
        self._rules: list[_Rule] = []
        for category, patterns in _flatten(doc["categories"], None, _FLAGS):
            if any(c.name == category.name for c in self.categories):
                raise ValueError(f"duplicate category {category.name!r}")
            self.categories.append(category)
            for pattern in patterns:
                rule = _compile(pattern, owners)
                rule.category = category.name
                self._rules.append(rule)

    def names(self, *, trip: bool | None = None, transfer: bool | None = None) -> list[str]:
        return [c.name for c in self.categories
                if (trip is None or c.trip == trip) and (transfer is None or c.transfer == transfer)]

    def family(self, name: str) -> list[str]:
        """A category and its children: a parent covers its children in filters."""
        if name not in self.names():
            raise ValueError(f"unknown category {name!r}")
        return [c.name for c in self.categories if name in (c.name, c.parent)]

    def top_level(self, name: str) -> str:
        parents = {c.name: c.parent for c in self.categories}
        while parents.get(name):
            name = parents[name]
        return name

    def classify(self, description: str, amount: float) -> str | None:
        """The category whose longest pattern matches; None when nothing matches or the best
        matches disagree."""
        desc = " ".join(description.upper().split())
        hits = [r for r in self._rules if r.predicate(desc, amount)]
        if not hits:
            return None
        top = max(r.priority for r in hits)
        winners = {r.category for r in hits if r.priority == top}
        return winners.pop() if len(winners) == 1 else None


def text() -> str:
    location = path()
    if not location.exists():
        raise ValueError(f"no {location} yet; write one with set_config, after the worked example "
                         f"{EXAMPLE} (its header gives the format)")
    return location.read_text(encoding="utf-8")


def load() -> Config:
    return Config(text())


def save(text: str) -> Config:
    """Validate by compiling, then replace the file atomically."""
    config = Config(text)
    location = path()
    tmp = location.with_suffix(".yaml.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(location)
    return config
