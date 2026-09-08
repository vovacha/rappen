# rappen

Personal finance through your AI agent. Export a statement from your bank, drop it into the
chat, and ask:

- Where did the money go this month?
- Am I eating out more than a year ago?
- What did the Balkans trip cost, per day?
- If rent goes up 200, what is left each month?
- How many months could I live off what I have?

There is no app and no dashboard: the agent is the interface, over MCP, and [SKILL.md](SKILL.md)
is its manual.

## Setup

Paste this to an agent with MCP and skills:

```
Install rappen from https://github.com/vovacha/rappen:

1. Clone it and run `uv sync` in the clone.
2. Register its MCP server for all projects:
     name:    rappen
     command: uv run --directory <absolute path of the clone> python -m rappen.mcp_server
3. Symlink its SKILL.md as a skill named `rappen`.
4. Reload the MCP servers yourself if you can; if only I can, tell me how and wait.
5. Set up my ledger as SKILL.md says.
```

If the agent stops to ask for a reload, reload and say `Set up rappen`.

Setup is a short conversation: the agent asks which currencies you use, proposes a category
tree, and writes `config.yaml` once you agree. Then drop in your first statement.

To update, `git pull` the clone, or ask the agent to. If an update changes the `config.yaml`
format, your old file is refused with a message saying what to change.

## How it works

- **Transactions.** Every bank line becomes one row, with a category and, once you tag one, a
  trip. Every spending figure is a sum over those rows.
  - **Categories.** Rules in `config.yaml` fill in what they match; the rest you set by hand,
    and a category set by hand is never overwritten ([CONFIG.md](CONFIG.md)).
  - **Transfers.** Money moved between your own accounts is neither income nor spending and
    stays out of the sums.
  - **Trips.** Name a trip and its dates; the food, transport and hotels in that window are the
    trip's cost. Flights paid earlier you attach by hand.
  - **Currencies.** Rows stay in the currency they were paid in; sums are in the currency you
    chose at setup.
- **Holdings.** What you own and owe, typed in. Their sum is your net worth.
- **Subscriptions.** The list of what renews, typed in.
- **Two files are the whole state**, `rappen.db` and `config.yaml` in `~/.rappen`. Copy them to
  back up or move.
- **Nothing is live.** The numbers are as fresh as the last statement you dropped in.

The whole data model:

```
transaction    date · description · amount · currency · account · category · trip
holding        name · value · description
subscription   name · amount · currency · monthly | yearly · active
config.yaml    currency · rates · categories, each with its rules and transfer / trip flags
```

## Supported banks

| Bank | Country | File | Notes |
|---|---|---|---|
| PostFinance | Switzerland | PDF | |
| UBS | Switzerland | CSV | |
| Yuh | Switzerland | CSV | exchanges become two rows; stock and crypto orders are dropped |
| Revolut | Lithuania | CSV | only settled rows are taken: let exports overlap by a few days |
| Monobank | Ukraine | CSV | export with English column names |

Any bank that exports transactions can be added: one folder in `rappen/parsers/`, see
[DEVELOPMENT.md](DEVELOPMENT.md).
