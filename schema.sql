-- rappen schema. Applied idempotently on every connection. Categories and trips are not
-- tables: a transaction carries their names. The taxonomy lives in categories.yaml.

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY,
    account     TEXT    NOT NULL,                 -- the bank the file came from: a package name in rappen/parsers/
    date        TEXT    NOT NULL,                 -- ISO 'YYYY-MM-DD HH:MM:SS'
    description TEXT    NOT NULL,
    amount      REAL    NOT NULL,                 -- native currency; sign is direction (+ in, - out)
    currency    TEXT    NOT NULL,
    category    TEXT,                             -- a name from categories.yaml; NULL = uncategorized
    trip        TEXT,                             -- a trip name; NULL = none

    -- Deduplication across re-imports. Sources without times stamp only identical rows with
    -- distinct seconds, so two different rows on one day can share date and amount; the
    -- description tells them apart.
    UNIQUE (account, date, amount, currency, description)
);

CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions (account, date);

-- What the owner holds, refreshed by hand: bank balances, pillar 2/3, deposits, crypto and
-- stock positions, loans out (positive), debts (negative). Net worth is their sum.
CREATE TABLE IF NOT EXISTS holdings (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    value_chf   REAL    NOT NULL,
    updated_at  TEXT    NOT NULL
);

-- Hand-maintained registry of recurring commitments; deliberately not linked to transactions.
CREATE TABLE IF NOT EXISTS subscriptions (
    id       INTEGER PRIMARY KEY,
    name     TEXT    NOT NULL UNIQUE,
    amount   REAL    NOT NULL,                    -- per-charge price, positive
    currency TEXT    NOT NULL,
    cadence  TEXT    NOT NULL CHECK (cadence IN ('monthly', 'yearly')),
    payment  TEXT    NOT NULL CHECK (payment IN ('apple_store', 'paypal', 'card')),
    active   INTEGER NOT NULL DEFAULT 1,
    notes    TEXT
);
