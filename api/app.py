"""FastAPI application for retail demand forecasting inference."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(
    title="Retail Demand Forecasting API",
    description="Inference endpoints for SKU demand forecasting and inventory replenishment.",
    version="0.1.0",
)

class ForecastRequest(BaseModel):
    store_id: str = Field(..., example="STORE_001")
    product_id: str = Field(..., example="PROD_0042")
    horizon_days: int = Field(30, ge=1, le=90)
    current_inventory: Optional[int] = Field(50, ge=0)

class ForecastResponse(BaseModel):
    store_id: str
    product_id: str
    horizon_days: int
    forecast_mean_daily: float
    reorder_point: float
    safety_stock: float
    reorder_recommended: bool

@app.get("/health")
def health_check():
    """Service health probe."""
    return {"status": "healthy", "service": "retail-demand-forecasting"}

@app.post("/forecast", response_model=ForecastResponse)
def get_forecast(req: ForecastRequest):
    """Generate forecast and inventory recommendations."""
    # Placeholder inference logic (completed in Week 2-3)
    forecast_mean = 18.5
    lead_time = 7
    safety_stock = 1.645 * 4.2 * (lead_time ** 0.5)
    rop = (forecast_mean * lead_time) + safety_stock
    current_inv = req.current_inventory if req.current_inventory is not None else 50
    
    return ForecastResponse(
        store_id=req.store_id,
        product_id=req.product_id,
        horizon_days=req.horizon_days,
        forecast_mean_daily=round(forecast_mean, 2),
        reorder_point=round(rop, 2),
        safety_stock=round(safety_stock, 2),
        reorder_recommended=(current_inv <= rop),
    )
