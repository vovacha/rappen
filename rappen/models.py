from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedTransaction:
    date: str                    # ISO 'YYYY-MM-DD HH:MM:SS'
    description: str
    amount: float                # native currency, signed
    currency: str


@dataclass
class Transaction:
    id: int | None
    account: str
    date: str
    description: str
    amount: float
    currency: str
    category: str | None
    trip: str | None = None


@dataclass
class Category:
    name: str
    parent: str | None = None
    trip: bool = False           # counts as trip spend: set_trip tags it inside the window
    transfer: bool = False       # money moved, not earned or spent: left out of cash_flow


@dataclass
class Holding:
    id: int
    name: str
    description: str | None
    value: float                 # in the base currency; positive = asset or receivable, negative = debt
    updated_at: str


@dataclass
class Subscription:
    id: int
    name: str
    amount: float                # per-charge price, positive
    currency: str
    cadence: str                 # 'monthly' | 'yearly'
    payment: str                 # 'apple_store' | 'paypal' | 'card'
    active: bool
    notes: str | None = None


@dataclass
class NetWorth:
    total: float
    currency: str                # the base currency, from config.yaml
    holdings: list[Holding]


@dataclass
class Bucket:
    name: str                    # a month '2026-06', an account, a currency, a category, or a trip
    income: float
    expense: float
    net: float
    txn_count: int
    children: list["Bucket"] = field(default_factory=list)   # sub-categories, for group_by='category'


@dataclass
class CashFlow:
    income: float
    expense: float
    net: float
    txn_count: int
    currency: str                # what the totals are in
    buckets: list[Bucket]


@dataclass
class ImportResult:
    account: str
    parsed: int
    inserted: int
    duplicates: int
    date_from: str | None
    date_to: str | None
    transactions: list[Transaction]   # the new rows, capped (service._MAX_ROWS)
