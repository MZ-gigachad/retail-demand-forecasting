"""CatBoost gradient boosted decision tree model wrapper."""
from typing import Any, Dict, List, Optional
import pandas as pd
from src.utils import get_logger

logger = get_logger(__name__)

class CatBoostForecaster:
    """Tabular demand forecaster utilizing CatBoost Regressor."""

    def __init__(self, cat_features: Optional[List[str]] = None, params: Optional[Dict[str, Any]] = None):
        self.cat_features = cat_features or []
        self.params = params or {"iterations": 500, "learning_rate": 0.05, "depth": 6, "verbose": False}
        self.model = None

    def fit(self, X: pd.DataFrame, y: pd.Series, eval_set: Optional[tuple] = None) -> "CatBoostForecaster":
        """Fit CatBoost regressor with optional validation evaluation set."""
        from catboost import CatBoostRegressor
        self.model = CatBoostRegressor(cat_features=self.cat_features, **self.params)
        self.model.fit(X, y, eval_set=eval_set, verbose=False)
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Predict continuous demand units."""
        if self.model is None:
            raise RuntimeError("Model must be fitted before predict.")
        preds = self.model.predict(X)
        return pd.Series(preds, index=X.index).clip(lower=0)
