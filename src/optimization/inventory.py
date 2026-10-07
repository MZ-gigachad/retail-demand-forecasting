"""Inventory optimization module: Safety Stock, Reorder Point, and Simulation."""
import math
from typing import Dict

def calculate_safety_stock(
    service_level_z: float = 1.645,
    forecast_std_err: float = 5.0,
    lead_time_days: int = 7,
) -> float:
    """Calculate safety stock buffer given z-score, forecast error std dev, and lead time."""
    return service_level_z * forecast_std_err * math.sqrt(lead_time_days)

def calculate_reorder_point(
    daily_demand_forecast: float,
    safety_stock: float,
    lead_time_days: int = 7,
) -> float:
    """Calculate Reorder Point (ROP) = (Lead Time Demand) + Safety Stock."""
    lead_time_demand = daily_demand_forecast * lead_time_days
    return lead_time_demand + safety_stock

def evaluate_inventory_policy(
    current_inventory: int,
    daily_demand_forecast: float,
    forecast_std_err: float = 5.0,
    lead_time_days: int = 7,
    service_level_z: float = 1.645,
) -> Dict[str, float]:
    """Assess whether current stock triggers a reorder."""
    ss = calculate_safety_stock(service_level_z, forecast_std_err, lead_time_days)
    rop = calculate_reorder_point(daily_demand_forecast, ss, lead_time_days)
    reorder_recommended = bool(current_inventory <= rop)
    order_quantity = max(0.0, rop * 1.5 - current_inventory) if reorder_recommended else 0.0
    
    return {
        "safety_stock": round(ss, 2),
        "reorder_point": round(rop, 2),
        "current_inventory": float(current_inventory),
        "reorder_recommended": float(reorder_recommended),
        "order_quantity": round(order_quantity, 2),
    }
