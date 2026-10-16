"""Data loader module for ingesting, transforming, and subsetting M5 retail data."""
from pathlib import Path
from typing import List, Optional, Sequence, Union

import numpy as np
import pandas as pd

from src.config import INTERIM_DIR, RAW_DIR, SEED
from src.utils import get_logger

logger = get_logger(__name__)

M5_DIR: Path = RAW_DIR / "m5_original"
ID_COLS: List[str] = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]


def load_calendar(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load calendar metadata with parsed dates and optimized category types.

    Args:
        filepath: Optional custom path to calendar.csv. Defaults to RAW_DIR / "m5" / "calendar.csv".

    Returns:
        DataFrame containing calendar features and day identifiers (d_1 ... d_N).
    """
    path = filepath or (M5_DIR / "calendar.csv")
    if not path.exists():
        raise FileNotFoundError(f"Calendar file not found at: {path}")

    logger.info(f"Loading calendar data from: {path}")
    cal = pd.read_csv(path, parse_dates=["date"])

    cat_cols = ["weekday", "event_name_1", "event_type_1", "event_name_2", "event_type_2"]
    for col in cat_cols:
        if col in cal.columns:
            cal[col] = cal[col].astype("category")

    if "wm_yr_wk" in cal.columns:
        cal["wm_yr_wk"] = cal["wm_yr_wk"].astype("int32")

    logger.info(f"Loaded calendar: {cal.shape[0]} days from {cal['date'].min().date()} to {cal['date'].max().date()}")
    return cal


def load_prices(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load weekly store-item prices with memory-efficient dtypes.

    Args:
        filepath: Optional custom path to sell_prices.csv.

    Returns:
        DataFrame of weekly sell prices per store and item.
    """
    path = filepath or (M5_DIR / "sell_prices.csv")
    if not path.exists():
        raise FileNotFoundError(f"Price file not found at: {path}")

    logger.info(f"Loading sell prices from: {path}")
    prices = pd.read_csv(
        path,
        dtype={
            "store_id": "category",
            "item_id": "category",
            "wm_yr_wk": "int32",
            "sell_price": "float32",
        },
    )
    logger.info(f"Loaded prices: {prices.shape[0]:,} records across {prices['store_id'].nunique()} stores")
    return prices


def load_sales_wide(
    filepath: Optional[Path] = None,
    stores: Optional[Sequence[str]] = None,
    items: Optional[Sequence[str]] = None,
    cats: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    """Load wide-format sales table with optional early filtering to save memory.

    Args:
        filepath: Path to sales_train_evaluation.csv (or validation fallback).
        stores: Sequence of store IDs to filter (e.g. ['CA_1', 'TX_1']).
        items: Sequence of item IDs to filter.
        cats: Sequence of category IDs to filter (e.g. ['FOODS']).

    Returns:
        Filtered wide-format DataFrame with downcast int16 day columns.
    """
    target_path = filepath
    if target_path is None:
        eval_path = M5_DIR / "sales_train_evaluation.csv"
        val_path = M5_DIR / "sales_train_validation.csv"
        target_path = eval_path if eval_path.exists() else val_path

    if not target_path.exists():
        raise FileNotFoundError(f"Sales wide file not found at: {target_path}")

    logger.info(f"Loading wide sales from: {target_path}")
    df = pd.read_csv(target_path)

    # Apply early filtering before dtype conversion
    initial_rows = len(df)
    if stores is not None:
        df = df[df["store_id"].isin(stores)]
    if items is not None:
        df = df[df["item_id"].isin(items)]
    if cats is not None:
        df = df[df["cat_id"].isin(cats)]

    if len(df) < initial_rows:
        logger.info(f"Filtered sales series from {initial_rows:,} down to {len(df):,}")

    day_cols = [c for c in df.columns if c.startswith("d_")]
    df[day_cols] = df[day_cols].astype("int16")

    # Downcast metadata categories
    for col in ["dept_id", "cat_id", "store_id", "state_id"]:
        if col in df.columns:
            df[col] = df[col].astype("category")

    return df.reset_index(drop=True)


def wide_to_long(sales_wide: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    """Melt wide d_* columns into normalized daily time series.

    Args:
        sales_wide: Wide format DataFrame containing d_* columns.
        calendar: Calendar DataFrame containing 'd', 'date', and 'wm_yr_wk'.

    Returns:
        Long-format DataFrame with 'Date', 'Units_Sold', and standard identifiers.
    """
    day_cols = [c for c in sales_wide.columns if c.startswith("d_")]
    existing_id_cols = [c for c in ID_COLS if c in sales_wide.columns]

    logger.info(f"Melting {len(sales_wide):,} series over {len(day_cols)} day columns...")
    long_df = sales_wide.melt(
        id_vars=existing_id_cols,
        value_vars=day_cols,
        var_name="d",
        value_name="Units_Sold",
    )

    # Merge calendar mapping for date and retail week
    cal_cols = ["d", "date", "wm_yr_wk"]
    cal_subset = calendar[cal_cols].copy()

    long_df = long_df.merge(cal_subset, on="d", how="left")
    long_df["Units_Sold"] = long_df["Units_Sold"].astype("int16")

    # Clean up and normalize Date column
    long_df = long_df.drop(columns=["d"]).rename(columns={"date": "Date"})
    logger.info(f"Reshaping complete: produced {len(long_df):,} rows.")
    return long_df


def attach_prices(sales_long: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Join weekly shelf prices to daily sales rows by store, item, and retail week.

    Args:
        sales_long: Long-format DataFrame containing 'store_id', 'item_id', 'wm_yr_wk'.
        prices: Weekly price DataFrame with 'store_id', 'item_id', 'wm_yr_wk', 'sell_price'.

    Returns:
        DataFrame with 'Price' column added.
    """
    initial_len = len(sales_long)
    logger.info("Attaching weekly sell prices...")

    # Ensure key types match to prevent categorical merge mismatches
    sales_long = sales_long.copy()
    prices_subset = prices[["store_id", "item_id", "wm_yr_wk", "sell_price"]].copy()

    sales_long["store_id"] = sales_long["store_id"].astype(str)
    sales_long["item_id"] = sales_long["item_id"].astype(str)
    prices_subset["store_id"] = prices_subset["store_id"].astype(str)
    prices_subset["item_id"] = prices_subset["item_id"].astype(str)

    merged = sales_long.merge(
        prices_subset,
        on=["store_id", "item_id", "wm_yr_wk"],
        how="left",
    )

    if len(merged) != initial_len:
        raise ValueError(
            f"Price join resulted in row count explosion: {initial_len:,} -> {len(merged):,}. "
            "Check for duplicate keys in sell_prices.csv."
        )

    merged = merged.rename(columns={"sell_price": "Price"})
    missing_prices = merged["Price"].isna().sum()
    if missing_prices > 0:
        pct = (missing_prices / len(merged)) * 100
        logger.info(f"Note: {missing_prices:,} ({pct:.1f}%) rows have missing prices (pre-launch period).")

    return merged


def stratified_item_sample(
    sales_wide: pd.DataFrame,
    n_per_cat_bucket: int = 15,
    seed: int = SEED,
) -> pd.DataFrame:
    """Select a stratified, reproducible sample of items across categories and demand terciles.

    Args:
        sales_wide: Full wide sales DataFrame.
        n_per_cat_bucket: Number of items to sample per category and demand bucket.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame of sampled items with total units and demand bucket assignment.
    """
    logger.info(f"Performing stratified item sampling (target: {n_per_cat_bucket} items/bucket)...")
    day_cols = [c for c in sales_wide.columns if c.startswith("d_")]

    # Stratify items into low, medium, and high demand terciles per category
    item_totals = (
        sales_wide.assign(total=sales_wide[day_cols].sum(axis=1))
        .groupby(["cat_id", "item_id"], observed=True)["total"]
        .sum()
        .reset_index()
    )

    def assign_buckets(series: pd.Series) -> pd.Series:
        return pd.qcut(
            series.rank(method="first"),
            q=3,
            labels=["low", "med", "high"],
        )

    item_totals["bucket"] = (
        item_totals.groupby("cat_id", observed=True)["total"]
        .transform(assign_buckets)
    )

    # Sample reproducibly within each stratum
    sampled_indices = []
    for _, group in item_totals.groupby(["cat_id", "bucket"], observed=True):
        take_n = min(len(group), n_per_cat_bucket)
        sampled_indices.extend(group.sample(n=take_n, random_state=seed).index.tolist())

    sampled = item_totals.loc[sampled_indices].reset_index(drop=True)

    logger.info(
        f"Sampled {len(sampled)} items across {sampled['cat_id'].nunique()} categories "
        f"and {sampled['bucket'].nunique()} demand terciles."
    )
    return sampled


def load_m5_long(
    stores: Optional[Sequence[str]] = None,
    items: Optional[Sequence[str]] = None,
    cats: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    """Convenience end-to-end pipeline: load calendar, prices, and wide sales, then return long table."""
    cal = load_calendar()
    prices = load_prices()
    sales_wide = load_sales_wide(stores=stores, items=items, cats=cats)
    sales_long = wide_to_long(sales_wide, cal)
    return attach_prices(sales_long, prices)


# Backwards compatibility wrappers
def load_sales_data(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Legacy wrapper: Load raw sales transactions."""
    return load_sales_wide(filepath=filepath)


def load_store_metadata(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Legacy wrapper: Load store metadata from raw dir."""
    target_path = filepath or (RAW_DIR / "stores.csv")
    if not target_path.exists():
        # Fallback: extract distinct stores from calendar/sales
        m5_sales = M5_DIR / "sales_train_evaluation.csv"
        if m5_sales.exists():
            df = pd.read_csv(m5_sales, nrows=500)
            return df[["store_id", "state_id"]].drop_duplicates().reset_index(drop=True)
        raise FileNotFoundError(f"Store file not found at: {target_path}")
    return pd.read_csv(target_path)


def load_product_metadata(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Legacy wrapper: Load product metadata from raw dir."""
    target_path = filepath or (RAW_DIR / "items.csv")
    if not target_path.exists():
        m5_sales = M5_DIR / "sales_train_evaluation.csv"
        if m5_sales.exists():
            df = pd.read_csv(m5_sales, nrows=500)
            return df[["item_id", "dept_id", "cat_id"]].drop_duplicates().reset_index(drop=True)
        raise FileNotFoundError(f"Product file not found at: {target_path}")
    return pd.read_csv(target_path)
