# rappen

Personal finance for you and your AI agent. Export statements from your banks, import them into
one SQLite ledger, and ask: what did I spend and on what, how does it compare to last year, what
did the trip cost, how much is left over each month, what am I worth. The transactions are the
ledger. Holdings and subscriptions you type in yourself, and your net worth is the sum of the
holdings. There is no dashboard and nothing runs in the background: the agent is the interface,
over MCP, and [SKILL.md](SKILL.md) is its manual. Its workflows are the feature list, one line
per thing you can say and how the agent answers it: read them to see what rappen does.

## Install

Paste this to an agent that speaks MCP and loads skills:

```
Install rappen from https://github.com/vovacha/rappen. Register its MCP server for all
projects: stdio, name `rappen`, command
`uv run --directory <absolute path of the clone> python -m rappen.mcp_server`.
Symlink its SKILL.md as a skill named `rappen`, then follow the skill's "First run".
```

Setting up is a conversation: the agent asks for your name as your banks print it and your
currencies, proposes a category tree and which categories are transfers or trip spend, reads the
plan back, and writes `config.yaml` once you agree. Then export a statement from your bank
and drop it into the chat. The bank is recognised from the file; a currency without a rate is
refused until you give one, and merchants that keep coming back become rules.

To update, `git pull` the clone and run `uv sync` again, or ask the agent to. The database
is brought up to date on the next start. If an update changes the `config.yaml` format, your old
file is rejected with a message saying what to change.

## How it works

- **Transactions are the ledger.** One row per bank line, in its own currency, with a category
  and, when you tag one, a trip. Every total is a sum over them; money moved between your own
  accounts is a transfer and stays out of it.
  - **You own the categories.** Rules in `config.yaml` fill in what they match; the rest you
    set by hand, and a category set by hand is never overwritten ([CONFIG.md](CONFIG.md)).
  - **Re-importing is safe.** A file imported twice adds nothing; a newer export of the same
    period adds only the rows that were pending in the older one.
  - **Rows keep their currency; totals are in yours.** The base currency and the rates are
    numbers you write in `config.yaml`; nothing is fetched.
- **Holdings and subscriptions are typed in**, never derived. Holdings are what you own and owe
  and add up to your net worth; subscriptions are the list of what renews. Both change when you
  say so, and are roughly right rather than live.
- **Two files are the whole state**, `rappen.db` and `config.yaml` in `~/.rappen`. Copy
  them to back up or move.
- **Nothing is live.** Import whenever you want the numbers current, correct the leftovers,
  then ask.

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
