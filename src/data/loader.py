"""Data loader module for ingesting raw data files."""
from pathlib import Path
from typing import Optional
import pandas as pd
from src.config import RAW_DIR
from src.utils import get_logger

logger = get_logger(__name__)

def load_sales_data(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load raw sales transactions into a pandas DataFrame."""
    target_path = filepath or (RAW_DIR / "train.csv")
    logger.info(f"Loading sales data from: {target_path}")
    if not target_path.exists():
        raise FileNotFoundError(f"Source file not found at: {target_path}")
    return pd.read_csv(target_path)

def load_store_metadata(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load store dimension metadata."""
    target_path = filepath or (RAW_DIR / "stores.csv")
    logger.info(f"Loading store metadata from: {target_path}")
    if not target_path.exists():
        raise FileNotFoundError(f"Source file not found at: {target_path}")
    return pd.read_csv(target_path)

def load_product_metadata(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load product/item dimension metadata."""
    target_path = filepath or (RAW_DIR / "items.csv")
    logger.info(f"Loading product metadata from: {target_path}")
    if not target_path.exists():
        raise FileNotFoundError(f"Source file not found at: {target_path}")
    return pd.read_csv(target_path)
