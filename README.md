# rappen

Personal finance through your AI agent. Drop your bank statements into the chat and ask: what
did I spend and on what, how does it compare to last year, what did the trip cost, how much is
left over each month. The transactions are the ledger. Holdings and subscriptions are optional
and typed in; net worth is the sum of the holdings. There is no dashboard and nothing runs in
the background: the agent is the interface, over MCP, and [SKILL.md](SKILL.md) is its manual.
Its workflows are the feature list, one line per thing you can say and how the agent answers it.

## Install

Paste this to an agent that speaks MCP and loads skills:

```
Install rappen from https://github.com/vovacha/rappen:

1. Clone it and run `uv sync` in the clone.
2. Register its MCP server for all projects:
     name:      rappen
     transport: stdio
     command:   uv run --directory <absolute path of the clone> python -m rappen.mcp_server
3. Symlink its SKILL.md as a skill named `rappen`.
4. Reload MCP servers, then call `get_config`: "no config.yaml yet" means it works. Only then
   follow the skill's "First run".
```

Setting up is a conversation: the agent asks for your currencies, proposes a small category
tree and which categories are transfers or trip spend, reads the plan back, and writes
`config.yaml` once you agree. Then export a statement from your bank and drop it into the chat.
The bank is recognised from the file; a currency without a rate is refused until you give one,
and merchants that keep coming back become rules.

To update, `git pull` the clone, or ask the agent to. The database
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
- **Nothing is live.** The numbers are as fresh as the last statement you dropped in. Import,
  correct the leftovers, then ask.

## Banks

| Bank | Country | File | Notes |
|---|---|---|---|
| PostFinance | Switzerland | PDF | |
| UBS | Switzerland | CSV | |
| Yuh | Switzerland | CSV | exchanges become two rows; stock and crypto orders are dropped |
| Revolut | Lithuania | CSV | only settled rows are taken: let exports overlap by a few days |
| Monobank | Ukraine | CSV | export with English column names |

Any bank that exports transactions can be added: one folder in `rappen/parsers/`, see
[DEVELOPMENT.md](DEVELOPMENT.md).
