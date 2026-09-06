# rappen

Personal finance for you and your AI agent. Export statements from your banks, import them into
one SQLite ledger, and ask the agent: what did I spend and on what, how does it compare to last
year, what did the trip cost, how much is left over each month, what am I worth. There is no
dashboard, and nothing runs in the background: the agent is the interface, over
[MCP](https://modelcontextprotocol.io), and [SKILL.md](SKILL.md) is its manual. Read it to see
every question it answers and how.

## Install

You need [uv](https://docs.astral.sh/uv/) and an agent harness that speaks MCP and loads skills.
Hand the rest to the agent:

> Clone `https://github.com/vovacha/rappen.git` to `~/rappen` and run `uv sync` in it. Register
> its MCP server under the name `rappen`, for every project rather than the current directory: stdio, command
> `uv run --directory <absolute path of ~/rappen> python -m rappen.mcp_server` (the host starts
> it without a shell, so `~` is not expanded). Install `~/rappen/SKILL.md` as a skill named
> `rappen`, as a symlink so a `git pull` updates it. Then follow the skill's "First run"
> workflow to write my `categories.yaml`.

Setting up is a conversation: the agent asks for your name as your banks print it and your
currencies, proposes a category tree and which categories are transfers or trip spend, reads the
plan back, and writes `categories.yaml` once you agree. Then export a statement from your bank
and drop it into the chat. The bank is recognised from the file; a currency without a rate is
refused until you give one, and merchants that keep coming back become rules.

To update, `git pull` in `~/rappen` and run `uv sync` again. The database is brought up to date
on the next start; a change to the `categories.yaml` format is announced by the tools and is
yours to make.

## Banks

| Bank | Country | File | Notes |
|---|---|---|---|
| PostFinance | Switzerland | PDF | account statement |
| UBS | Switzerland | CSV | account transactions export |
| Yuh | Switzerland | CSV | exchanges become two rows; stock and crypto orders are dropped |
| Revolut | Lithuania | CSV | only settled rows are taken: let exports overlap by a few days |
| Monobank | Ukraine | CSV | export with English column names |

Any bank that exports transactions can be added: one folder in `rappen/parsers/`, see
[DEVELOPMENT.md](DEVELOPMENT.md).

## What to expect

- **Two files are the whole state**, `rappen.db` and `categories.yaml` in the checkout. Copy
  them to back up or move.
- **Re-importing is safe.** A file imported twice adds nothing; a newer export of the same period
  adds only the rows that were pending in the older one.
- **You own the categories.** Rules in `categories.yaml` fill in what they match; the rest you set
  by hand, and a category set by hand is never overwritten ([RULES.md](RULES.md)).
- **Rows keep their currency; totals are in yours.** The base currency and the rates are
  numbers you write in `categories.yaml`; nothing is fetched.
- **Holdings and subscriptions are typed in**, never derived. Net worth is the sum of the
  holdings.
- **Nothing is live.** Import at month end, correct the leftovers, then ask.
