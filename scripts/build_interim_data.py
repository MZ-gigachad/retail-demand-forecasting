
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

import numpy as np

from src.config import INTERIM_DIR, SEED
from src.data.loader import (
    attach_prices,
    load_calendar,
    load_prices,
    load_sales_wide,
    stratified_item_sample,
    wide_to_long,
)
from src.utils import get_logger

logger = get_logger("build_interim_data")


def run_pipeline():
    logger.info("=" * 60)
    logger.info("Starting Day 2 Data Collection & Interim Pipeline")
    logger.info("=" * 60)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load calendar
    calendar = load_calendar()
    calendar_min = calendar["date"].min().strftime("%Y-%m-%d")
    calendar_max = calendar["date"].max().strftime("%Y-%m-%d")
    calendar_days = len(calendar)
    events_count = calendar["event_name_1"].notna().sum()

    # 2. Load weekly prices
    prices = load_prices()
    num_price_records = len(prices)
    price_mean = float(prices["sell_price"].mean())
    price_min = float(prices["sell_price"].min())
    price_max = float(prices["sell_price"].max())

    # 3. Load full wide-format sales
    sales_wide = load_sales_wide()
    num_series = len(sales_wide)

    stores = sorted(sales_wide["store_id"].astype(str).unique().tolist())
    categories = sorted(sales_wide["cat_id"].astype(str).unique().tolist())
    departments = sorted(sales_wide["dept_id"].astype(str).unique().tolist())
    items = sorted(sales_wide["item_id"].astype(str).unique().tolist())

    day_cols = [c for c in sales_wide.columns if c.startswith("d_")]
    sales_days = len(day_cols)

    # Sales dates correspond to d_ columns, not the entire calendar.
    day_mapping = calendar.set_index("d")["date"]
    first_day = f"d_{1}"
    last_day = f"d_{sales_days}"

    sales_date_min = day_mapping.loc[first_day].strftime("%Y-%m-%d")
    sales_date_max = day_mapping.loc[last_day].strftime("%Y-%m-%d")

    sales_matrix = sales_wide[day_cols].to_numpy()
    total_sales_units = int(np.sum(sales_matrix))
    total_cells = sales_matrix.size
    zero_cells = int(np.sum(sales_matrix == 0))
    zero_share_pct = (zero_cells / total_cells * 100) if total_cells else 0.0

    full_reshaped_rows = num_series * sales_days

    logger.info("--- Raw Data Profile Summary ---")
    logger.info(
        f"Sales date range: {sales_date_min} to {sales_date_max} "
        f"({sales_days} sales days)"
    )
    logger.info(
        f"Calendar date range: {calendar_min} to {calendar_max} "
        f"({calendar_days} calendar days)"
    )
    logger.info(
        f"Series count: {num_series:,} "
        f"({len(stores)} stores, {len(items)} items)"
    )
    logger.info(f"Categories: {categories}")
    logger.info(f"Total sales units: {total_sales_units:,}")
    logger.info(
        f"Zero-sales cells: {zero_cells:,}/{total_cells:,} "
        f"({zero_share_pct:.1f}%)"
    )
    logger.info(
        f"Weekly price records: {num_price_records:,}; "
        f"range: ${price_min:.2f}-${price_max:.2f}; "
        f"mean: ${price_mean:.2f}"
    )

    # 4. Select 12 items per category and demand bucket.
    # Expected target: 3 categories x 3 buckets x 12 = 108 items.
    logger.info("--- Performing Stratified Sampling ---")
    stratified_items_df = stratified_item_sample(
        sales_wide,
        n_per_cat_bucket=12,
        seed=SEED,
    )

    selected_items_path = INTERIM_DIR / "selected_items.csv"
    stratified_items_df.to_csv(selected_items_path, index=False)
    logger.info(
        f"Saved {len(stratified_items_df)} selected items to "
        f"{selected_items_path}"
    )

    selected_item_ids = stratified_items_df["item_id"].astype(str).tolist()

    # 5. Load only the selected items.
    subset_wide = load_sales_wide(items=selected_item_ids)
    subset_series_count = len(subset_wide)

    subset_day_cols = [
        c for c in subset_wide.columns if c.startswith("d_")
    ]
    if subset_day_cols != day_cols:
        raise ValueError(
            "Selected sales data does not have the same daily columns "
            "as the full sales data."
        )

    subset_wide_units_sum = int(
        subset_wide[subset_day_cols].to_numpy().sum()
    )

    # 6. Convert selected sales to long format.
    logger.info("--- Reshaping Subset to Long Format ---")
    long_df = wide_to_long(subset_wide, calendar)

    # 7. Attach weekly prices.
    logger.info("--- Attaching Weekly Prices ---")
    long_with_prices = attach_prices(long_df, prices)

    # 8. Save the interim dataset.
    interim_parquet_path = INTERIM_DIR / "m5_subset_long.parquet"
    logger.info(f"Saving interim dataset to {interim_parquet_path}")
    long_with_prices.to_parquet(interim_parquet_path, index=False)

    parquet_size_mb = interim_parquet_path.stat().st_size / 1e6
    logger.info(
        f"Saved {len(long_with_prices):,} rows "
        f"({parquet_size_mb:.2f} MB)"
    )

    # 9. Validate the dataset.
    logger.info("--- Running Sanity Checks ---")

    expected_rows = subset_series_count * len(subset_day_cols)
    actual_rows = len(long_with_prices)

    assert actual_rows == expected_rows, (
        f"Row count mismatch: expected {expected_rows:,}, "
        f"got {actual_rows:,}"
    )
    logger.info(
        f"Sanity Check 1 - Row count: PASS ({actual_rows:,} rows)"
    )

    long_units_sum = int(long_with_prices["Units_Sold"].sum())
    assert long_units_sum == subset_wide_units_sum, (
        f"Sales sum mismatch: wide={subset_wide_units_sum:,}, "
        f"long={long_units_sum:,}"
    )
    logger.info(
        f"Sanity Check 2 - Units preserved: PASS ({long_units_sum:,})"
    )

    duplicate_keys = long_with_prices.duplicated(
        subset=["Date", "store_id", "item_id"]
    ).sum()

    assert duplicate_keys == 0, (
        f"Found {duplicate_keys:,} duplicate Date/store/item keys"
    )
    logger.info("Sanity Check 3 - Unique date/store/item keys: PASS")

    missing_price_count = int(long_with_prices["Price"].isna().sum())
    missing_price_pct = (
        missing_price_count / actual_rows * 100 if actual_rows else 0.0
    )
    priced_rows = actual_rows - missing_price_count

    logger.info(
        f"Sanity Check 4 - Price coverage: "
        f"{priced_rows:,}/{actual_rows:,} priced rows; "
        f"{missing_price_pct:.2f}% missing prices"
    )

    # 10. Print the data profile for the documentation.
    print("\n" + "=" * 60)
    print("DATA PROFILE REPORT FOR docs/data_sources.md")
    print("=" * 60)

    report = f"""
| Metric | Value |
|---|---|
| Sales date range | {sales_date_min} to {sales_date_max} |
| Number of sales days | {sales_days:,} |
| Full calendar range | {calendar_min} to {calendar_max} |
| Number of calendar days | {calendar_days:,} |
| Stores | {len(stores)} ({', '.join(stores)}) |
| Total raw items | {len(items):,} |
| Selected item records | {len(stratified_items_df):,} |
| Categories | {len(categories)} ({', '.join(categories)}) |
| Departments | {len(departments)} |
| Full sales series | {num_series:,} |
| Subset sales series | {subset_series_count:,} |
| Full reshaped row estimate | {full_reshaped_rows:,} |
| Interim subset rows | {actual_rows:,} |
| Total raw sales units | {total_sales_units:,} |
| Subset sales units | {long_units_sum:,} |
| Zero-sales cells | {zero_share_pct:.2f}% |
| Missing subset prices | {missing_price_pct:.2f}% |
| Price range (USD) | ${price_min:.2f}-${price_max:.2f} |
| Mean price (USD) | ${price_mean:.2f} |
| Calendar events | {events_count:,} |
"""
    print(report)
    print("=" * 60)

    return {
        "sales_date_min": sales_date_min,
        "sales_date_max": sales_date_max,
        "calendar_days": calendar_days,
        "sales_days": sales_days,
        "stores": stores,
        "items_count": len(items),
        "selected_items_count": len(stratified_items_df),
        "categories": categories,
        "departments": departments,
        "num_series": num_series,
        "subset_series_count": subset_series_count,
        "full_reshaped_rows": full_reshaped_rows,
        "actual_rows": actual_rows,
        "total_sales_units": total_sales_units,
        "long_units_sum": long_units_sum,
        "zero_share_pct": zero_share_pct,
        "missing_price_count": missing_price_count,
        "missing_price_pct": missing_price_pct,
        "price_min": price_min,
        "price_max": price_max,
        "price_mean": price_mean,
        "events_count": int(events_count),
    }


if __name__ == "__main__":
    run_pipeline()
