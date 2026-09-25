"""Aggregate hourly weather into daily rows and label each day with a weather type."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Hourly column -> (daily column, aggregation)
DAILY_AGGREGATIONS = {
    "temp_mean_f": ("temperature_2m", "mean"),
    "temp_max_f": ("temperature_2m", "max"),
    "apparent_temp_mean_f": ("apparent_temperature", "mean"),
    "precip_mm": ("precipitation", "sum"),
    "rain_mm": ("rain", "sum"),
    "snowfall_cm": ("snowfall", "sum"),  # Open-Meteo reports snowfall in cm
    "cloud_cover_pct": ("cloud_cover", "mean"),
    "wind_mean_kmh": ("wind_speed_10m", "mean"),
}

SUM_COLUMNS = {"precipitation", "rain", "snowfall"}


def aggregate_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    df = hourly.copy()
    for col in df.columns.drop("time"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if col in SUM_COLUMNS:
            df[col] = df[col].fillna(0.0)  # missing precipitation hour = no precipitation
    df["date"] = df["time"].dt.normalize()

    available = {k: v for k, v in DAILY_AGGREGATIONS.items() if v[0] in df.columns}
    daily = df.groupby("date").agg(**available).reset_index()
    return daily.round({col: 2 for col in available})


def classify_weather_type(daily: pd.DataFrame, cfg: dict) -> pd.Series:
    """One label per day. Order matters: precipitation and clouds override temperature.

    Thresholds are in config/settings.yaml (converted from the class version's Celsius cutoffs).
    """
    t = daily["temp_mean_f"]
    conditions = [
        daily.get("snowfall_cm", pd.Series(0, index=daily.index)) >= cfg["snow_threshold_cm"],
        daily["precip_mm"] >= cfg["rain_threshold_mm"],
        daily.get("cloud_cover_pct", pd.Series(0, index=daily.index)) >= cfg["cloudy_threshold_pct"],
        t >= cfg["hot_min_f"],
        t >= cfg["warm_min_f"],
        t >= cfg["cool_min_f"],
    ]
    labels = ["Snow", "Rainy", "Cloudy", "Hot", "Warm", "Cool"]
    return pd.Series(np.select(conditions, labels, default="Cold"), index=daily.index)


def clean_weather(hourly: pd.DataFrame, weather_type_cfg: dict) -> pd.DataFrame:
    daily = aggregate_daily(hourly)
    daily["weather_type"] = classify_weather_type(daily, weather_type_cfg)
    return daily.sort_values("date").reset_index(drop=True)
