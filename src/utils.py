"""Utility helpers: seed management, logging, and general helpers."""
import logging
import os
import random
import sys
from typing import Optional
import numpy as np

def set_seed(seed: int = 42) -> None:
    """Set random seed across Python, NumPy, and TensorFlow for reproducibility."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
    except ImportError:
        pass

def get_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger with standard stream formatting."""
    logger = logging.getLogger(name or "retail-demand-forecasting")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
