# Development

```bash
uv run --extra dev pytest
```

`RAPPEN_HOME=/some/dir` keeps `rappen.db` and `categories.yaml` outside the checkout; the
directory and the database are created on first use. An installed wheel has no checkout and
uses `~/.rappen`.

## Adding a bank

A bank is a package in `rappen/parsers/`, discovered by name; the package name is the account
its rows land in. It carries `KIND` (`"csv"` or `"pdf"`), a `SIGNATURE` found in that kind's
fingerprint (the first 64 bytes of a CSV, the first page's text of a PDF),
`parse(path) -> list[ParsedTransaction]`, a `test_parser.py`, and an anonymised
`statement.csv` or `statement.pdf`. Rows are signed amounts in their native currency with an
ISO timestamp; a source that prints no times goes through `stamp`, which gives identical rows
on one day successive seconds. A new currency needs a rate in `categories.example.yaml`, which
the tests run with. The shared importer test then covers detection and idempotent re-import for
free.

## Design

Simplicity outranks performance, generality and robustness against events that will not happen
to one person with a few thousand rows. Nothing is optimized; every mechanism is the smallest one
that works. Every feature serves a workflow in SKILL.md; code that serves none is a deletion
candidate.

- **One flat `transactions` table.** Category and trip are names on the row, not foreign keys:
  no joins, no orphans. The taxonomy is the yaml, read from disk on every call, never cached.
- **A connection per call.** No pool, no write-ahead log, no server state. The two files in the
  home directory are the whole state; copy them to back up or move.
- **Migrations are a list of SQL scripts.** `schema.sql` is always the current schema, applied
  idempotently on every connection. A change to it also appends one script to `MIGRATIONS` in
  `db.py`, which every older database runs once on its next start; `PRAGMA user_version` counts
  them. A parser fix that changes stored descriptions or timestamps is not a migration: it
  changes their dedup key, the re-import lists those rows as new, and the old twins are deleted
  by hand.
- **Natural keys instead of bookkeeping.** A row is unique by (account, date, amount, currency,
  description), so re-imports are idempotent through a UNIQUE constraint, not an import log,
  and descriptions are never edited. Holdings and subscriptions are typed in, not derived and
  reconciled.
- **Static rates, capped lists.** Exchange rates are numbers typed into `categories.yaml`, never
  fetched; mutations list back at most 200 rows instead of paginating.
- **A rare problem gets a design, not a guard.** Find the design under which it cannot happen,
  or accept it and write it down. A change that is buggy in several places means the design is
  wrong, not that it needs more fixes.
