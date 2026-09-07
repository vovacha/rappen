---
name: rappen
description: "Use when the user asks about personal finances tracked in Rappen: spending, trends, trips, savings, budget, net worth and holdings, subscriptions, checks on single charges, tax figures, statement imports, categories and rules, or the database file. Query and maintain the ledger only through Rappen MCP tools."
license: MIT
metadata:
  version: 11.0.0
  tags: [personal-finance, rappen, mcp, transactions, cash-flow, trips, net-worth, subscriptions]
---

# Personal Finance with Rappen

## Overview

Rappen is a personal ledger. You export the statements from your banks and import them; every transaction gets a category from rules you write yourself in `config.yaml`, what the rules miss you set by hand, and a category set by hand is never overwritten by a rule. Then you ask: what did I spend and on what, how does it compare to last year, what did the trip cost, how much is left over each month. Money moved between your own accounts is a transfer and stays out of those totals. What you own and what you pay for regularly you type in yourself: the holdings add up to your net worth, the subscriptions are a list. Rows keep their own currency; totals are in one base currency, set in `config.yaml` and named in every total. There are no budgets.

## Workflows

What the user says, and how to answer it. Category names are the example yaml's; the user's own apply.

**First run**

- *No rappen tool can be called.*
  Name the host's MCP reload command and stop; nothing here runs without the tools.
- *Set up rappen, or a tool says there is no config.yaml yet.*
  One conversation, in this order, and only the questions: no tool names, step names, or what has or has not been written. Every step is a proposal the user approves or changes; only the currencies are asked outright. Nothing is written before step 5.
  1. **Currencies.** One question, word for word: "What should be your main currency, and which other currencies do you use?" (`currency`). Nothing about country, banks or rates. Rates are never asked for: from the answer, propose one for each other currency yourself, one unit of it in the base currency, and say they are typed in and never fetched, so they update them when the numbers drift.
  2. **Categories.** Propose a small two-level tree in the example's names, fitted to what you know of the user, and say what you fitted. Merchants are not proposed; rules come from the first imports.
  3. **Transfers.** Propose which of those are money moved, not earned or spent: own accounts and exchanges, pension savings, loans. `transfer: true`.
  4. **Trip spend.** Propose which count as trip spend when a trip's window is tagged: food, transport, accommodation, shopping, entertainment, and not rent, insurance, subscriptions. `trip: true`.
  5. **Plan.** Read it all back in one message: currency and rates, the tree with its flags. On agreement write the yaml after the example, keeping its Transfers patterns (they are the supported banks' own strings) and none of its merchants or owner, then `set_config(text)` and say the ledger is ready for its first statement.
- *An import is refused: no rate for a currency.*
  Propose one, have it confirmed, add it under `rates` via `get_config` / `set_config`, import again.
- *A tool says config.yaml is an older format, and lists what to edit.*
  `get_config`, make exactly the listed edits, set `version` to the number named, `set_config`. Nothing else changes.

**Keeping the ledger true**

- *At month end I import the statements.*
  `import_file(path)`, one file at a time.
- *I import a file a second time.*
  Nothing is inserted. A newer export of the same period can still add rows that were pending in the older one.
- *I categorize the leftovers by hand.*
  `list_transactions(uncategorized=true, date_from, date_to)`, then `set_category(ids, name)` once per category.
- *A transfer to my own account at another bank was not recognised.*
  Add the name as that bank printed it under `owner`, via `get_config` / `set_config`; `owner_mention` then catches it.
- *A merchant keeps coming back and I set it by hand every time.*
  `get_config`, add the pattern under its category, `set_config(text)`. Never a rule for a one-off.
- *I want a new category, or to rename or split one.*
  `get_config`, edit the taxonomy, `set_config`. Rows keep the old name until `clear_categories(old_name)` and `categorize`.
- *A rule was wrong.*
  Fix it via `get_config` and `set_config`, then `clear_categories(name)` and `categorize`. `clear_categories()` without a name loses every hand-set category: only on explicit request.
- *I want to edit config.yaml myself.*
  `get_config`, send it as a file; `set_config` with the full text when it comes back.

**Spending overview**

- *What I spent this month by category, and what came in.*
  `cash_flow(date_from, date_to, group_by="category")`.
- *The same for a year, month by month.*
  `group_by="month"` over the year.
- *The same for one bank only, or one currency.*
  `account=` / `currency=`, or `group_by="account"` / `"currency"`.

**Trend detection**

- *Is eating out higher than six months ago?*
  `cash_flow(category="Restaurants", group_by="month")` over both periods.
- *Which categories grew most against last year?*
  One `cash_flow(group_by="category")` per year, bucket by bucket.
- *Groceries feel expensive: more visits, or bigger baskets?*
  `cash_flow(category="Groceries", group_by="month")`: `txn_count` is the visits, `expense / txn_count` the basket.
- *Did the numbers change after I cancelled something, switched insurer, moved, got a raise?*
  Two `cash_flow` calls, before and after the date.

**Trips**

- *I name a trip and its dates.*
  `set_trip(name, date_from, date_to)`, once the window is categorized.
- *The flights and the hotel were paid months earlier.*
  `set_trip_rows(ids, name)`; `set_trip_rows(ids, None)` removes a stray, like a laptop bought on the road.
- *What did the trip cost, in total and per day?*
  `cash_flow(trip=name)`: the cost is `−net`. Per day over the trip's dates, which the user gives; Rappen does not keep them.
- *What did I spend on the trip, per category?*
  `cash_flow(trip=name, group_by="category")`.
- *My companion paid me back part of it. I paid a friend my share of the apartment.*
  `set_category(ids, ...)` to what it was (`Other Income`, `Accommodation`), then `set_trip_rows(ids, name)`; the cost above nets it out.
- *What did I spend on trips this year?*
  `cash_flow(group_by="trip", date_from, date_to)`; `trip="*"` for the total.
- *A ski season is several weekends.*
  `set_trip` once per weekend, same name.
- *This category should count as trip spend.*
  `trip: true` on it via `get_config` / `set_config`, then `set_trip` again with the same name and dates.
- *I got a trip's name or dates wrong.*
  `delete_trip(name)` untags every row, hand-attached ones included; then `set_trip` again and re-attach the pre-paid rows.

**Budget tracking**

- *How much is free on an average month, and what does a rent increase do to it?*
  `cash_flow(group_by="month")`: average `net`, minus the increase.
- *Which large payments come up next quarter: insurance, taxes, yearly renewals?*
  Last year's same quarter with `list_transactions(date_from, date_to, direction="out")`, and the yearly rows of `list_subscriptions`.
- *How many months of expenses does my net worth cover?*
  `net_worth` over the average monthly `expense`.
- *Spent, remaining and pace per category; move an amount between categories; next year's budgets from this year's actuals.*
  Budgets are not built. Say so; offer `cash_flow(group_by="category")` for the year as the starting point.

**Savings**

- *How much did I save so far this year, and where does that pace land in December?*
  `cash_flow(date_from=1 Jan, date_to=today)`: saved is `net`; the pace is net per elapsed month, times twelve.
- *What share of my income stays, now and a year ago?*
  `net / income`, for both windows.

**Subscriptions**

- *Everything that renews, with the yearly total.*
  `list_subscriptions`; the yearly total per currency is monthly × 12 plus the yearly ones.
- *Add or change a subscription. Pause or cancel one.*
  `set_subscription(...)`; paused is `active=false`. `delete_subscription` only on explicit request.

**Net worth**

- *My net worth now: accounts, pillars, deposits, crypto and stocks, loans out, debts.*
  `net_worth`.
- *I checked the app, Revolut holds 4200 now. The yearly 3a statement came.*
  `set_holding("revolut", 4200, "all currencies")`; roughly right, not live.
- *I lent money to a friend.*
  `set_holding(name, amount)` as a receivable; its rows `set_category(ids, "Loans")`. When repaid, `delete_holding(name)` or set what is still open.

**Checks**

- *What is this charge from Tuesday? Did the hotel charge me twice?*
  `list_transactions(search=..., date_from, date_to)`.
- *Did the rent go out, did the salary or the airline refund arrive?*
  `list_transactions(category=..., date_from, date_to)`, or `search`.

**Tax return**

- *What did I pay into 3a this year?*
  `cash_flow(category="Pillar 3a", include_transfers=true, date_from, date_to)`.
- *Health insurance premiums, medical costs, taxes paid, per year.*
  `cash_flow(category=...)` per category and year.

**Backup and restore**

- *Send me the database. Send me the rules.*
  `rappen.db` / `config.yaml` from `~/.rappen` (or `RAPPEN_HOME`, when set), as-is.
- *Here is a rappen.db, use this one.*
  Copy the current one to `rappen.db.bak-<YYYY-MM-DD>`, move the new one into place; no restart needed. Confirm with a `cash_flow` for the current month.

## Rules

1. The ledger is read and changed through the Rappen MCP tools only: never SQL, the files behind them, or a client script around them. Tools that are not callable are reported, not replaced. The exception is Backup and restore above.
2. Totals come from `cash_flow`. `list_transactions` is capped and for looking at rows.
3. Categories are the user's: use the names `list_categories` returns, and change stored categories only when asked or where a workflow above says so.
4. Transfer categories are left out of `cash_flow` unless `include_transfers=true`; a total over them is both legs of every move.
5. Confirm an ambiguous target before a mutation; report from the tool result. A missing capability is named and offered as a Rappen change, not worked around.

## Rendering

The user reads answers on a small screen: proportional text, no code blocks, no tables, short lines. Tool names, workflow names and files never appear. Bold the headline figure, `·` as separator, amounts as `1,234.50 CCY` with their sign (the row's currency, or the base currency for totals), dates as `14 Jul` / `14 Jul 23:36`, child categories as `Parent → Child`. No IDs and no account names on screen; the user points at a row by merchant and amount.

- **Transaction row:** `14 Jul 23:36 · Tesla · Transport · −16.27 CCY`
- **Cash flow:** `**Aug 2026** · in +7,439.10 · out −5,230.40 · net **+2,208.70 CCY**`, then ranked bullets `• Food 1,023.06 CCY (Restaurants 697.52 · Groceries 325.54)`. Month trend: `• Jul · out 4,102.30 · net +1,020.00 CCY` per month.
- **Trip:** `**Balkans 2026** · 1–22 Aug · **3,382.50 CCY** · 107 rows`; with reimbursements `**2,950.00 CCY** (3,740.00 out · 790.00 back)`. Then category bullets.
- **Net worth:** `**Net worth 123,456.78 CCY**`, then `• revolut · 4,200.00 CCY · all currencies` per holding.
- **Subscriptions:** `• Netflix · 9.99 EUR monthly · card`.
- **Import:** `Imported yuh · 34 parsed · 31 new · 3 duplicates · 2 Aug – 30 Aug 2026`, then **Uncategorized (2)** and **Categorized (29)** as transaction rows.
- **Set trip:** `**Balkans 2026** · 1–22 Aug · 100 rows in the trip · 12 rows in those dates are not`, then both lists as transaction rows.
- **Mutation:** one line: `Set 3 rows → Transport` / `Removed 1 row from Balkans 2026`.
