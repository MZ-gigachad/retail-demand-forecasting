"""Product and Store Master builders for retail demand forecasting adaptation."""
from pathlib import Path
import logging
import numpy as np
import pandas as pd
from src.config import CFG, EXTERNAL_DIR, INTERIM_DIR

logger = logging.getLogger(__name__)

CAT_MAP = {
    "FOODS": "Grocery & Food",
    "HOUSEHOLD": "Home & Household",
    "HOBBIES": "Toys & Hobbies",
}

DEPT_MAP = {
    "FOODS_1": "Snacks & Beverages",
    "FOODS_2": "Staples & Packaged Food",
    "FOODS_3": "Fresh & Dairy",
    "HOUSEHOLD_1": "Cleaning & Utilities",
    "HOUSEHOLD_2": "Home Decor & Kitchen",
    "HOBBIES_1": "Toys & Games",
    "HOBBIES_2": "Stationery & Crafts",
}

MARGIN = {
    "Grocery & Food": (0.70, 0.88),
    "Home & Household": (0.60, 0.80),
    "Toys & Hobbies": (0.50, 0.75),
}


def build_product_master(long_df: pd.DataFrame) -> pd.DataFrame:
    """Build standardized Product Master dimension table from interim long dataframe."""
    rng = np.random.default_rng(CFG["adaptation"]["seed"])
    items = (
        long_df[["item_id", "dept_id", "cat_id"]]
        .drop_duplicates()
        .sort_values("item_id")
        .reset_index(drop=True)
    )
    items["Product_ID"] = [f"PROD_{i:04d}" for i in range(1, len(items) + 1)]
    items["Category"] = items["cat_id"].astype(str).map(CAT_MAP)
    items["Department"] = items["dept_id"].astype(str).map(DEPT_MAP)
    items["Product_Name"] = (
        items["Department"].astype(str)
        + " Item "
        + items.groupby("dept_id", observed=False).cumcount().add(1).astype(str).str.zfill(3)
    )

    scale = CFG["adaptation"]["price_scale"]
    jitter = CFG["adaptation"]["price_jitter"]
    u = rng.uniform(-1, 1, len(items))
    items["Price_Factor"] = items["cat_id"].astype(str).map(scale) * (1 + jitter * u)

    items["Lead_Time_Days"] = rng.integers(2, 8, len(items))
    items["Min_Order_Qty"] = rng.choice([6, 12, 24], len(items))
    items["Shelf_Life_Days"] = np.where(
        items["dept_id"] == "FOODS_3", rng.integers(3, 15, len(items)), np.nan
    )
    items = items.rename(columns={"item_id": "Source_Item_ID"})
    logger.info("Built product master with %d products.", len(items))
    return items.drop(columns=["dept_id", "cat_id"])


def build_store_master(long_df: pd.DataFrame) -> pd.DataFrame:
    """Build standardized Store Master dimension table mapped to Indian retail stores."""
    mapping_path = EXTERNAL_DIR / "store_mapping.csv"
    if not mapping_path.exists():
        raise FileNotFoundError(f"Store mapping not found at {mapping_path}")
    mapping = pd.read_csv(mapping_path)
    totals = (
        long_df.groupby("store_id", observed=True)["Units_Sold"]
        .sum()
        .rename("total_units")
    )
    sm = mapping.merge(totals, left_on="Source_Store_ID", right_index=True, how="inner")
    sm = sm.sort_values("total_units", ascending=False).reset_index(drop=True)
    n = len(sm)
    sm["Store_Type"] = (
        ["Hypermarket"] * (n // 3)
        + ["Supermarket"] * (n // 3)
        + ["Express"] * (n - 2 * (n // 3))
    )
    rng = np.random.default_rng(CFG["adaptation"]["seed"])
    size_ranges = {
        "Hypermarket": (40000, 70000),
        "Supermarket": (10000, 25000),
        "Express": (2000, 6000),
    }
    sm["Size_Sqft"] = [int(rng.integers(*size_ranges[t])) for t in sm["Store_Type"]]
    sm["Opening_Date"] = pd.Timestamp("2010-01-01")
    logger.info("Built store master with %d stores.", len(sm))
    return sm.drop(columns="total_units").sort_values("Store_ID").reset_index(drop=True)
