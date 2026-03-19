-- ============================================================
-- sql/analysis/03_retail_analysis.sql
-- Retail Sales Deep Dive
-- Techniques: CTEs, window functions, YoY growth,
-- ranking, cohort, RFM scoring, basket analysis
-- ============================================================


-- ════════════════════════════════════════════════
-- SECTION 1: REVENUE & GROWTH
-- ════════════════════════════════════════════════

-- 1A. Year-over-year revenue growth
WITH yearly AS (
    SELECT year,
           ROUND(SUM(net_revenue), 2)  AS revenue,
           ROUND(SUM(profit), 2)       AS profit,
           COUNT(*)                    AS transactions,
           COUNT(DISTINCT customer_id) AS unique_customers
    FROM transactions
    GROUP BY year
)
SELECT
    year, revenue, profit, transactions, unique_customers,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY year))
          / NULLIF(LAG(revenue) OVER (ORDER BY year), 0), 1) AS yoy_revenue_growth_pct,
    ROUND(100.0 * (profit - LAG(profit) OVER (ORDER BY year))
          / NULLIF(LAG(profit) OVER (ORDER BY year), 0), 1)  AS yoy_profit_growth_pct
FROM yearly ORDER BY year;


-- 1B. Monthly revenue with 3-month rolling average
WITH monthly AS (
    SELECT year, month,
           ROUND(SUM(net_revenue), 2) AS revenue
    FROM transactions
    GROUP BY year, month
)
SELECT
    year, month, revenue,
    ROUND(AVG(revenue) OVER (
        ORDER BY year, month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_3m_avg_revenue,
    ROUND(revenue - LAG(revenue, 12) OVER (ORDER BY year, month), 2)
          AS vs_same_month_last_year
FROM monthly ORDER BY year, month;


-- 1C. Best and worst months (ranked)
SELECT
    year, month, quarter,
    ROUND(SUM(net_revenue), 2)  AS revenue,
    ROUND(SUM(profit), 2)       AS profit,
    RANK() OVER (PARTITION BY year ORDER BY SUM(net_revenue) DESC) AS rank_in_year
FROM transactions
GROUP BY year, month, quarter
ORDER BY year, rank_in_year;


-- ════════════════════════════════════════════════
-- SECTION 2: STORE PERFORMANCE
-- ════════════════════════════════════════════════

-- 2A. Store ranking with gap to top performer
WITH store_rev AS (
    SELECT store, region, store_tier,
           ROUND(SUM(net_revenue), 2)  AS revenue,
           ROUND(SUM(profit), 2)       AS profit,
           ROUND(AVG(profit_margin), 2) AS avg_margin,
           COUNT(DISTINCT customer_id) AS customers,
           ROUND(AVG(net_revenue), 2)  AS aov
    FROM transactions
    GROUP BY store, region, store_tier
)
SELECT *,
    RANK() OVER (ORDER BY revenue DESC)          AS revenue_rank,
    ROUND(MAX(revenue) OVER () - revenue, 2)     AS gap_to_top_store,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 1) AS pct_of_total_revenue
FROM store_rev ORDER BY revenue DESC;


-- 2B. Weekend vs weekday performance per store
SELECT
    store,
    ROUND(AVG(CASE WHEN is_weekend=1 THEN net_revenue END), 2) AS avg_weekend_order,
    ROUND(AVG(CASE WHEN is_weekend=0 THEN net_revenue END), 2) AS avg_weekday_order,
    SUM(CASE WHEN is_weekend=1 THEN net_revenue ELSE 0 END)    AS weekend_revenue,
    SUM(CASE WHEN is_weekend=0 THEN net_revenue ELSE 0 END)    AS weekday_revenue,
    ROUND(100.0 * SUM(CASE WHEN is_weekend=1 THEN net_revenue ELSE 0 END)
          / SUM(net_revenue), 1)                               AS weekend_pct_of_revenue
FROM transactions
GROUP BY store ORDER BY weekend_revenue DESC;


-- ════════════════════════════════════════════════
-- SECTION 3: CATEGORY & PRODUCT ANALYSIS
-- ════════════════════════════════════════════════

-- 3A. Category performance with margin ranking
SELECT
    category,
    COUNT(*)                               AS transactions,
    SUM(quantity)                          AS units_sold,
    ROUND(SUM(net_revenue), 2)             AS revenue,
    ROUND(SUM(profit), 2)                  AS profit,
    ROUND(AVG(profit_margin), 2)           AS avg_margin_pct,
    ROUND(100.0 * SUM(is_return)/COUNT(*),2) AS return_rate_pct,
    RANK() OVER (ORDER BY SUM(profit) DESC)  AS profit_rank,
    RANK() OVER (ORDER BY AVG(profit_margin) DESC) AS margin_rank
FROM transactions
GROUP BY category ORDER BY profit DESC;


-- 3B. Top 10 products by revenue (with category context)
SELECT
    product, category,
    COUNT(*) AS times_sold,
    SUM(quantity) AS units_sold,
    ROUND(SUM(net_revenue), 2) AS total_revenue,
    ROUND(SUM(profit), 2)      AS total_profit,
    ROUND(AVG(unit_price), 2)  AS avg_price,
    ROUND(100.0 * SUM(is_return)/COUNT(*), 2) AS return_rate_pct,
    RANK() OVER (ORDER BY SUM(net_revenue) DESC) AS revenue_rank
FROM transactions
GROUP BY product, category
ORDER BY total_revenue DESC LIMIT 20;


-- ════════════════════════════════════════════════
-- SECTION 4: CUSTOMER ANALYTICS
-- ════════════════════════════════════════════════

-- 4A. Customer RFM Scoring (Recency, Frequency, Monetary)
-- This is one of the most important techniques in retail analytics
WITH last_date AS (SELECT MAX(date) AS max_date FROM transactions),
rfm_base AS (
    SELECT
        t.customer_id,
        c.loyalty_tier,
        c.age,
        CAST(julianday((SELECT max_date FROM last_date)) -
             julianday(MAX(t.date)) AS INTEGER)  AS recency_days,
        COUNT(*)                                  AS frequency,
        ROUND(SUM(t.net_revenue), 2)              AS monetary
    FROM transactions t
    JOIN customers c ON t.customer_id = c.customer_id
    GROUP BY t.customer_id, c.loyalty_tier, c.age
),
rfm_scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days ASC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency DESC)    AS f_score,
        NTILE(5) OVER (ORDER BY monetary DESC)     AS m_score
    FROM rfm_base
)
SELECT
    customer_id, loyalty_tier, age,
    recency_days, frequency, monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champion'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent'
        WHEN r_score <= 2 AND f_score >= 4 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
        ELSE 'Potential'
    END AS customer_segment
FROM rfm_scored
ORDER BY rfm_total DESC LIMIT 50;


-- 4B. Customer segment summary
WITH last_date AS (SELECT MAX(date) AS max_date FROM transactions),
rfm_base AS (
    SELECT customer_id,
        CAST(julianday((SELECT max_date FROM last_date)) -
             julianday(MAX(date)) AS INTEGER) AS recency_days,
        COUNT(*) AS frequency,
        ROUND(SUM(net_revenue), 2) AS monetary
    FROM transactions GROUP BY customer_id
),
rfm_scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days ASC)  AS r,
        NTILE(5) OVER (ORDER BY frequency DESC)    AS f,
        NTILE(5) OVER (ORDER BY monetary DESC)     AS m
    FROM rfm_base
)
SELECT
    CASE
        WHEN r >= 4 AND f >= 4 THEN 'Champion'
        WHEN r >= 3 AND f >= 3 THEN 'Loyal'
        WHEN r >= 4 AND f <= 2 THEN 'Recent'
        WHEN r <= 2 AND f >= 4 THEN 'At Risk'
        WHEN r <= 2 AND f <= 2 THEN 'Lost'
        ELSE 'Potential'
    END AS segment,
    COUNT(*) AS customers,
    ROUND(AVG(monetary), 2) AS avg_spend,
    ROUND(AVG(frequency), 1) AS avg_orders,
    ROUND(AVG(recency_days), 0) AS avg_days_since_purchase
FROM rfm_scored
GROUP BY segment ORDER BY avg_spend DESC;


-- ════════════════════════════════════════════════
-- SECTION 5: CHANNEL & PAYMENT ANALYSIS
-- ════════════════════════════════════════════════

-- 5A. Channel performance comparison
SELECT
    channel,
    COUNT(*) AS transactions,
    ROUND(SUM(net_revenue), 2) AS revenue,
    ROUND(AVG(net_revenue), 2) AS avg_order_value,
    ROUND(100.0 * SUM(is_return)/COUNT(*), 2) AS return_rate_pct,
    ROUND(AVG(profit_margin), 2) AS avg_margin_pct,
    ROUND(100.0 * SUM(CASE WHEN discount_pct > 0 THEN 1 ELSE 0 END)
          / COUNT(*), 1) AS pct_discounted
FROM transactions
GROUP BY channel ORDER BY revenue DESC;


-- 5B. Discount impact analysis
SELECT
    CASE
        WHEN discount_pct = 0    THEN '1. No discount'
        WHEN discount_pct <= 0.05 THEN '2. 1-5%'
        WHEN discount_pct <= 0.10 THEN '3. 6-10%'
        WHEN discount_pct <= 0.20 THEN '4. 11-20%'
        ELSE                          '5. 21%+'
    END AS discount_band,
    COUNT(*) AS transactions,
    ROUND(AVG(net_revenue), 2) AS avg_order_value,
    ROUND(AVG(profit_margin), 2) AS avg_margin_pct,
    ROUND(100.0 * SUM(is_return)/COUNT(*), 2) AS return_rate_pct,
    ROUND(SUM(net_revenue), 2) AS total_revenue
FROM transactions
GROUP BY discount_band ORDER BY discount_band;
