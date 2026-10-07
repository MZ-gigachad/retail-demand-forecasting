"""Feature engineering pipeline: Calendar, Lag, and Rolling aggregations."""
from typing import List
import pandas as pd
from src.config import DATE_COL, STORE_COL, PRODUCT_COL, TARGET_COL
from src.utils import get_logger

logger = get_logger(__name__)

def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract temporal features from date column."""
    data = df.copy()
    dates = pd.to_datetime(data[DATE_COL])
    
    data["day_of_week"] = dates.dt.dayofweek
    data["day_of_month"] = dates.dt.day
    data["month"] = dates.dt.month
    data["quarter"] = dates.dt.quarter
    data["year"] = dates.dt.year
    data["is_weekend"] = (dates.dt.dayofweek >= 5).astype(int)
    return data

def add_lag_features(df: pd.DataFrame, lags: List[int] = [1, 7, 14, 28]) -> pd.DataFrame:
    """Generate lagged demand features grouped by store and product."""
    data = df.copy()
    group_cols = [STORE_COL, PRODUCT_COL]
    
    for lag in lags:
        col_name = f"lag_{lag}"
        data[col_name] = data.groupby(group_cols)[TARGET_COL].shift(lag)
        
    return data

def add_rolling_features(df: pd.DataFrame, windows: List[int] = [7, 14, 28]) -> pd.DataFrame:
    """Generate rolling mean demand features grouped by store and product."""
    data = df.copy()
    group_cols = [STORE_COL, PRODUCT_COL]
    
    for window in windows:
        # Shift by 1 first to avoid target leakage at time t
        shifted = data.groupby(group_cols)[TARGET_COL].shift(1)
        data[f"rolling_mean_{window}"] = (
            shifted.groupby([data[c] for c in group_cols])
            .transform(lambda s: s.rolling(window, min_periods=1).mean())
        )
    return data
