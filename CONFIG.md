# The config file

`config.yaml` is the one file you write: who you are, what totals are in, and the categories
with the rules that assign them. It lives next to `rappen.db` in `~/.rappen`, and nothing works
until it exists: every tool says so and points at `config.example.yaml`, which your agent adapts
and installs with `set_config`. Every command reads the file, so a change needs no restart.

## The file

```yaml
version: 1                    # the file format (see Updates)
owner: [MUSTER, MAX]          # your name as banks print it (see owner_mention)
currency: CHF                 # what totals are in
rates: { EUR: 0.94, USD: 0.80 }   # one unit of each other currency in it

categories:
  - name: Food
    trip: true                # inherited by children
    children:
      - name: Groceries
        match: [MIGROS, COOP]
      - name: Restaurants
        match: [RESTAURANT*, "*BAR"]
  - name: Transfers
    transfer: true
    match:
      - { owner_mention: true }
      - { pattern: "*EXCHANGE*", not: EXCHANGE RATE }
```

Anything else at the top level, in a node or in a pattern, a misspelt key included, is rejected.

## Owner, currency, rates

`owner` lists your name as your banks print it, so the `owner_mention` pattern recognises money
moved between your own accounts; it is required, so no placeholder name can slip through.

`currency` is what every total is in; rows keep their own. It is required too.

`rates` gives one unit of each other currency in it, typed by hand and never fetched, and grows
as needed: a statement in a currency that has no rate is rejected before anything is imported,
naming the currency, so you add the rate and import again. A config that drops a rate the ledger
already holds rows in is rejected too.

## Categories

A node has a `name`, optional `children` (two levels at most), optional `match` patterns, and
two flags that children inherit, both false by default:

- `trip: true` — counts as trip spend (food, transport, accommodation, shopping…); `set_trip`
  tags it inside a trip's window. Rent, insurance, salary and subscriptions stay unflagged.
- `transfer: true` — money moved, not earned or spent (own-account transfers, loans); left out
  of `cash_flow` unless asked for. A total over such a category is both legs of every move and
  means nothing; what you hold at the other end (3a, a loan out) is a holding.

A transaction stores the category name; there is no categories table. Renaming one in the yaml
creates a new category; rows keep the old name (`cash_flow` shows it as its own bucket) until you
clear that category (`clear_categories`) and run `categorize`.

## Patterns

Matching runs on the upper-cased description with whitespace collapsed.

| form | meaning |
|---|---|
| `MIGROS` | whole word or phrase; `MIGROS` matches "Migros Zürich", not "MIGROSBANK" |
| `GASTR*`, `*BAR`, `*CAFE*` | a `*` at either end relaxes that word boundary |
| `{ pattern: APPLE, not: APPLE PAY, max_amount: 20 }` | the same, with guards |
| `{ owner_mention: true, sign: in }` | the description names an `owner` entry |

Guards, all optional and all required to hold: `sign: in` or `out`, `min_amount` and
`max_amount` (absolute value, max exclusive), `not` (a pattern that must be absent).

The longest matching pattern wins across all categories. A tie between two categories, or no
match at all, leaves the row uncategorized for you to set by hand. `owner_mention` outranks
everything, so keep `owner` to what only your own transfers print: an employer or landlord
whose name contains yours would land in Transfers.

## Changing the config

Ask your agent for the change, or edit the yaml yourself and send it the file; either way it
installs the result with `set_config`, as `rappen config set FILE` does from the command line.
The new file is validated first; a broken one is rejected and the old one kept. The new rules
then fill every row that has no category, and the result says how many are still uncategorized.
Set those by hand (`set_category`).

A stored category is never overwritten, whether a rule or your hand wrote it. When a rule was
wrong, or a category splits into new ones, clear it and let the rules fill it again:
`clear_categories` for that category, then `categorize`; rows that were set by hand in it are
set again. `clear_categories` without a category is the full redo.

## Updates

`version` numbers the file format. An update that changes it rejects your file, from every tool,
with one line per change since your version saying what to edit; make those edits and
`set_config` again. Nothing rewrites the file for you.

A rule earns its place by matching repeatedly. Ambiguous merchants (Amazon, Apple devices),
person-to-person payments and one-off foreign merchants are set by hand and never get a rule.
The exception is a merchant you keep setting by hand: name it, so the rules do it for you.
Never edit a description to dodge a rule; it is part of the dedup key.
`tests/test_config.py` holds the tricky cases against the example file; add yours there when a
pattern surprised you.
