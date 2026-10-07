"""Data cleaning and validation module."""
import pandas as pd
from src.config import DATE_COL, STORE_COL, PRODUCT_COL, TARGET_COL
from src.utils import get_logger

logger = get_logger(__name__)

def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and clean sales dataframe ensuring proper formats and sorted order."""
    logger.info("Starting sales data cleaning pipeline.")
    data = df.copy()
    
    # Ensure datetime format
    data[DATE_COL] = pd.to_datetime(data[DATE_COL])
    
    # Remove negative units sold (returns/anomalies) or clip to zero
    if TARGET_COL in data.columns:
        data[TARGET_COL] = data[TARGET_COL].clip(lower=0)
        
    # Sort chronologically per store-product series
    sort_cols = [c for c in [STORE_COL, PRODUCT_COL, DATE_COL] if c in data.columns]
    data = data.sort_values(by=sort_cols).reset_index(drop=True)
    
    logger.info(f"Cleaning complete. Output shape: {data.shape}")
    return data
