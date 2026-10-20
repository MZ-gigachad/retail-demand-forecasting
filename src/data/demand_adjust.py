"""Documented festival demand uplift adjustment for Indian retail seasonality."""
import logging
import numpy as np
import pandas as pd
from src.config import CFG

logger = logging.getLogger(__name__)


def apply_festival_uplift(df: pd.DataFrame) -> pd.DataFrame:
    """Apply documented category-specific demand uplift during Indian festival windows.

    Preserves original target values in Units_Sold_Original for full auditability
    and uses stochastic rounding to ensure integer counts.
    """
    cfg = CFG.get("adaptation", {}).get("festival_uplift", {})
    df["Units_Sold_Original"] = df["Units_Sold"].copy()

    if not cfg.get("enabled", True):
        logger.info("Festival uplift disabled in config; keeping original Units_Sold.")
        return df

    rng = np.random.default_rng(CFG["adaptation"]["seed"] + 2)
    by_category = cfg.get("by_category", {})
    uplift = df["Category"].map(by_category).fillna(0.0).to_numpy()
    window = df["Festival_Window"].fillna(0).to_numpy()
    factor = 1.0 + uplift * window

    x = df["Units_Sold_Original"].to_numpy().astype(float) * factor
    base = np.floor(x)
    frac = x - base

    df["Units_Sold"] = (base + (rng.random(len(df)) < frac)).astype("int16")
    n_uplifted = int(((df["Festival_Window"] == 1) & (df["Units_Sold_Original"] > 0)).sum())
    logger.info(
        "Applied festival uplift (enabled=%s) affecting %d positive sales rows.",
        cfg.get("enabled", True),
        n_uplifted,
    )
    return df
