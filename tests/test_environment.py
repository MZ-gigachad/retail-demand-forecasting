"""Unit test verifying core package imports and environment integrity."""

def test_core_imports():
    import pandas  # noqa: F401
    import numpy  # noqa: F401
    import sklearn  # noqa: F401
    import yaml  # noqa: F401

def test_config_import():
    from src.config import ROOT, RAW_DIR, PROCESSED_DIR, SEED, DATE_COL, TARGET_COL
    assert ROOT.exists()
    assert RAW_DIR.exists()
    assert PROCESSED_DIR.exists()
    assert SEED == 42
    assert DATE_COL == "Date"
    assert TARGET_COL == "Units_Sold"

def test_utils_import():
    from src.utils import set_seed, get_logger
    set_seed(42)
    logger = get_logger("test")
    assert logger is not None
