"""
src/charts.py — Retail Sales Publication-Quality Charts
"""
import sqlite3, numpy as np, pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from pathlib import Path

P = {"teal":"#1D9E75","blue":"#185FA5","amber":"#BA7517","red":"#A32D2D",
     "purple":"#534AB7","coral":"#D85A30","neutral":"#5F5E5A","light":"#F1EFE8","mid":"#B4B2A9"}

BASE = {"figure.facecolor":"white","axes.facecolor":"#FAFAF8",
        "axes.spines.top":False,"axes.spines.right":False,"axes.spines.left":False,
        "axes.grid":True,"axes.grid.axis":"y","grid.color":"#ECEAE4","grid.linewidth":0.6,
        "font.family":"DejaVu Sans","axes.titlesize":12,"axes.titleweight":"bold",
        "axes.labelsize":10,"xtick.labelsize":9,"ytick.labelsize":9,
        "xtick.bottom":False,"ytick.left":False}

def q(conn, sql): return pd.read_sql_query(sql, conn)
def save(fig, path):
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {Path(path).name}")

def fmt_k(x, _): return f"${x/1000:.0f}K"
def fmt_m(x, _): return f"${x/1e6:.1f}M"


def run_all(db_path, out_dir):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    # ── Chart 1: Monthly Revenue 3 Years + Holiday Annotations ─────────
    df1 = q(conn, """
        SELECT year, month,
               ROUND(SUM(net_revenue),2) AS revenue,
               ROUND(SUM(profit),2)      AS profit
        FROM transactions GROUP BY year, month ORDER BY year, month
    """)
    df1["period"] = df1["year"].astype(str) + "-" + df1["month"].astype(str).str.zfill(2)

    with plt.rc_context({**BASE,"axes.grid.axis":"x"}):
        fig, (ax1,ax2) = plt.subplots(2,1,figsize=(14,7),sharex=True)
        colors = {2022:P["blue"], 2023:P["teal"], 2024:P["coral"]}
        for yr, grp in df1.groupby("year"):
            ax1.plot(range(len(grp)), grp["revenue"], "o-", lw=2, markersize=4,
                     color=colors[yr], label=str(yr))
            ax2.plot(range(len(grp)), grp["profit"],  "o-", lw=2, markersize=4,
                     color=colors[yr], label=str(yr))

        # Mark holiday spikes
        for ax in [ax1, ax2]:
            for xpos, lbl in [(10,"Nov\nHoliday"),(11,"Dec\nPeak"),(7,"Back\nto School")]:
                ax.axvline(xpos, color=P["amber"], lw=1, linestyle=":", alpha=0.7)
                ax.text(xpos+0.1, ax.get_ylim()[1]*0.92, lbl,
                        fontsize=7.5, color=P["amber"])

        ax1.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_k))
        ax2.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_k))
        ax1.set_ylabel("Net Revenue")
        ax2.set_ylabel("Profit")
        ax2.set_xticks(range(12))
        ax2.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun",
                             "Jul","Aug","Sep","Oct","Nov","Dec"])
        ax1.set_title("Monthly Revenue — 3 Years")
        ax2.set_title("Monthly Profit — 3 Years")
        ax1.legend(fontsize=9)
        fig.tight_layout()
        save(fig, f"{out_dir}/01_monthly_revenue_3yr.png")

    # ── Chart 2: Store Performance Matrix ──────────────────────────────
    df2 = q(conn, """
        SELECT store, region, store_tier,
               ROUND(SUM(net_revenue)/1000,1) AS rev_k,
               ROUND(AVG(profit_margin),1)    AS margin,
               COUNT(DISTINCT customer_id)    AS customers,
               COUNT(*) AS txns
        FROM transactions GROUP BY store, region, store_tier
        ORDER BY rev_k DESC
    """)
    with plt.rc_context({**BASE,"axes.grid":False}):
        fig, ax = plt.subplots(figsize=(11,6))
        tier_c = {"Premium":P["purple"],"Standard":P["teal"],"Budget":P["amber"]}
        for _, row in df2.iterrows():
            ax.scatter(row["rev_k"], row["margin"],
                       s=row["customers"]*0.4,
                       c=tier_c[row["store_tier"]], alpha=0.8,
                       edgecolors="white", linewidths=0.8, zorder=3)
            ax.annotate(row["store"].split("-")[1],
                        (row["rev_k"], row["margin"]),
                        fontsize=7.5, color=P["neutral"],
                        xytext=(4,3), textcoords="offset points")
        from matplotlib.lines import Line2D
        legend_els = [Line2D([0],[0], marker="o", color="w",
                             markerfacecolor=v, markersize=9, label=k)
                      for k,v in tier_c.items()]
        ax.legend(handles=legend_els, title="Store tier", fontsize=9)
        ax.set_xlabel("Total Revenue ($K)")
        ax.set_ylabel("Avg Profit Margin (%)")
        ax.set_title("Store Performance Matrix\nBubble size = unique customers")
        ax.spines["left"].set_visible(True)
        ax.spines["bottom"].set_visible(True)
        fig.tight_layout()
        save(fig, f"{out_dir}/02_store_performance.png")

    # ── Chart 3: Category Revenue + Margin (dual axis) ─────────────────
    df3 = q(conn, """
        SELECT category,
               ROUND(SUM(net_revenue)/1000,1) AS rev_k,
               ROUND(AVG(profit_margin),1)    AS margin,
               ROUND(100.0*SUM(is_return)/COUNT(*),1) AS return_rate
        FROM transactions GROUP BY category ORDER BY rev_k DESC
    """)
    with plt.rc_context(BASE):
        fig, ax1 = plt.subplots(figsize=(12,5))
        ax2 = ax1.twinx()
        x = range(len(df3))
        bars = ax1.bar(x, df3["rev_k"], color=P["teal"], alpha=0.8,
                       width=0.6, label="Revenue ($K)")
        ax2.plot(x, df3["margin"], "D--", color=P["red"], lw=2,
                 markersize=7, label="Avg margin %")
        ax1.set_xticks(x)
        ax1.set_xticklabels(df3["category"], rotation=25, ha="right")
        ax1.set_ylabel("Revenue ($K)")
        ax2.set_ylabel("Avg Profit Margin (%)", color=P["red"])
        ax1.set_title("Category Revenue vs Profit Margin")
        h1,l1 = ax1.get_legend_handles_labels()
        h2,l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1+h2, l1+l2, fontsize=9)
        fig.tight_layout()
        save(fig, f"{out_dir}/03_category_revenue_margin.png")

    # ── Chart 4: Seasonality Heatmap (Month × Category) ────────────────
    df4 = q(conn, """
        SELECT category, month,
               ROUND(SUM(net_revenue)/1000,1) AS rev_k
        FROM transactions GROUP BY category, month
    """)
    pivot = df4.pivot(index="category", columns="month", values="rev_k")
    pivot.columns = ["Jan","Feb","Mar","Apr","May","Jun",
                     "Jul","Aug","Sep","Oct","Nov","Dec"]
    with plt.rc_context({**BASE,"axes.grid":False}):
        fig, ax = plt.subplots(figsize=(13,5.5))
        sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlGn",
                    linewidths=0.4, linecolor="#E0DED8",
                    cbar_kws={"label":"Revenue ($K)"}, ax=ax)
        ax.set_title("Revenue Seasonality Heatmap — Category × Month ($K)",
                     fontweight="bold")
        ax.set_ylabel("")
        plt.xticks(rotation=0)
        plt.yticks(rotation=0)
        fig.tight_layout()
        save(fig, f"{out_dir}/04_seasonality_heatmap.png")

    # ── Chart 5: RFM Customer Segment Donut + Avg Spend ────────────────
    df5 = q(conn, """
        WITH ld AS (SELECT MAX(date) mx FROM transactions),
        base AS (
            SELECT customer_id,
                   CAST(julianday((SELECT mx FROM ld))-julianday(MAX(date)) AS INTEGER) AS r,
                   COUNT(*) AS f,
                   ROUND(SUM(net_revenue),2) AS m
            FROM transactions GROUP BY customer_id
        ),
        sc AS (
            SELECT *,
                   NTILE(5) OVER (ORDER BY r ASC) rs,
                   NTILE(5) OVER (ORDER BY f DESC) fs,
                   NTILE(5) OVER (ORDER BY m DESC) ms
            FROM base
        )
        SELECT
            CASE WHEN rs>=4 AND fs>=4 THEN 'Champion'
                 WHEN rs>=3 AND fs>=3 THEN 'Loyal'
                 WHEN rs>=4 AND fs<=2 THEN 'Recent'
                 WHEN rs<=2 AND fs>=4 THEN 'At Risk'
                 WHEN rs<=2 AND fs<=2 THEN 'Lost'
                 ELSE 'Potential' END AS seg,
            COUNT(*) AS n,
            ROUND(AVG(m),2) AS avg_spend
        FROM sc GROUP BY seg ORDER BY avg_spend DESC
    """)
    seg_colors = {"Champion":P["purple"],"Loyal":P["teal"],"Recent":P["blue"],
                  "Potential":P["amber"],"At Risk":P["coral"],"Lost":P["mid"]}
    with plt.rc_context({**BASE,"axes.grid":False}):
        fig,(ax1,ax2) = plt.subplots(1,2,figsize=(12,5))
        cs = [seg_colors.get(s, P["mid"]) for s in df5["seg"]]
        ax1.pie(df5["n"], labels=df5["seg"], colors=cs,
                autopct="%1.0f%%", startangle=90,
                wedgeprops={"edgecolor":"white","linewidth":1.5})
        ax1.set_title("Customer Segments by Count")
        bars = ax2.barh(df5["seg"], df5["avg_spend"],
                        color=cs, height=0.6)
        for bar, v in zip(bars, df5["avg_spend"]):
            ax2.text(v+10, bar.get_y()+bar.get_height()/2,
                     f"${v:,.0f}", va="center", fontsize=9)
        ax2.set_xlabel("Avg Total Spend per Customer ($)")
        ax2.set_title("Avg Spend by Customer Segment")
        fig.suptitle("RFM Customer Segmentation", fontsize=13, fontweight="bold")
        fig.tight_layout()
        save(fig, f"{out_dir}/05_rfm_segments.png")

    # ── Chart 6: Channel + Payment + Discount analysis ─────────────────
    df6a = q(conn, """
        SELECT channel, ROUND(SUM(net_revenue)/1000,1) rv,
               ROUND(AVG(net_revenue),2) aov,
               ROUND(100.0*SUM(is_return)/COUNT(*),2) ret
        FROM transactions GROUP BY channel ORDER BY rv DESC
    """)
    df6b = q(conn, """
        SELECT payment_method, ROUND(SUM(net_revenue)/1000,1) rv,
               COUNT(*) txns
        FROM transactions GROUP BY payment_method ORDER BY rv DESC
    """)
    with plt.rc_context(BASE):
        fig,(ax1,ax2) = plt.subplots(1,2,figsize=(12,4.5))
        channel_colors = [P["teal"], P["blue"], P["purple"]]
        bars = ax1.bar(df6a["channel"], df6a["rv"],
                       color=channel_colors, width=0.5)
        for bar, v, aov in zip(bars, df6a["rv"], df6a["aov"]):
            ax1.text(bar.get_x()+bar.get_width()/2, v+5,
                     f"${v:.0f}K\nAOV ${aov:.0f}",
                     ha="center", fontsize=8.5)
        ax1.set_ylabel("Revenue ($K)")
        ax1.set_title("Revenue & AOV by Channel")

        pay_colors = [P["teal"],P["blue"],P["amber"],P["coral"],P["mid"]]
        ax2.bar(df6b["payment_method"], df6b["rv"],
                color=pay_colors, width=0.5)
        ax2.set_ylabel("Revenue ($K)")
        ax2.set_title("Revenue by Payment Method")
        ax2.tick_params(axis="x", rotation=20)
        fig.tight_layout()
        save(fig, f"{out_dir}/06_channel_payment.png")

    # ── Chart 7: YoY Growth by Category ────────────────────────────────
    df7 = q(conn, """
        SELECT category, year, ROUND(SUM(net_revenue)/1000,1) rv
        FROM transactions GROUP BY category, year
    """)
    pivot7 = df7.pivot(index="category", columns="year", values="rv").fillna(0)
    if 2022 in pivot7.columns and 2023 in pivot7.columns:
        pivot7["growth_23"] = ((pivot7[2023]-pivot7[2022])/pivot7[2022]*100).round(1)
    if 2023 in pivot7.columns and 2024 in pivot7.columns:
        pivot7["growth_24"] = ((pivot7[2024]-pivot7[2023])/pivot7[2023]*100).round(1)

    with plt.rc_context(BASE):
        fig, ax = plt.subplots(figsize=(11,5))
        x = np.arange(len(pivot7))
        w = 0.35
        if "growth_23" in pivot7.columns:
            b1 = ax.bar(x-w/2, pivot7["growth_23"],
                        width=w, color=P["teal"], alpha=0.85, label="2022→2023")
        if "growth_24" in pivot7.columns:
            b2 = ax.bar(x+w/2, pivot7["growth_24"],
                        width=w, color=P["coral"], alpha=0.85, label="2023→2024")
        ax.axhline(0, color=P["neutral"], lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(pivot7.index, rotation=25, ha="right")
        ax.set_ylabel("YoY Revenue Growth (%)")
        ax.set_title("Year-over-Year Revenue Growth by Category")
        ax.legend(fontsize=9)
        fig.tight_layout()
        save(fig, f"{out_dir}/07_yoy_category_growth.png")

    conn.close()
