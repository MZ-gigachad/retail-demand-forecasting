"""Prophet model wrapper for additive baseline forecasting."""
from typing import Any, Dict, Optional
import pandas as pd
from src.utils import get_logger

logger = get_logger(__name__)

class ProphetForecaster:
    """Wrapper around Facebook Prophet for individual SKU/Store or category forecasting."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model = None

    def fit(self, df: pd.DataFrame) -> "ProphetForecaster":
        """Fit Prophet model on dataframe with 'ds' and 'y' columns."""
        from prophet import Prophet
        self.model = Prophet(
            yearly_seasonality=self.config.get("yearly_seasonality", True),
            weekly_seasonality=self.config.get("weekly_seasonality", True),
            daily_seasonality=self.config.get("daily_seasonality", False),
        )
        self.model.fit(df)
        return self

    def predict(self, periods: int = 30) -> pd.DataFrame:
        """Forecast forward horizons."""
        if not self.model:
            raise RuntimeError("Model must be fitted before predict.")
        future = self.model.make_future_dataframe(periods=periods)
        forecast = self.model.predict(future)
        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]
