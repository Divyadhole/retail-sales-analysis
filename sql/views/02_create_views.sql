-- ============================================================
-- sql/views/02_create_views.sql
-- ============================================================

CREATE VIEW IF NOT EXISTS vw_monthly_summary AS
SELECT
    year, month, quarter,
    COUNT(*)                                        AS transactions,
    SUM(quantity)                                   AS units_sold,
    ROUND(SUM(net_revenue), 2)                      AS net_revenue,
    ROUND(SUM(profit), 2)                           AS total_profit,
    ROUND(AVG(profit_margin), 2)                    AS avg_margin_pct,
    SUM(is_return)                                  AS returns,
    ROUND(100.0 * SUM(is_return) / COUNT(*), 2)     AS return_rate_pct,
    ROUND(AVG(net_revenue), 2)                      AS avg_order_value
FROM transactions
GROUP BY year, month, quarter
ORDER BY year, month;


CREATE VIEW IF NOT EXISTS vw_store_kpis AS
SELECT
    t.store,
    s.region,
    s.tier,
    s.size,
    COUNT(*)                                        AS total_transactions,
    ROUND(SUM(t.net_revenue), 2)                    AS total_revenue,
    ROUND(SUM(t.profit), 2)                         AS total_profit,
    ROUND(AVG(t.profit_margin), 2)                  AS avg_margin_pct,
    ROUND(AVG(t.net_revenue), 2)                    AS avg_order_value,
    ROUND(100.0 * SUM(t.is_return) / COUNT(*), 2)   AS return_rate_pct,
    COUNT(DISTINCT t.customer_id)                   AS unique_customers,
    ROUND(SUM(t.discount_amt), 2)                   AS total_discounts
FROM transactions t
LEFT JOIN stores s ON t.store = s.store
GROUP BY t.store, s.region, s.tier, s.size;


CREATE VIEW IF NOT EXISTS vw_category_performance AS
SELECT
    category,
    year,
    COUNT(*)                                        AS transactions,
    SUM(quantity)                                   AS units_sold,
    ROUND(SUM(net_revenue), 2)                      AS net_revenue,
    ROUND(SUM(profit), 2)                           AS profit,
    ROUND(AVG(profit_margin), 2)                    AS avg_margin_pct,
    ROUND(AVG(net_revenue), 2)                      AS avg_order_value,
    ROUND(100.0 * SUM(is_return) / COUNT(*), 2)     AS return_rate_pct
FROM transactions
GROUP BY category, year
ORDER BY year, net_revenue DESC;
