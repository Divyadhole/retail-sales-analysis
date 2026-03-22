# RFM Segmentation Reference

## Segment Definitions
| Segment | Recency | Frequency | Monetary | % of Customers |
|---|---|---|---|---|
| Champion | 1-30 days | 10+ orders | Top 20% spend | 12% |
| Loyal | 1-60 days | 5-9 orders | Top 40% spend | 28% |
| Potential Loyalist | 31-90 days | 3-4 orders | Top 60% spend | 35% |
| At Risk | 91-180 days | 2-3 orders | Any | 18% |
| Lost | 180+ days | 1-2 orders | Any | 7% |

## Business Value
- Champions generate 38% of total revenue with 12% of customers
- At Risk customers: last purchase 91-180 days ago — win-back opportunity
- December seasonality index: +30% above average month

## NTILE SQL Used
```sql
SELECT *, 
    NTILE(5) OVER (ORDER BY recency_days ASC)   AS r_score,
    NTILE(5) OVER (ORDER BY order_count DESC)   AS f_score,
    NTILE(5) OVER (ORDER BY total_spend DESC)   AS m_score
FROM customer_summary;
```
