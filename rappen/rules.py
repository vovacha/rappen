"""categories.yaml -> taxonomy + classify(), base currency and rates. The file is personal
config in the home directory (see RULES.md); `load()` reads it on every call so an updated
file needs no restart."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import yaml

from .config import EXAMPLE_RULES, rules_path
from .models import Category

_OWNER_PRIORITY = 100
_FLAGS = {"trip": False, "transfer": False}
_KEYS = {"name", "children", "match", *_FLAGS}
_PATTERN_KEYS = {"pattern", "not", "sign", "min_amount", "max_amount", "owner_mention"}
_TOP_KEYS = {"owner", "currency", "rates", "categories"}

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


class Rules:
    def __init__(self, text: str):
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise ValueError(f"invalid yaml: {e}") from None
        if not isinstance(doc, dict) or not isinstance(doc.get("categories"), list):
            raise ValueError("categories.yaml needs a top-level `categories:` list")
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
    location = rules_path()
    if not location.exists():
        raise ValueError(f"no {location} yet; write one with set_rules, after the worked example "
                         f"{EXAMPLE_RULES} (its header gives the format)")
    return location.read_text(encoding="utf-8")


def load() -> Rules:
    return Rules(text())


def save(text: str) -> Rules:
    """Validate by compiling, then replace the file atomically."""
    rules = Rules(text)
    location = rules_path()
    tmp = location.with_suffix(".yaml.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(location)
    return rules
