-- ============================================================
-- sql/schema/01_create_tables.sql
-- Retail Sales Analysis — Schema
-- ============================================================

DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS products;
DROP VIEW IF EXISTS vw_monthly_summary;
DROP VIEW IF EXISTS vw_store_kpis;
DROP VIEW IF EXISTS vw_category_performance;

CREATE TABLE transactions (
    transaction_id  TEXT    PRIMARY KEY,
    date            TEXT    NOT NULL,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    quarter         TEXT    NOT NULL,
    day_of_week     TEXT    NOT NULL,
    is_weekend      INTEGER NOT NULL DEFAULT 0,
    store           TEXT    NOT NULL,
    region          TEXT    NOT NULL,
    store_tier      TEXT    NOT NULL,
    customer_id     TEXT    NOT NULL,
    category        TEXT    NOT NULL,
    product         TEXT    NOT NULL,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      REAL    NOT NULL,
    gross_revenue   REAL    NOT NULL,
    discount_pct    REAL    NOT NULL DEFAULT 0,
    discount_amt    REAL    NOT NULL DEFAULT 0,
    net_revenue     REAL    NOT NULL,
    cogs            REAL    NOT NULL,
    profit          REAL    NOT NULL,
    profit_margin   REAL    NOT NULL,
    is_return       INTEGER NOT NULL DEFAULT 0,
    payment_method  TEXT    NOT NULL,
    channel         TEXT    NOT NULL
);

CREATE TABLE customers (
    customer_id     TEXT PRIMARY KEY,
    age             INTEGER,
    gender          TEXT,
    loyalty_tier    TEXT,
    signup_year     INTEGER,
    preferred_store TEXT
);

CREATE TABLE stores (
    store   TEXT PRIMARY KEY,
    region  TEXT,
    tier    TEXT,
    size    TEXT,
    opened  INTEGER
);

CREATE TABLE products (
    product         TEXT,
    category        TEXT,
    base_price      REAL,
    target_margin   REAL,
    return_rate     REAL
);

CREATE INDEX idx_txn_date     ON transactions(date);
CREATE INDEX idx_txn_year     ON transactions(year);
CREATE INDEX idx_txn_store    ON transactions(store);
CREATE INDEX idx_txn_category ON transactions(category);
CREATE INDEX idx_txn_customer ON transactions(customer_id);
