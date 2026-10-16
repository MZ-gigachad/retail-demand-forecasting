"""Download raw datasets into data/raw. Safe to re-run."""
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

from src.config import RAW_DIR, SEED
from src.utils import get_logger

logger = get_logger(__name__)

COMPETITION = "m5-forecasting-accuracy"
TARGET_DIR: Path = RAW_DIR / "m5"


def check_kaggle_installed() -> bool:
    """Check if the kaggle command-line tool is available."""
    return shutil.which("kaggle") is not None


def check_kaggle_credentials() -> bool:
    """Check if kaggle credentials exist in the standard user home path."""
    home_kaggle = Path.home() / ".kaggle" / "kaggle.json"
    env_user = os.environ.get("KAGGLE_USERNAME")
    env_key = os.environ.get("KAGGLE_KEY")
    return home_kaggle.exists() or bool(env_user and env_key)


def extract_zip(zip_path: Path, destination: Path) -> None:
    """Extract an archive and remove the zip to save disk space."""
    logger.info(f"Extracting {zip_path.name} to {destination}...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(destination)
    logger.info("Extraction complete.")
    try:
        zip_path.unlink()
        logger.info(f"Removed archive {zip_path.name} to save disk space.")
    except OSError as e:
        logger.warning(f"Could not remove archive {zip_path}: {e}")


def download_m5(target_dir: Optional[Path] = None, force: bool = False) -> Path:
    """Download the M5 Forecasting competition dataset using Kaggle CLI.

    Falls back gracefully with actionable instructions if Kaggle CLI or
    credentials are not present.
    """
    out_dir = target_dir or TARGET_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    eval_file = out_dir / "sales_train_evaluation.csv"
    val_file = out_dir / "sales_train_validation.csv"

    if not force and (eval_file.exists() or val_file.exists()):
        logger.info(f"M5 dataset already present at: {out_dir}. Skipping download.")
        return out_dir

    # Check for downloaded zip in downloads or target folder
    downloads_dir = Path.home() / "Downloads"
    candidate_zips = [
        out_dir / f"{COMPETITION}.zip",
        downloads_dir / f"{COMPETITION}.zip",
    ]
    for cz in candidate_zips:
        if cz.exists():
            logger.info(f"Found existing dataset archive at {cz}")
            extract_zip(cz, out_dir)
            return out_dir

    if not check_kaggle_installed():
        logger.error(
            "The 'kaggle' CLI tool is not installed or not in PATH.\n"
            "To install in your active environment:\n"
            "    pip install kaggle\n"
            "Alternatively, manually download from:\n"
            "    https://www.kaggle.com/competitions/m5-forecasting-accuracy/data\n"
            f"and place the CSV files directly into '{out_dir}'."
        )
        raise RuntimeError("Kaggle CLI not found. Please install or place files manually.")

    if not check_kaggle_credentials():
        logger.error(
            "Kaggle API credentials not found.\n"
            "Please download your 'kaggle.json' API token from your Kaggle Account Settings and place it at:\n"
            f"    {Path.home() / '.kaggle' / 'kaggle.json'}\n"
            "Or set the environment variables KAGGLE_USERNAME and KAGGLE_KEY."
        )
        raise RuntimeError("Kaggle credentials not configured.")

    logger.info(f"Downloading M5 competition files to {out_dir} via Kaggle API...")
    cmd = ["kaggle", "competitions", "download", "-c", COMPETITION, "-p", str(out_dir)]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    logger.info(f"Kaggle output: {res.stdout.strip()}")

    zip_path = out_dir / f"{COMPETITION}.zip"
    if zip_path.exists():
        extract_zip(zip_path, out_dir)
    else:
        # Check if individual files were downloaded as separate zips
        for z in out_dir.glob("*.zip"):
            extract_zip(z, out_dir)

    return out_dir


def generate_m5_sample(
    target_dir: Optional[Path] = None,
    num_stores: int = 10,
    items_per_cat: int = 40,
    days: int = 730,
) -> Path:
    """Generate an exact M5-schema compatible sample dataset.

    Produces `calendar.csv`, `sales_train_evaluation.csv`, and `sell_prices.csv`
    in exact M5 format. Useful for offline testing, CI environments, and
    immediate development without waiting for multi-gigabyte downloads.
    """
    out_dir = target_dir or TARGET_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Generating realistic M5-schema sample in: {out_dir}...")
    np.random.seed(SEED)

    # 1. Calendar
    start_date = pd.Timestamp("2014-01-01")
    dates = pd.date_range(start_date, periods=days, freq="D")
    d_cols = [f"d_{i+1}" for i in range(days)]

    # M5 retail calendar week: wm_yr_wk is roughly 11401 to 11652 etc.
    cal_df = pd.DataFrame({
        "date": dates,
        "wm_yr_wk": [11400 + (i // 7) for i in range(days)],
        "weekday": dates.day_name(),
        "wday": [((d.dayofweek + 2) % 7) + 1 for d in dates], # M5 1=Saturday
        "month": dates.month,
        "year": dates.year,
        "d": d_cols,
        "event_name_1": np.where((dates.month == 12) & (dates.day == 25), "Christmas",
                        np.where((dates.month == 1) & (dates.day == 1), "NewYear", None)),
        "event_type_1": np.where((dates.month == 12) & (dates.day == 25), "National",
                        np.where((dates.month == 1) & (dates.day == 1), "National", None)),
        "event_name_2": None,
        "event_type_2": None,
        "snap_CA": np.random.choice([0, 1], size=days, p=[0.7, 0.3]),
        "snap_TX": np.random.choice([0, 1], size=days, p=[0.7, 0.3]),
        "snap_WI": np.random.choice([0, 1], size=days, p=[0.7, 0.3]),
    })
    cal_df.to_csv(out_dir / "calendar.csv", index=False)

    # 2. Stores and Items
    stores = [
        "CA_1", "CA_2", "CA_3", "CA_4",
        "TX_1", "TX_2", "TX_3",
        "WI_1", "WI_2", "WI_3"
    ][:num_stores]

    categories = ["FOODS", "HOBBIES", "HOUSEHOLD"]
    dept_map = {
        "FOODS": ["FOODS_1", "FOODS_2", "FOODS_3"],
        "HOBBIES": ["HOBBIES_1", "HOBBIES_2"],
        "HOUSEHOLD": ["HOUSEHOLD_1", "HOUSEHOLD_2"]
    }

    items_meta = []
    for cat in categories:
        depts = dept_map[cat]
        for i in range(1, items_per_cat + 1):
            dept = depts[i % len(depts)]
            item_id = f"{dept}_{i:03d}"
            base_price = round(float(np.random.uniform(1.5, 25.0)), 2)
            items_meta.append({"cat_id": cat, "dept_id": dept, "item_id": item_id, "base_price": base_price})

    # 3. Sales wide format
    sales_rows = []
    price_rows = []
    unique_weeks = cal_df["wm_yr_wk"].unique()

    for s in stores:
        state = s.split("_")[0]
        for item in items_meta:
            row_id = f"{item['item_id']}_{s}_evaluation"

            # Poisson/intermittent daily demand
            lam = np.random.uniform(0.5, 8.0) if item["cat_id"] == "FOODS" else np.random.uniform(0.1, 3.0)
            daily_sales = np.random.poisson(lam=lam, size=days)
            # Add some zero inflation / intermittency
            mask_zero = np.random.rand(days) < 0.25
            daily_sales[mask_zero] = 0

            row_dict = {
                "id": row_id,
                "item_id": item["item_id"],
                "dept_id": item["dept_id"],
                "cat_id": item["cat_id"],
                "store_id": s,
                "state_id": state,
            }
            for d_idx, col in enumerate(d_cols):
                row_dict[col] = int(daily_sales[d_idx])
            sales_rows.append(row_dict)

            # Generate weekly prices
            for wk in unique_weeks:
                # Occasional promo markdown
                discount = 0.85 if np.random.rand() < 0.15 else 1.0
                p = round(item["base_price"] * discount, 2)
                price_rows.append({
                    "store_id": s,
                    "item_id": item["item_id"],
                    "wm_yr_wk": wk,
                    "sell_price": p,
                })

    sales_df = pd.DataFrame(sales_rows)
    sales_df.to_csv(out_dir / "sales_train_evaluation.csv", index=False)
    sales_df.to_csv(out_dir / "sales_train_validation.csv", index=False)

    prices_df = pd.DataFrame(price_rows)
    prices_df.to_csv(out_dir / "sell_prices.csv", index=False)

    logger.info(
        f"M5 sample generated successfully: {len(sales_df)} series, {days} days, "
        f"{len(prices_df)} price records."
    )
    return out_dir


if __name__ == "__main__":
    try:
        download_m5()
    except Exception as exc:
        logger.warning(f"Live Kaggle download could not proceed ({exc}).")
        logger.info("Generating representative M5-schema dataset for development...")
        generate_m5_sample()
