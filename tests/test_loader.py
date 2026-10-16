"""Unit tests for data loader, reshaping, stratified sampling, and integrity verification."""
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.data.loader import (
    attach_prices,
    load_calendar,
    load_prices,
    load_sales_wide,
    stratified_item_sample,
    wide_to_long,
)
from src.data.manifest import parse_manifest, sha256, verify_manifest, write_manifest


@pytest.fixture
def sample_sales_and_calendar():
    """Create a minimal synthetic wide sales DataFrame and matching calendar."""
    wide = pd.DataFrame({
        "id": ["item_1_CA_1_eval", "item_2_CA_1_eval"],
        "item_id": ["item_1", "item_2"],
        "dept_id": ["FOODS_1", "FOODS_1"],
        "cat_id": ["FOODS", "FOODS"],
        "store_id": ["CA_1", "CA_1"],
        "state_id": ["CA", "CA"],
        "d_1": [3, 0],
        "d_2": [5, 2],
        "d_3": [0, 4],
    })

    cal = pd.DataFrame({
        "d": ["d_1", "d_2", "d_3"],
        "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
        "wm_yr_wk": [12001, 12001, 12001],
        "weekday": ["Wednesday", "Thursday", "Friday"],
    })

    prices = pd.DataFrame({
        "store_id": ["CA_1", "CA_1"],
        "item_id": ["item_1", "item_2"],
        "wm_yr_wk": [12001, 12001],
        "sell_price": [2.50, 4.99],
    })

    return wide, cal, prices


def test_wide_to_long_shape_and_sum(sample_sales_and_calendar):
    """Verify that wide_to_long creates exactly (series x days) rows and preserves total sales units."""
    wide, cal, _ = sample_sales_and_calendar
    long_df = wide_to_long(wide, cal)

    # 2 series x 3 days = 6 rows
    assert len(long_df) == 6
    assert "Date" in long_df.columns
    assert "Units_Sold" in long_df.columns
    assert "d" not in long_df.columns

    # Sum check: 3 + 0 + 5 + 2 + 0 + 4 = 14
    assert long_df["Units_Sold"].sum() == 14
    assert long_df["Date"].min() == pd.Timestamp("2020-01-01")
    assert long_df["Date"].max() == pd.Timestamp("2020-01-03")


def test_attach_prices_no_duplicates(sample_sales_and_calendar):
    """Verify that attaching weekly prices does not duplicate rows and assigns correct prices."""
    wide, cal, prices = sample_sales_and_calendar
    long_df = wide_to_long(wide, cal)
    merged = attach_prices(long_df, prices)

    # Row count must remain identical
    assert len(merged) == len(long_df)
    assert "Price" in merged.columns
    assert merged["Price"].isna().sum() == 0

    # Key uniqueness
    dup_count = merged.duplicated(subset=["Date", "store_id", "item_id"]).sum()
    assert dup_count == 0

    # Item prices verified
    item_1_price = merged.loc[merged["item_id"] == "item_1", "Price"].iloc[0]
    item_2_price = merged.loc[merged["item_id"] == "item_2", "Price"].iloc[0]
    assert np.isclose(item_1_price, 2.50)
    assert np.isclose(item_2_price, 4.99)


def test_stratified_item_sample_reproducibility():
    """Verify that stratified_item_sample produces balanced terciles and is reproducible."""
    # Create 30 items across 2 categories
    items = [f"item_{i:02d}" for i in range(30)]
    cats = ["FOODS"] * 15 + ["HOBBIES"] * 15
    wide_data = {
        "id": [f"{it}_store_1" for it in items],
        "item_id": items,
        "dept_id": ["dept_1"] * 30,
        "cat_id": cats,
        "store_id": ["store_1"] * 30,
        "state_id": ["state_1"] * 30,
    }
    # Create distinct sales volumes so terciles are unambiguous
    for d in range(1, 11):
        wide_data[f"d_{d}"] = [i * d for i in range(30)]

    mock_wide = pd.DataFrame(wide_data)

    # Sample 2 items per bucket per category = 2 * 3 * 2 = 12 items
    s1 = stratified_item_sample(mock_wide, n_per_cat_bucket=2, seed=42)
    s2 = stratified_item_sample(mock_wide, n_per_cat_bucket=2, seed=42)

    assert len(s1) == 12
    assert s1["item_id"].tolist() == s2["item_id"].tolist()
    assert set(s1["cat_id"].unique()) == {"FOODS", "HOBBIES"}
    assert set(s1["bucket"].unique()) == {"low", "med", "high"}


def test_manifest_generation_and_verification():
    """Verify that write_manifest and verify_manifest accurately check file hashes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        folder = Path(tmp_dir)
        test_file = folder / "test_data.csv"
        test_file.write_text("Date,Units_Sold\n2020-01-01,10\n", encoding="utf-8")

        # Generate manifest
        manifest_path = write_manifest(folder, source="Unit Test Source")
        assert manifest_path.exists()

        # Verify integrity
        assert verify_manifest(folder) is True

        # Tamper with file and verify detection
        test_file.write_text("Date,Units_Sold\n2020-01-01,999\n", encoding="utf-8")
        assert verify_manifest(folder) is False


def test_m5_raw_files_exist_and_loadable():
    """Verify that real/generated M5 raw files exist and can be loaded with loaders."""
    from src.config import RAW_DIR
    m5_dir = RAW_DIR / "m5"
    if (m5_dir / "calendar.csv").exists():
        cal = load_calendar()
        assert len(cal) > 0
        assert "date" in cal.columns

        prices = load_prices()
        assert len(prices) > 0
        assert "sell_price" in prices.columns

        wide = load_sales_wide(stores=["CA_1"])
        assert len(wide) > 0
        assert (wide["store_id"] == "CA_1").all()
