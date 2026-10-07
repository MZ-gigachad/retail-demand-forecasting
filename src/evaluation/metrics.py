"""Forecast evaluation metrics: MAE, RMSE, MAPE, WMAPE, and Bias."""
from typing import Dict
import numpy as np

def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute MAE."""
    return float(np.mean(np.abs(y_true - y_pred)))

def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute RMSE."""
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

def mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray, epsilon: float = 1e-5) -> float:
    """Compute MAPE in percentage, avoiding divide-by-zero using epsilon."""
    denom = np.where(y_true == 0, epsilon, y_true)
    return float(np.mean(np.abs((y_true - y_pred) / denom)) * 100)

def weighted_mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute WMAPE (sum of absolute errors divided by total actual demand)."""
    total_actual = np.sum(y_true)
    if total_actual == 0:
        return 0.0
    return float((np.sum(np.abs(y_true - y_pred)) / total_actual) * 100)

def forecast_bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Mean Forecast Bias (positive means over-forecasting)."""
    return float(np.mean(y_pred - y_true))

def evaluate_forecasts(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute full evaluation metric dictionary."""
    yt = np.asarray(y_true)
    yp = np.asarray(y_pred)
    return {
        "MAE": mean_absolute_error(yt, yp),
        "RMSE": root_mean_squared_error(yt, yp),
        "MAPE": mean_absolute_percentage_error(yt, yp),
        "WMAPE": weighted_mean_absolute_percentage_error(yt, yp),
        "Bias": forecast_bias(yt, yp),
    }
