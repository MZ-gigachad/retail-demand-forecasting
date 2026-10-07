"""Smoke test: confirms every key library imports and basic operations work."""
import sys

def check(name, fn):
    try:
        fn()
        print(f"[OK]   {name}")
        return True
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return False

def pandas_numpy():
    import pandas as pd
    import numpy as np
    df = pd.DataFrame({"a": np.arange(5)})
    assert df["a"].sum() == 10

def sklearn_check():
    from sklearn.linear_model import LinearRegression
    LinearRegression().fit([[0], [1]], [0, 1])

def prophet_check():
    import pandas as pd
    from prophet import Prophet
    df = pd.DataFrame({
        "ds": pd.date_range("2024-01-01", periods=60),
        "y": range(60)
    })
    m = Prophet()
    m.fit(df)
    m.predict(m.make_future_dataframe(periods=5))

def tensorflow_check():
    import tensorflow as tf
    from tensorflow import keras
    model = keras.Sequential([
        keras.layers.Input((7, 1)),
        keras.layers.LSTM(4),
        keras.layers.Dense(1)
    ])
    model.compile(optimizer="adam", loss="mse")

def catboost_check():
    from catboost import CatBoostRegressor
    m = CatBoostRegressor(iterations=5, verbose=False)
    m.fit([[0], [1], [2], [3]], [0, 1, 2, 3])

def fastapi_streamlit():
    import fastapi
    import streamlit  # noqa: F401

def holidays_check():
    import holidays
    assert len(holidays.India(years=2024)) > 0

if __name__ == "__main__":
    print("Python", sys.version)
    results = [
        check("pandas / numpy", pandas_numpy),
        check("scikit-learn", sklearn_check),
        check("prophet", prophet_check),
        check("tensorflow / keras LSTM", tensorflow_check),
        check("catboost", catboost_check),
        check("fastapi / streamlit", fastapi_streamlit),
        check("holidays (India)", holidays_check),
    ]
    sys.exit(0 if all(results) else 1)
