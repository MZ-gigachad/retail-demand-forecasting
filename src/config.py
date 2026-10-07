"""Configuration module for retail-demand-forecasting."""
from pathlib import Path
from typing import Any, Dict
import yaml

# Resolve project repository root (two levels up from this file)
ROOT: Path = Path(__file__).resolve().parents[1]

def load_config(config_path: Path = ROOT / "config.yaml") -> Dict[str, Any]:
    """Load configuration parameters from YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CFG: Dict[str, Any] = load_config()

# Standard project directory paths
RAW_DIR: Path = ROOT / CFG["paths"]["raw"]
INTERIM_DIR: Path = ROOT / CFG["paths"]["interim"]
PROCESSED_DIR: Path = ROOT / CFG["paths"]["processed"]
EXTERNAL_DIR: Path = ROOT / CFG["paths"]["external"]
MODELS_DIR: Path = ROOT / CFG["paths"]["models"]
REPORTS_DIR: Path = ROOT / CFG["paths"]["reports"]
FIGURES_DIR: Path = ROOT / CFG["paths"].get("figures", "reports/figures")

# Core project parameters
PROJECT_NAME: str = CFG["project"]["name"]
SEED: int = CFG["project"]["seed"]

# Data column definitions
DATE_COL: str = CFG["data"]["date_col"]
STORE_COL: str = CFG["data"]["store_col"]
PRODUCT_COL: str = CFG["data"]["product_col"]
TARGET_COL: str = CFG["data"]["target_col"]
FREQUENCY: str = CFG["data"]["frequency"]

# Forecast settings
DEFAULT_HORIZON: int = CFG["forecast"]["default_horizon"]
HORIZONS: list = CFG["forecast"]["horizons"]
FORECAST_STRATEGY: str = CFG["forecast"].get("strategy", "direct")
