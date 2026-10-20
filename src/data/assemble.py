"""End-to-end dataset assembly pipeline for retail demand forecasting."""
import logging
from pathlib import Path
import pandas as pd
from src.config import CFG, EXTERNAL_DIR, INTERIM_DIR, RAW_DIR
from src.data.build_masters import build_product_master, build_store_master
from src.data.calendar_india import build_holiday_calendar
from src.data.demand_adjust import apply_festival_uplift
from src.data.inventory import simulate_inventory
from src.data.prices import complete_product_master, derive_promotions, to_inr
from src.data.weather import build_weather_table

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CORE_COLS = [
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

EXTRA_COLS = [
    "Department",
    "City",
    "Discount_Pct",
    "Regular_Price",
    "Rainfall_mm",
    "Holiday_Name",
    "Festival_Window",
    "Stockout_Flag",
    "Shortfall",
    "Units_Sold_Original",
]


def assemble_dataset(
    interim_path: Path = INTERIM_DIR / "m5_subset_long.parquet",
    output_path: Path = RAW_DIR / "retail_demand_raw.parquet",
    save_sample: bool = True,
) -> pd.DataFrame:
    """Run full assembly pipeline merging all dimensions, adaptations, and simulations."""
    logger.info("Loading interim long table from %s...", interim_path)
    df = pd.read_parquet(interim_path)
    n_initial = len(df)
    logger.info("Loaded %d interim observations.", n_initial)

    # 1. Build product and store masters
    logger.info("Building product master...")
    pm_raw = build_product_master(df)

    logger.info("Building store master...")
    sm = build_store_master(df)
    sm.to_parquet(EXTERNAL_DIR / "store_master.parquet", index=False)
    sm.to_parquet(INTERIM_DIR / "store_master.parquet", index=False)

    # 2. Convert prices to INR and complete product master
    logger.info("Converting prices to INR...")
    df = to_inr(df, pm_raw)
    pm = complete_product_master(pm_raw, df)
    pm.to_parquet(EXTERNAL_DIR / "product_master.parquet", index=False)
    pm.to_parquet(INTERIM_DIR / "product_master.parquet", index=False)

    # 3. Derive promotions and regular price
    logger.info("Deriving promotions...")
    df = derive_promotions(df)

    # 4. Indian holiday and festival calendar
    start_date = df["Date"].min()
    end_date = df["Date"].max()
    logger.info("Building holiday calendar from %s to %s...", start_date, end_date)
    holidays_df = build_holiday_calendar(start_date, end_date)
    holidays_df.to_parquet(EXTERNAL_DIR / "holidays_india.parquet", index=False)

    # 5. Weather telemetry
    logger.info("Fetching / generating city weather...")
    weather_df = build_weather_table(
        sm,
        str(pd.to_datetime(start_date).strftime("%Y-%m-%d")),
        str(pd.to_datetime(end_date).strftime("%Y-%m-%d")),
    )

    # 6. Merge store, product, holiday, and weather dimensions
    logger.info("Merging dimensional attributes...")
    df = df.merge(
        sm[["Source_Store_ID", "Store_ID", "City"]],
        left_on="store_id",
        right_on="Source_Store_ID",
        how="left",
        validate="m:1",
    )
    df = df.merge(
        pm[["Product_ID", "Category", "Department"]],
        on="Product_ID",
        how="left",
        validate="m:1",
    )
    df = df.merge(
        holidays_df[["Date", "Holiday", "Holiday_Name", "Festival_Window"]],
        on="Date",
        how="left",
        validate="m:1",
    )
    df = df.merge(
        weather_df[["Date", "City", "Temperature", "Rainfall_mm"]],
        on=["Date", "City"],
        how="left",
        validate="m:1",
    )
    if len(df) != n_initial:
        raise ValueError(f"Row count changed during merges: {len(df)} vs expected {n_initial}")

    # 7. Festival demand uplift
    logger.info("Applying festival demand uplift...")
    df = apply_festival_uplift(df)

    # 8. Inventory simulation
    logger.info("Simulating inventory levels...")
    df = simulate_inventory(df, pm)

    # 9. Compute Revenue
    logger.info("Computing net daily revenue...")
    df["Revenue"] = (df["Units_Sold"] * df["Price"]).round(2)

    # 10. Assemble and sort target schema
    cols_to_keep = CORE_COLS + [c for c in EXTRA_COLS if c in df.columns]
    out = df[cols_to_keep].sort_values(["Store_ID", "Product_ID", "Date"]).reset_index(drop=True)

    # Optimize dtypes
    out["Date"] = pd.to_datetime(out["Date"])
    out["Promotion"] = out["Promotion"].astype("int8")
    out["Holiday"] = out["Holiday"].astype("int8")
    out["Festival_Window"] = out["Festival_Window"].astype("int8")
    out["Units_Sold"] = out["Units_Sold"].astype("int16")
    out["Units_Sold_Original"] = out["Units_Sold_Original"].astype("int16")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Saving assembled dataset to %s...", output_path)
    out.to_parquet(output_path, index=False)
    logger.info("Saved raw dataset: %d rows x %d cols.", len(out), len(out.columns))

    if save_sample:
        sample_dir = output_path.parents[1] / "sample"
        sample_dir.mkdir(parents=True, exist_ok=True)
        sample_path = sample_dir / "sample_sales.csv"
        # Sample first 2 stores, first 3 products across full dates
        sample_stores = out["Store_ID"].drop_duplicates().head(2)
        sample_prods = out["Product_ID"].drop_duplicates().head(3)
        sample_subset = out[
            out["Store_ID"].isin(sample_stores) & out["Product_ID"].isin(sample_prods)
        ].head(5000)
        sample_subset.to_csv(sample_path, index=False)
        logger.info("Saved sample sales dataset to %s (%d rows).", sample_path, len(sample_subset))

    return out


if __name__ == "__main__":
    assemble_dataset()
