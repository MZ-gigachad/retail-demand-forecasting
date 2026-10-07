"""Synthetic data generator for local prototyping and testing without downloading massive datasets."""
from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np
import pandas as pd
from src.config import SEED
from src.utils import get_logger, set_seed

logger = get_logger(__name__)

def generate_synthetic_retail_data(
    num_stores: int = 5,
    num_products: int = 20,
    days: int = 365,
    start_date: str = "2023-01-01",
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """Generate realistic daily retail sales dataset for testing pipelines."""
    set_seed(seed or SEED)
    logger.info(f"Generating synthetic retail data for {num_stores} stores, {num_products} items over {days} days.")
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    dates = [start + timedelta(days=i) for i in range(days)]
    
    stores = [f"STORE_{i:03d}" for i in range(1, num_stores + 1)]
    categories = ["GROCERY", "BEVERAGES", "DAIRY", "BAKERY", "CLEANING"]
    products = [
        {"Product_ID": f"PROD_{i:04d}", "Category": categories[i % len(categories)], "Base_Price": round(float(np.random.uniform(20.0, 500.0)), 2)}
        for i in range(1, num_products + 1)
    ]
    
    records: List[dict] = []
    for d in dates:
        day_of_week = d.weekday()
        weekend_boost = 1.35 if day_of_week in [5, 6] else 1.0
        
        for s in stores:
            for p in products:
                promo = int(np.random.random() < 0.15)
                promo_boost = 1.5 if promo else 1.0
                price = round(p["Base_Price"] * (0.85 if promo else 1.0), 2)
                
                # Base demand + random variation
                base_demand = np.random.poisson(lam=15.0)
                demand = int(base_demand * weekend_boost * promo_boost + np.random.normal(0, 2))
                demand = max(0, demand)
                
                records.append({
                    "Date": d.strftime("%Y-%m-%d"),
                    "Store_ID": s,
                    "Product_ID": p["Product_ID"],
                    "Category": p["Category"],
                    "Price": price,
                    "Promotion": promo,
                    "Holiday": int(d.month == 12 and d.day == 25),
                    "Units_Sold": demand,
                    "Revenue": round(demand * price, 2),
                })
                
    df = pd.DataFrame(records)
    logger.info(f"Generated synthetic dataset with {len(df)} rows.")
    return df
