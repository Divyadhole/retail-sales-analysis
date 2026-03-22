# Key Findings — Retail Sales Analysis

## Revenue Overview
- **Total revenue:** $8.97M across 50,000 transactions
- **Stores:** 10 locations, 3 years of data
- **Average margin:** 40.71%

## Top Insights

### 1. Pareto Effect in Customer Base
Champions (12% of customers) drive 38% of revenue.
Loyal customers (28%) contribute another 31%.
Top 40% of customers = 69% of all revenue.

### 2. December Seasonality is Massive
- December seasonality index: **+30% above average month**
- Inventory planning must account for December surge
- Q4 consistently highest revenue quarter

### 3. Store Variance is Significant
- Best performing store: 34% above chain average
- Worst performing store: 18% below chain average
- 3-month rolling average smooths seasonal noise

### 4. At-Risk Customers Are Low-Hanging Fruit
- 18% of customers haven't purchased in 91-180 days
- Last order avg: $62 — still engaged at lower level
- Win-back email campaign estimated ROI: 4:1

## SQL Techniques Used
- NTILE(5) for RFM scoring
- LAG() for MoM store comparison
- Rolling window AVG for trend smoothing
- RANK() for dual metric rankings
