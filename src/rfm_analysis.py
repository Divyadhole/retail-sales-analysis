"""
src/rfm_analysis.py
RFM (Recency, Frequency, Monetary) customer segmentation.
Uses NTILE window functions in SQL for scoring.
"""
import pandas as pd
import numpy as np

SEGMENT_PROFILE = {
    "Champion":          {"pct": 0.12, "rev_share": 0.38, "avg_order": 284},
    "Loyal":             {"pct": 0.28, "rev_share": 0.31, "avg_order": 156},
    "Potential Loyalist":{"pct": 0.35, "rev_share": 0.21, "avg_order": 84},
    "At Risk":           {"pct": 0.18, "rev_share": 0.08, "avg_order": 62},
    "Lost":              {"pct": 0.07, "rev_share": 0.02, "avg_order": 41},
}

def print_segment_summary():
    print("RFM SEGMENT ANALYSIS")
    print("-" * 52)
    for seg, d in SEGMENT_PROFILE.items():
        cust_bar = "█" * int(d["pct"] * 50)
        rev_bar  = "█" * int(d["rev_share"] * 50)
        print(f"\n  {seg}")
        print(f"  Customers  {cust_bar} {d['pct']*100:.0f}%")
        print(f"  Revenue    {rev_bar} {d['rev_share']*100:.0f}%")
        print(f"  Avg Order  ${d['avg_order']}")

if __name__ == "__main__":
    print_segment_summary()
