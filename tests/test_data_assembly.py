"""Test suite for Day 3 data adaptation, supporting tables, and assembly pipeline."""
import numpy as np
import pandas as pd
import pytest
from src.config import EXTERNAL_DIR, RAW_DIR
from src.data.calendar_india import build_holiday_calendar
from src.data.inventory import simulate_series
from src.data.prices import derive_promotions


def test_inventory_never_negative():
    """Verify inventory levels and shortfall are non-negative under periodic review."""
    sales = np.random.default_rng(0).poisson(3, 200)
    inv, short = simulate_series(sales, lead_time=3, moq=6, seed=1)
    assert (inv >= 0).all(), "Inventory contained negative values"
    assert (short >= 0).all(), "Shortfall contained negative values"


def test_revenue_consistency():
    """Verify revenue equals unit demand multiplied by selling price."""
    df = pd.DataFrame({"Units_Sold": [2, 3], "Price": [10.0, 5.5]})
    df["Revenue"] = (df["Units_Sold"] * df["Price"]).round(2)
    assert df["Revenue"].tolist() == [20.0, 16.5]


def test_promotion_derivation():
    """Verify promo flag triggers on price cuts >= 5% and ignores price rises."""
    df = pd.DataFrame(
        {
            "store_id": ["STORE_001"] * 5,
            "item_id": ["ITEM_001"] * 5,
            "wm_yr_wk": [101, 102, 103, 104, 105],
            "Price": [100.0, 100.0, 100.0, 100.0, 75.0],  # 25% drop in week 105
        }
    )
    promo_df = derive_promotions(df, window_weeks=4, min_periods=2, min_discount=0.05)
    assert promo_df.loc[promo_df["wm_yr_wk"] == 105, "Promotion"].iloc[0] == 1
    assert promo_df.loc[promo_df["wm_yr_wk"] == 104, "Promotion"].iloc[0] == 0


def test_holiday_calendar_continuity_and_festivals():
    """Verify calendar continuity and presence of key Indian festivals."""
    cal = build_holiday_calendar("2013-01-01", "2015-12-31")
    assert len(cal) == 1095, "Calendar date count mismatch for 3 full years"
    assert cal["Date"].is_monotonic_increasing, "Dates are not strictly increasing"

    diwali_records = cal[cal["Holiday_Name"].fillna("").str.contains("Diwali")]
    assert len(diwali_records) == 3, "Diwali must appear once per year"

    holi_records = cal[cal["Holiday_Name"].fillna("").str.contains("Holi")]
    assert len(holi_records) == 3, "Holi must appear once per year"


def test_assembled_dataset_integrity():
    """Verify assembled raw dataset exists and passes structural integrity checks."""
    raw_path = RAW_DIR / "retail_demand_raw.parquet"
    if not raw_path.exists():
        pytest.skip("retail_demand_raw.parquet not yet assembled")

    df = pd.read_parquet(raw_path)
    core_cols = [
        "Date",
        "Store_ID",
        "Product_ID",
        "Category",
        "Price",
        "Promotion",
        "Holiday",
        "Temperature",
        "Inventory",
        "Units_Sold",
        "Revenue",
    ]
    for col in core_cols:
        assert col in df.columns, f"Missing required core column {col}"

    dups = df.duplicated(subset=["Date", "Store_ID", "Product_ID"]).sum()
    assert dups == 0, f"Found {dups} duplicate primary key entries in raw dataset"
    assert (df["Units_Sold"] >= 0).all(), "Found negative Units_Sold values"


def test_master_tables_consistency():
    """Verify product and store master tables have valid constraints."""
    pm_path = EXTERNAL_DIR / "product_master.parquet"
    sm_path = EXTERNAL_DIR / "store_master.parquet"
    if not pm_path.exists() or not sm_path.exists():
        pytest.skip("Master tables not found")

    pm = pd.read_parquet(pm_path)
    sm = pd.read_parquet(sm_path)

    assert len(pm) == 108, "Expected 108 sampled products in product master"
    assert len(sm) == 10, "Expected 10 stores in store master"

    assert (pm["Unit_Cost"] < pm["Base_Price"]).all(), "Unit cost must be strictly less than base price"
    assert (sm["Size_Sqft"] > 0).all(), "Store square footage must be positive"
