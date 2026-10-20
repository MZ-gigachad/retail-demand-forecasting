"""Price conversion to INR and promotion derivation modules."""
import logging
from typing import Optional
import numpy as np
import pandas as pd
from src.config import CFG
from src.data.build_masters import MARGIN

logger = logging.getLogger(__name__)


def to_inr(long_df: pd.DataFrame, product_master: pd.DataFrame) -> pd.DataFrame:
    """Convert USD benchmark sell prices to INR using item-specific price scale factors."""
    pm = product_master[["Source_Item_ID", "Product_ID", "Price_Factor"]]
    df = long_df.merge(
        pm, left_on="item_id", right_on="Source_Item_ID", how="left", validate="m:1"
    )
    if not df["Product_ID"].notna().all():
        unmapped = df[df["Product_ID"].isna()]["item_id"].unique()
        raise ValueError(f"Unmapped items found in dataset: {unmapped}")
    df["Price"] = (df["Price"] * df["Price_Factor"]).round(2)
    logger.info("Converted prices to INR with item price factors.")
    return df.drop(columns=["Source_Item_ID"])


def complete_product_master(
    product_master: pd.DataFrame, df: pd.DataFrame
) -> pd.DataFrame:
    """Complete product master with Base_Price (median INR price) and Unit_Cost."""
    base = (
        df.dropna(subset=["Price"])
        .groupby("Product_ID")["Price"]
        .median()
        .rename("Base_Price")
    )
    pm = product_master.drop(columns=["Base_Price"], errors="ignore").merge(
        base, on="Product_ID", how="left"
    )
    rng = np.random.default_rng(CFG["adaptation"]["seed"] + 1)
    lo_hi = pm["Category"].map(MARGIN)
    cost_ratio = [rng.uniform(lo, hi) for lo, hi in lo_hi]
    pm["Unit_Cost"] = (pm["Base_Price"] * np.array(cost_ratio)).round(2)
    logger.info("Completed product master with Base_Price and Unit_Cost.")
    return pm


def derive_promotions(
    df: pd.DataFrame,
    window_weeks: Optional[int] = None,
    min_periods: Optional[int] = None,
    min_discount: Optional[float] = None,
) -> pd.DataFrame:
    """Derive promotion flag, regular price, and discount % from price drops."""
    promo_cfg = CFG.get("adaptation", {}).get("promo", {})
    if window_weeks is None:
        window_weeks = promo_cfg.get("window_weeks", 13)
    if min_periods is None:
        min_periods = promo_cfg.get("min_periods", 4)
    if min_discount is None:
        min_discount = promo_cfg.get("min_discount", 0.05)

    keys = ["store_id", "item_id"]
    wk = (
        df[keys + ["wm_yr_wk", "Price"]]
        .drop_duplicates()
        .sort_values(keys + ["wm_yr_wk"])
        .reset_index(drop=True)
    )

    wk["Regular_Price"] = wk.groupby(keys, observed=True)["Price"].transform(
        lambda s: s.shift(1).rolling(window_weeks, min_periods=min_periods).median()
    )
    disc = 1 - wk["Price"] / wk["Regular_Price"]
    wk["Discount_Pct"] = disc.clip(lower=0).fillna(0).round(4)
    wk["Promotion"] = (wk["Discount_Pct"] >= min_discount).astype("int8")
    wk["Regular_Price"] = wk["Regular_Price"].fillna(wk["Price"]).round(2)

    out = df.merge(
        wk[keys + ["wm_yr_wk", "Regular_Price", "Discount_Pct", "Promotion"]],
        on=keys + ["wm_yr_wk"],
        how="left",
        validate="m:1",
    )
    logger.info(
        "Derived promotions: %.2f%% of store-item-weeks flagged with discount >= %.2f%%",
        (wk["Promotion"].mean() * 100),
        min_discount * 100,
    )
    return out
