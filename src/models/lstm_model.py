"""LSTM deep learning model wrapper for sequential pattern forecasting."""
from typing import Tuple, Optional
import numpy as np
from src.utils import get_logger

logger = get_logger(__name__)

class LSTMForecaster:
    """Sequential LSTM forecaster implemented in Keras/TensorFlow."""

    def __init__(self, lookback_window: int = 30, n_features: int = 1, units: int = 64):
        self.lookback_window = lookback_window
        self.n_features = n_features
        self.units = units
        self.model = None

    def build_model(self) -> None:
        """Construct the compiled sequential architecture."""
        from tensorflow import keras
        self.model = keras.Sequential([
            keras.layers.Input((self.lookback_window, self.n_features)),
            keras.layers.LSTM(self.units, return_sequences=False),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dense(1)
        ])
        self.model.compile(optimizer="adam", loss="mse", metrics=["mae"])

    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 20, batch_size: int = 32) -> Any:
        """Fit model weights on windowed sequences."""
        if self.model is None:
            self.build_model()
        return self.model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate forecasts from input sequences."""
        if self.model is None:
            raise RuntimeError("Model must be trained or loaded before prediction.")
        return self.model.predict(X, verbose=0)
