"""
run_analysis.py — Retail Sales EDA full pipeline
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from src.data_generator import generate, load_to_sqlite
from src.charts import run_all as run_charts

DB     = "data/retail_sales.db"
CHARTS = "outputs/charts"
EXCEL  = "outputs/excel"

os.makedirs(CHARTS, exist_ok=True)
os.makedirs(EXCEL,  exist_ok=True)
os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)

print("=" * 58)
print("  RETAIL SALES EDA — 3 YEARS OF TRANSACTIONS")
print("=" * 58)

# ── 1. Generate data ──────────────────────────────────────────
print("\n[1/5] Generating dataset...")
tables = generate(n_transactions=50000, seed=42)
for name, df in tables.items():
    df.to_csv(f"data/raw/{name}.csv", index=False)
load_to_sqlite(tables, DB)

# ── 2. Views ──────────────────────────────────────────────────
print("\n[2/5] Creating SQL views...")
conn = sqlite3.connect(DB)
with open("sql/views/02_create_views.sql") as f:
    conn.executescript(f.read())
conn.commit()
for (v,) in conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall():
    print(f"  ✓ {v}")

# ── 3. Key metrics ────────────────────────────────────────────
print("\n[3/5] Computing key metrics...")
kpis = conn.execute("""
    SELECT
        COUNT(*)                           AS transactions,
        COUNT(DISTINCT customer_id)        AS customers,
        COUNT(DISTINCT store)              AS stores,
        ROUND(SUM(net_revenue)/1000000,2)  AS revenue_M,
        ROUND(SUM(profit)/1000000,2)       AS profit_M,
        ROUND(AVG(profit_margin),2)        AS avg_margin,
        ROUND(AVG(net_revenue),2)          AS avg_order_value,
        ROUND(100.0*SUM(is_return)/COUNT(*),2) AS return_rate
    FROM transactions
""").fetchone()
labels = ["Transactions","Customers","Stores","Revenue $M","Profit $M",
          "Avg Margin %","AOV $","Return Rate %"]
for l, v in zip(labels, kpis):
    print(f"  {l:25s}: {v}")

# ── 4. Charts ─────────────────────────────────────────────────
print("\n[4/5] Generating charts...")
run_charts(DB, CHARTS)

# ── 5. Excel workbook ─────────────────────────────────────────
print("\n[5/5] Building Excel workbook...")
sheets = {
    "Executive Summary": pd.read_sql("""
        SELECT year,
               COUNT(*) transactions,
               COUNT(DISTINCT customer_id) customers,
               ROUND(SUM(net_revenue),2) revenue,
               ROUND(SUM(profit),2) profit,
               ROUND(AVG(profit_margin),2) avg_margin_pct,
               ROUND(AVG(net_revenue),2) avg_order_value,
               ROUND(100.0*SUM(is_return)/COUNT(*),2) return_rate_pct
        FROM transactions GROUP BY year ORDER BY year
    """, conn),
    "Monthly Revenue": pd.read_sql("SELECT * FROM vw_monthly_summary", conn),
    "Store KPIs":      pd.read_sql("SELECT * FROM vw_store_kpis ORDER BY total_revenue DESC", conn),
    "Category Perf":   pd.read_sql("SELECT * FROM vw_category_performance ORDER BY year,net_revenue DESC", conn),
    "Top 20 Products": pd.read_sql("""
        SELECT product, category,
               COUNT(*) times_sold,
               SUM(quantity) units_sold,
               ROUND(SUM(net_revenue),2) revenue,
               ROUND(SUM(profit),2) profit,
               ROUND(AVG(profit_margin),2) avg_margin
        FROM transactions GROUP BY product, category
        ORDER BY revenue DESC LIMIT 20
    """, conn),
    "Channel Analysis": pd.read_sql("""
        SELECT channel,
               COUNT(*) transactions,
               ROUND(SUM(net_revenue),2) revenue,
               ROUND(AVG(net_revenue),2) avg_order_value,
               ROUND(100.0*SUM(is_return)/COUNT(*),2) return_rate_pct,
               ROUND(AVG(profit_margin),2) avg_margin_pct
        FROM transactions GROUP BY channel ORDER BY revenue DESC
    """, conn),
    "RFM Segments": pd.read_sql("""
        WITH ld AS (SELECT MAX(date) mx FROM transactions),
        base AS (
            SELECT customer_id,
                   CAST(julianday((SELECT mx FROM ld))-julianday(MAX(date)) AS INTEGER) r,
                   COUNT(*) f, ROUND(SUM(net_revenue),2) m
            FROM transactions GROUP BY customer_id),
        sc AS (SELECT *,
               NTILE(5) OVER (ORDER BY r ASC) rs,
               NTILE(5) OVER (ORDER BY f DESC) fs,
               NTILE(5) OVER (ORDER BY m DESC) ms FROM base)
        SELECT CASE WHEN rs>=4 AND fs>=4 THEN 'Champion'
                    WHEN rs>=3 AND fs>=3 THEN 'Loyal'
                    WHEN rs>=4 AND fs<=2 THEN 'Recent'
                    WHEN rs<=2 AND fs>=4 THEN 'At Risk'
                    WHEN rs<=2 AND fs<=2 THEN 'Lost'
                    ELSE 'Potential' END AS segment,
               COUNT(*) customers, ROUND(AVG(m),2) avg_spend,
               ROUND(AVG(f),1) avg_orders
        FROM sc GROUP BY segment ORDER BY avg_spend DESC
    """, conn),
    "Discount Impact": pd.read_sql("""
        SELECT CASE WHEN discount_pct=0 THEN 'No discount'
                    WHEN discount_pct<=0.05 THEN '1-5%'
                    WHEN discount_pct<=0.10 THEN '6-10%'
                    WHEN discount_pct<=0.20 THEN '11-20%'
                    ELSE '21%+' END AS discount_band,
               COUNT(*) transactions,
               ROUND(AVG(net_revenue),2) avg_order_value,
               ROUND(AVG(profit_margin),2) avg_margin_pct,
               ROUND(100.0*SUM(is_return)/COUNT(*),2) return_rate_pct
        FROM transactions GROUP BY discount_band ORDER BY discount_band
    """, conn),
}

excel_path = f"{EXCEL}/retail_sales_analysis.xlsx"
with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    for name, df in sheets.items():
        df.to_excel(writer, sheet_name=name, index=False)
        ws = writer.sheets[name]
        for col in ws.columns:
            w = max(len(str(c.value or "")) for c in col) + 3
            ws.column_dimensions[col[0].column_letter].width = min(w, 35)

conn.close()
print(f"  ✓ Excel → {excel_path}  ({len(sheets)} sheets)")

print("\n" + "=" * 58)
print("  PIPELINE COMPLETE")
print("=" * 58)
print(f"  Total transactions : 50,000")
print(f"  Revenue            : ${kpis[3]}M")
print(f"  Profit             : ${kpis[4]}M  (margin {kpis[5]}%)")
print(f"  Avg order value    : ${kpis[6]}")
print(f"  Charts → {CHARTS}/  (7 files)")
print(f"  Excel  → {excel_path}")
