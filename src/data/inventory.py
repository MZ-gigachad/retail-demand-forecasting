"""Inventory simulation module implementing periodic review (R, S) order-up-to policy."""
import logging
from typing import Tuple
import numpy as np
import pandas as pd
from src.config import CFG

logger = logging.getLogger(__name__)


def simulate_series(
    sales: np.ndarray,
    lead_time: int,
    moq: int,
    seed: int,
    review: int = 7,
    z: float = 1.65,
    window: int = 28,
    cover: int = 14,
) -> Tuple[np.ndarray, np.ndarray]:
    """Simulate daily inventory position for a single time series under (R, S) policy.

    Parameters
    ----------
    sales : np.ndarray
        Historical daily units sold from launch date onwards.
    lead_time : int
        Replenishment lead time L in days.
    moq : int
        Minimum order quantity / batch multiple.
    seed : int
        RNG seed for review day offset.
    review : int
        Review period R in days.
    z : float
        Safety factor for service level (e.g. 1.65 for ~95%).
    window : int
        Lookback window for rolling demand expectation.
    cover : int
        Initial days of demand cover for opening stock.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        Ending inventory array and shortfall array.
    """
    n = len(sales)
    s = pd.Series(sales, dtype="float64")
    early = max(float(s.iloc[:14].mean()), 0.5)
    mu = s.shift(1).rolling(window, min_periods=7).mean().fillna(early).to_numpy()
    sd = s.shift(1).rolling(window, min_periods=7).std().fillna(0.0).to_numpy()

    rng = np.random.default_rng(seed)
    offset = int(rng.integers(0, review))
    arrivals = np.zeros(n + lead_time + 10)
    stock = float(np.ceil(early * cover))
    on_order = 0.0
    inv = np.zeros(n, dtype="float64")
    short = np.zeros(n, dtype="float64")

    review_lead = review + lead_time
    sqrt_review_lead = np.sqrt(review_lead)

    for t in range(n):
        stock += arrivals[t]
        on_order -= arrivals[t]
        if (t + offset) % review == 0:
            target_s = mu[t] * review_lead + z * sd[t] * sqrt_review_lead
            qty = max(0.0, target_s - (stock + on_order))
            if qty > 0:
                qty = float(np.ceil(qty / moq) * moq)
                arrivals[t + lead_time] += qty
                on_order += qty
        available = stock
        short[t] = max(0.0, float(sales[t]) - available)
        stock = max(0.0, available - float(sales[t]))
        inv[t] = stock

    return inv, short


def simulate_inventory(
    df: pd.DataFrame, product_master: pd.DataFrame
) -> pd.DataFrame:
    """Run inventory simulation across all Store x Product series from first launch date."""
    cfg = CFG.get("adaptation", {}).get("inventory", {})
    review_days = int(cfg.get("review_days", 7))
    service_z = float(cfg.get("service_z", 1.65))
    window = int(cfg.get("window", 28))
    initial_cover_days = int(cfg.get("initial_cover_days", 14))
    seed = int(CFG.get("adaptation", {}).get("seed", 42))

    pm = product_master.set_index("Product_ID")[["Lead_Time_Days", "Min_Order_Qty"]]
    df = df.sort_values(["Store_ID", "Product_ID", "Date"]).reset_index(drop=True)
    df["Inventory"] = np.nan
    df["Shortfall"] = np.nan

    grouped = df.groupby(["Store_ID", "Product_ID"], sort=False).groups
    logger.info("Starting inventory simulation across %d series...", len(grouped))

    for k, (key, idx) in enumerate(grouped.items()):
        sub = df.loc[idx]
        launched = sub["Price"].notna().to_numpy()
        if not launched.any():
            continue
        first = launched.argmax()
        pos = sub.index[first:]
        prod_id = key[1]
        lead_time = int(pm.loc[prod_id, "Lead_Time_Days"])
        moq = int(pm.loc[prod_id, "Min_Order_Qty"])

        inv, short = simulate_series(
            sub.loc[pos, "Units_Sold"].to_numpy(),
            lead_time=lead_time,
            moq=moq,
            seed=seed + k,
            review=review_days,
            z=service_z,
            window=window,
            cover=initial_cover_days,
        )
        df.loc[pos, "Inventory"] = inv
        df.loc[pos, "Shortfall"] = short

    df["Stockout_Flag"] = (df["Inventory"] == 0).astype("float").where(df["Inventory"].notna())
    valid_inv = df["Inventory"].dropna()
    logger.info(
        "Inventory simulation complete. Mean inventory: %.1f, Stockout rate: %.2f%%, Shortfall rate: %.2f%%",
        valid_inv.mean(),
        (valid_inv == 0).mean() * 100,
        (df["Shortfall"].dropna() > 0).mean() * 100,
    )
    return df
