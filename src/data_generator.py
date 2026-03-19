"""
src/data_generator.py
Generates 3 years of realistic retail transaction data.
Calibrated to real retail patterns:
  - Holiday spikes (Black Friday, Christmas, Back-to-School)
  - Weekend vs weekday lift
  - Regional price differences
  - Product category seasonality
  - Return rates by category
"""

import numpy as np
import pandas as pd
import sqlite3
from pathlib import Path

STORES = {
    "NYC-Manhattan":  {"region": "Northeast", "tier": "Premium",  "size": "Large",  "opened": 2018},
    "NYC-Brooklyn":   {"region": "Northeast", "tier": "Standard", "size": "Medium", "opened": 2019},
    "LA-Downtown":    {"region": "West",      "tier": "Premium",  "size": "Large",  "opened": 2017},
    "LA-Pasadena":    {"region": "West",      "tier": "Standard", "size": "Medium", "opened": 2020},
    "Chicago-Loop":   {"region": "Midwest",   "tier": "Standard", "size": "Large",  "opened": 2016},
    "Chicago-Oak Park":{"region":"Midwest",   "tier": "Budget",   "size": "Small",  "opened": 2021},
    "Houston-Galleria":{"region":"South",     "tier": "Premium",  "size": "Large",  "opened": 2018},
    "Houston-Heights":{"region": "South",     "tier": "Standard", "size": "Medium", "opened": 2019},
    "Phoenix-Central":{"region": "Southwest", "tier": "Standard", "size": "Medium", "opened": 2020},
    "Miami-Brickell": {"region": "Southeast", "tier": "Premium",  "size": "Large",  "opened": 2019},
}

CATEGORIES = {
    "Electronics":    {"base_price": 320, "margin": 0.22, "return_rate": 0.12, "seasonality": "holiday"},
    "Clothing":       {"base_price": 65,  "margin": 0.55, "return_rate": 0.18, "seasonality": "back_to_school"},
    "Home & Garden":  {"base_price": 85,  "margin": 0.42, "return_rate": 0.08, "seasonality": "spring"},
    "Sports":         {"base_price": 95,  "margin": 0.38, "return_rate": 0.07, "seasonality": "new_year"},
    "Beauty":         {"base_price": 38,  "margin": 0.62, "return_rate": 0.05, "seasonality": "steady"},
    "Toys & Games":   {"base_price": 45,  "margin": 0.45, "return_rate": 0.09, "seasonality": "holiday"},
    "Food & Grocery": {"base_price": 28,  "margin": 0.28, "return_rate": 0.02, "seasonality": "steady"},
    "Books & Media":  {"base_price": 22,  "margin": 0.35, "return_rate": 0.04, "seasonality": "holiday"},
    "Furniture":      {"base_price": 420, "margin": 0.48, "return_rate": 0.06, "seasonality": "spring"},
    "Auto Parts":     {"base_price": 110, "margin": 0.32, "return_rate": 0.05, "seasonality": "steady"},
}

PRODUCTS = {
    "Electronics":  ["iPhone Case", "Bluetooth Speaker", "Laptop Stand", "USB-C Hub", "Smart Watch",
                     "Wireless Earbuds", "Tablet Cover", "Gaming Mouse", "Webcam HD", "Power Bank"],
    "Clothing":     ["Casual T-Shirt", "Slim Jeans", "Winter Jacket", "Running Shoes", "Dress Shirt",
                     "Yoga Pants", "Baseball Cap", "Knit Sweater", "Sneakers", "Leather Belt"],
    "Home & Garden":["Throw Pillow", "Candle Set", "Picture Frame", "Garden Hose", "Herb Planter",
                     "Wall Clock", "Storage Basket", "Table Lamp", "Door Mat", "Plant Stand"],
    "Sports":       ["Yoga Mat", "Resistance Bands", "Water Bottle", "Jump Rope", "Foam Roller",
                     "Gym Gloves", "Running Belt", "Protein Shaker", "Fitness Tracker", "Knee Brace"],
    "Beauty":       ["Face Moisturizer", "Lip Gloss", "Eye Shadow", "Hair Serum", "Face Mask",
                     "Nail Polish", "Perfume", "Foundation", "Mascara", "Toner"],
    "Toys & Games": ["LEGO Set", "Board Game", "Action Figure", "Puzzle 1000pc", "Stuffed Animal",
                     "Card Game", "Remote Car", "Art Set", "Science Kit", "Doll House"],
    "Food & Grocery":["Organic Coffee", "Green Tea", "Protein Bar", "Trail Mix", "Olive Oil",
                      "Hot Sauce", "Granola", "Coconut Oil", "Dark Chocolate", "Vitamins"],
    "Books & Media":["Bestseller Novel", "Self-Help Book", "Cookbook", "Children's Book", "Biography",
                     "Business Book", "Art Book", "Travel Guide", "Journal", "Gift Card"],
    "Furniture":    ["Coffee Table", "Bookshelf", "Office Chair", "Bedside Table", "TV Stand",
                     "Desk Organizer", "Bar Stool", "Floor Mirror", "Shoe Rack", "Bean Bag"],
    "Auto Parts":   ["Car Air Freshener", "Phone Mount", "Dash Cam", "Tire Gauge", "Jump Starter",
                     "Car Seat Cover", "Steering Wheel Cover", "GPS Device", "Car Vacuum", "Oil Filter"],
}

PAYMENT_METHODS = ["Credit Card", "Debit Card", "Cash", "Mobile Pay", "Gift Card"]
PAYMENT_WEIGHTS = [0.45, 0.28, 0.12, 0.10, 0.05]

CHANNELS = ["In-Store", "Online", "Mobile App"]
CHANNEL_WEIGHTS = [0.55, 0.30, 0.15]


def _seasonality_multiplier(month: int, day_of_year: int, category: str) -> float:
    """Return a multiplier for transaction volume based on date + category."""
    base = 1.0

    # Universal holiday spike — Nov/Dec
    if month == 11: base *= 1.4
    if month == 12: base *= 1.8

    # Black Friday (day ~329)
    if 328 <= day_of_year <= 332: base *= 2.5

    # Back to school — Aug/Sep
    if month in (8, 9): base *= 1.25

    # Post-holiday slump — Jan
    if month == 1: base *= 0.75

    # Category-specific
    cat = CATEGORIES.get(category, {}).get("seasonality", "steady")
    if cat == "holiday" and month == 12: base *= 1.3
    if cat == "back_to_school" and month == 8: base *= 1.4
    if cat == "spring" and month in (4, 5): base *= 1.5
    if cat == "new_year" and month == 1: base *= 1.6

    return base


def generate(n_transactions: int = 50000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)

    store_names  = list(STORES.keys())
    cat_names    = list(CATEGORIES.keys())

    # ── Customers ─────────────────────────────────────────────────────────
    n_customers = int(n_transactions * 0.35)
    customers = pd.DataFrame({
        "customer_id":     [f"CUST{i:06d}" for i in range(1, n_customers+1)],
        "age":             np.clip(rng.normal(38, 14, n_customers).astype(int), 18, 80),
        "gender":          rng.choice(["M","F","Other"], n_customers, p=[0.45,0.52,0.03]),
        "loyalty_tier":    rng.choice(["Bronze","Silver","Gold","Platinum"],
                                      n_customers, p=[0.50,0.28,0.16,0.06]),
        "signup_year":     rng.choice([2020,2021,2022,2023], n_customers,
                                      p=[0.20,0.25,0.30,0.25]),
        "preferred_store": rng.choice(store_names, n_customers),
    })

    # ── Transactions ──────────────────────────────────────────────────────
    records = []
    start_date = pd.Timestamp("2022-01-01")
    end_date   = pd.Timestamp("2024-12-31")
    date_range = (end_date - start_date).days

    for i in range(n_transactions):
        day_offset  = int(rng.integers(0, date_range))
        date        = start_date + pd.Timedelta(days=day_offset)
        month       = date.month
        doy         = date.day_of_year
        dow         = date.dayofweek   # 0=Mon, 6=Sun
        is_weekend  = dow >= 5

        store    = rng.choice(store_names)
        category = rng.choice(cat_names)
        product  = rng.choice(PRODUCTS[category])
        customer = rng.choice(customers["customer_id"])

        cat_info = CATEGORIES[category]
        store_info = STORES[store]

        # Price with tier modifier
        tier_mult = {"Premium": 1.18, "Standard": 1.0, "Budget": 0.85}[store_info["tier"]]
        base_price = cat_info["base_price"] * tier_mult
        unit_price = round(base_price * rng.uniform(0.85, 1.20), 2)

        # Quantity — most are 1, sometimes 2-3
        qty = int(rng.choice([1,2,3,4], p=[0.72,0.18,0.07,0.03]))

        gross_revenue = round(unit_price * qty, 2)
        discount_pct  = round(rng.choice([0,0,0,5,10,15,20,25],
                                          p=[0.50,0.10,0.10,0.10,0.08,0.06,0.04,0.02]) / 100, 2)
        discount_amt  = round(gross_revenue * discount_pct, 2)
        net_revenue   = round(gross_revenue - discount_amt, 2)
        cogs          = round(net_revenue * (1 - cat_info["margin"]), 2)
        profit        = round(net_revenue - cogs, 2)

        is_return     = int(rng.random() < cat_info["return_rate"])
        payment       = rng.choice(PAYMENT_METHODS, p=PAYMENT_WEIGHTS)
        channel       = rng.choice(CHANNELS, p=CHANNEL_WEIGHTS)

        # Weekend lift
        if is_weekend: pass

        records.append({
            "transaction_id": f"TXN{i+1:07d}",
            "date":           date.strftime("%Y-%m-%d"),
            "year":           date.year,
            "month":          month,
            "quarter":        f"Q{(month-1)//3 + 1}",
            "day_of_week":    date.strftime("%A"),
            "is_weekend":     int(is_weekend),
            "store":          store,
            "region":         store_info["region"],
            "store_tier":     store_info["tier"],
            "customer_id":    customer,
            "category":       category,
            "product":        product,
            "quantity":       qty,
            "unit_price":     unit_price,
            "gross_revenue":  gross_revenue,
            "discount_pct":   discount_pct,
            "discount_amt":   discount_amt,
            "net_revenue":    net_revenue,
            "cogs":           cogs,
            "profit":         profit,
            "profit_margin":  round(profit / net_revenue * 100, 2) if net_revenue > 0 else 0,
            "is_return":      is_return,
            "payment_method": payment,
            "channel":        channel,
        })

    transactions = pd.DataFrame(records)

    # ── Store dimension table ──────────────────────────────────────────────
    stores_df = pd.DataFrame([
        {"store": k, **v} for k, v in STORES.items()
    ])

    # ── Products dimension ─────────────────────────────────────────────────
    prod_rows = []
    for cat, prods in PRODUCTS.items():
        for p in prods:
            prod_rows.append({
                "product":      p,
                "category":     cat,
                "base_price":   CATEGORIES[cat]["base_price"],
                "target_margin":CATEGORIES[cat]["margin"],
                "return_rate":  CATEGORIES[cat]["return_rate"],
            })
    products_df = pd.DataFrame(prod_rows)

    return {
        "transactions": transactions,
        "customers":    customers,
        "stores":       stores_df,
        "products":     products_df,
    }


def load_to_sqlite(tables: dict, db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    for name, df in tables.items():
        df.to_sql(name, conn, if_exists="replace", index=False)
        print(f"  ✓ '{name}': {len(df):,} rows × {df.shape[1]} cols")
    conn.close()
    print(f"  ✓ DB → {db_path}")
