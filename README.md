# rappen

A small personal-finance tool: bank exports in, one SQLite ledger, answers out. It is built for
agent harnesses: **MCP** is the interface, and `SKILL.md` is the agent's manual, which also says
what the tool is for in the owner's words. This file is the developer's.

## What it answers

`SKILL.md` tells it in the owner's words, with the calls that answer each: keeping the ledger true,
spending overview, trend detection, trips, budget tracking, savings, subscriptions, net worth,
checks, tax return, backup and restore.

## Sources

| Bank | Country | Export | What to know |
|---|---|---|---|
| PostFinance | Switzerland | account statement, **PDF** | one currency per statement; dates without times |
| Revolut | Lithuania | transactions export, **CSV** | any mix of currencies; only settled rows are taken, so let exports overlap by a few days |
| Yuh | Switzerland | transactions export, **CSV** | all currencies in one file; an exchange is two rows; stock and crypto orders are dropped, they belong in holdings |
| Monobank | Ukraine | statement export with **English column names**, **CSV** | a UAH card; a purchase abroad keeps the merchant's currency and amount, not the bank's UAH conversion |
| UBS | Switzerland | account transactions export, **CSV** | one currency per account; card payments carry a time, TWINT and e-banking rows do not |

The bank is recognised from the file itself, so an import is just the path, and the bank's name
is the account the rows land in. Any bank that exports transactions can be added: each one is a
folder in `rappen/parsers/`, and this table is the only list of them.

## Concepts

- **Transactions** — signed amounts (`+` in, `−` out) in their native currency; `account` is the
  bank the file came from. A row is unique by (account, date, amount, currency, description),
  which makes re-imports idempotent, so descriptions are never edited. Aggregates convert to
  CHF with the static `RATES` in `config.py`.
- **Categories** — a two-level taxonomy keyed by name, with the rules that assign it, in your own
  `categories.yaml` ([RULES.md](RULES.md)). Rules only fill rows that have no category; a stored
  one is never overwritten, so hand-set categories survive every rules change. Two inherited
  flags: `trip` (what a trip tags) and `transfer` (money moved, not earned or spent; left out of
  `cash_flow`).
- **Trips** — a name on rows, nothing else. `set_trip` tags the trip categories in a date window;
  pre-paid bookings are attached by hand; trip spend is then a filter.
- **Holdings and subscriptions** — typed in by hand, never derived from transactions. Net worth
  is the sum of the holdings.

## Design

Simplicity outranks performance, generality and robustness against events that will not happen
to one person with a few thousand rows. Nothing is optimized; every mechanism is the smallest one
that works. Every feature serves a workflow in SKILL.md; code that serves none is a deletion
candidate.

- **One flat `transactions` table.** Category and trip are names on the row, not foreign keys:
  no joins, no orphans. The taxonomy is the yaml, read from disk on every call, never cached.
- **A connection per call.** No pool, no write-ahead log, no server state. The two files in the
  home directory are the whole state; copy them to back up or move.
- **No migrations.** The schema is applied idempotently on every connection; a schema change is
  a one-off fix on one database. So is a parser fix that changes stored descriptions or
  timestamps: it changes their dedup key, the re-import lists those rows as new, and the old
  twins are deleted by hand.
- **Natural keys instead of bookkeeping.** Re-imports are idempotent through a UNIQUE
  constraint, not an import log. Holdings and subscriptions are typed in, not derived and
  reconciled.
- **Static rates, capped lists.** Exchange rates are three constants in `config.py`; mutations
  list back at most 200 rows instead of paginating.
- **A rare problem gets a design, not a guard.** Find the design under which it cannot happen,
  or accept it and write it down. A change that is buggy in several places means the design is
  wrong, not that it needs more fixes.

## Setup

```bash
uv run rappen init-db        # creates rappen.db and copies categories.example.yaml -> categories.yaml
uv run --extra dev pytest    # tests
```

Both files live in the checkout, gitignored; set `RAPPEN_HOME=/some/dir` to keep them elsewhere
(run `init-db` there first). They are all the state there is. Put your name and your rules into
`categories.yaml` (see RULES.md), then register the MCP server, `python -m rappen.mcp_server`
over stdio, in your harness.
