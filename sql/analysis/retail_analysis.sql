
-- 7. Product category margin analysis
SELECT category,
    COUNT(*) transactions,
    ROUND(SUM(revenue), 0) total_revenue,
    ROUND(AVG(margin_pct), 2) avg_margin_pct,
    RANK() OVER (ORDER BY SUM(revenue) DESC) revenue_rank,
    RANK() OVER (ORDER BY AVG(margin_pct) DESC) margin_rank
FROM transactions
GROUP BY category ORDER BY total_revenue DESC;

-- 8. Store performance vs chain average (LAG window)
SELECT store_id, month,
    monthly_revenue,
    ROUND(AVG(monthly_revenue) OVER (PARTITION BY store_id 
          ORDER BY month ROWS 2 PRECEDING), 0) AS rolling_3mo_avg,
    monthly_revenue - LAG(monthly_revenue) OVER 
          (PARTITION BY store_id ORDER BY month) AS mom_change
FROM monthly_store_revenue ORDER BY store_id, month;
