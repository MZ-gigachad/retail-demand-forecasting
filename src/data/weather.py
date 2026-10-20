"""Weather data acquisition and seasonal fallback module for Indian retail cities."""
import logging
from pathlib import Path
import time
from typing import Union
import numpy as np
import pandas as pd
import requests
from src.config import CFG, EXTERNAL_DIR

logger = logging.getLogger(__name__)

URL = "https://archive-api.open-meteo.com/v1/archive"
CACHE: Path = EXTERNAL_DIR / "weather"


def fallback_weather(
    city_seed: int,
    start: Union[str, pd.Timestamp],
    end: Union[str, pd.Timestamp],
    mean_temp: float = 27.0,
    amp: float = 6.0,
) -> pd.DataFrame:
    """Generate seasonal synthetic temperature and rainfall if API is unavailable."""
    rng = np.random.default_rng(city_seed)
    dates = pd.date_range(start, end)
    doy = dates.dayofyear.values
    temp = (
        mean_temp
        + amp * np.sin(2 * np.pi * (doy - 100) / 365)
        + rng.normal(0, 1.2, len(dates))
    )
    rain = np.clip(
        rng.gamma(0.4, 6, len(dates))
        * (np.sin(2 * np.pi * (doy - 150) / 365) > 0.3),
        0,
        None,
    )
    return pd.DataFrame(
        {
            "Date": dates,
            "Temperature": temp.round(1),
            "Rainfall_mm": rain.round(1),
        }
    )


def fetch_city_weather(
    city: str,
    lat: float,
    lon: float,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Fetch daily weather telemetry from Open-Meteo API with local disk caching."""
    CACHE.mkdir(parents=True, exist_ok=True)
    clean_city = city.lower().replace(" ", "_")
    path = CACHE / f"{clean_city}_{start}_{end}.csv"
    if path.exists():
        logger.info("Loading cached weather for %s from %s", city, path)
        return pd.read_csv(path, parse_dates=["Date"])

    weather_cfg = CFG.get("adaptation", {}).get("weather", {})
    if not weather_cfg.get("enabled", True):
        logger.info("Weather disabled in config. Using fallback for %s.", city)
        city_seed = abs(hash(city)) % (2**31)
        df = fallback_weather(city_seed, start, end)
        df.to_csv(path, index=False)
        return df

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "Asia/Kolkata",
    }
    try:
        logger.info("Requesting Open-Meteo weather for %s (%.4f, %.4f)...", city, lat, lon)
        r = requests.get(URL, params=params, timeout=60)
        r.raise_for_status()
        d = r.json()["daily"]
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(d["time"]),
                "Temperature": d["temperature_2m_mean"],
                "Rainfall_mm": d["precipitation_sum"],
            }
        )
        df.to_csv(path, index=False)
        time.sleep(1.5)  # Be polite to the free API
        return df
    except Exception as exc:
        logger.warning("Open-Meteo API request failed for %s: %s", city, exc)
        if weather_cfg.get("use_fallback_if_api_fails", True):
            logger.info("Falling back to seasonal weather model for %s", city)
            city_seed = abs(hash(city)) % (2**31)
            df = fallback_weather(city_seed, start, end)
            df.to_csv(path, index=False)
            return df
        raise


def build_weather_table(
    store_master: pd.DataFrame, start: str, end: str
) -> pd.DataFrame:
    """Fetch or load weather for all unique store cities."""
    cities = (
        store_master[["City", "Latitude", "Longitude"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    records = []
    for _, row in cities.iterrows():
        city_df = fetch_city_weather(
            row["City"], float(row["Latitude"]), float(row["Longitude"]), start, end
        )
        city_df["City"] = row["City"]
        records.append(city_df)

    weather_df = pd.concat(records, ignore_index=True)
    logger.info(
        "Built weather table with %d rows across %d cities.",
        len(weather_df),
        len(cities),
    )
    return weather_df
