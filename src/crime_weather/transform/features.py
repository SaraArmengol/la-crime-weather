"""Build the daily analysis panel: crime counts per day and category, joined to weather.

Calendar features matter because weather is confounded with season and weekday:
summer is both hot and busy. The model controls for these instead of reading
raw correlations.
"""

from __future__ import annotations

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar


def daily_counts(crime: pd.DataFrame, by_category: bool = True) -> pd.DataFrame:
    """Counts per (date, category), including zero-count days."""
    keys = ["date_occ", "crime_category"] if by_category else ["date_occ"]
    counts = crime.groupby(keys).size().rename("crime_count").reset_index()
    counts = counts.rename(columns={"date_occ": "date"})

    all_days = pd.date_range(counts["date"].min(), counts["date"].max(), freq="D")
    if by_category:
        cats = sorted(crime["crime_category"].dropna().unique())
        grid = pd.MultiIndex.from_product([all_days, cats], names=["date", "crime_category"])
        counts = counts.set_index(["date", "crime_category"]).reindex(grid, fill_value=0)
    else:
        counts = counts.set_index("date").reindex(pd.Index(all_days, name="date"), fill_value=0)
    return counts.reset_index()


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    d = out["date"]
    out["year"] = d.dt.year
    out["month"] = d.dt.month
    out["dow"] = d.dt.day_name().str[:3]
    out["is_weekend"] = d.dt.dayofweek >= 5
    holidays = USFederalHolidayCalendar().holidays(start=d.min(), end=d.max())
    out["is_holiday"] = d.isin(holidays)
    # Data artifact: crimes with an unknown occurrence date are often recorded on the 1st
    # of the month (and January 1st). Flagging these days keeps them from biasing the model.
    out["is_first_of_month"] = d.dt.day == 1
    out["is_jan_1"] = (d.dt.month == 1) & (d.dt.day == 1)
    return out


def add_weather_features(
    df: pd.DataFrame,
    temp_bins: list[float],
    temp_labels: list[str],
    rain_threshold_mm: float,
) -> pd.DataFrame:
    out = df.copy()
    out["temp_bin"] = pd.cut(out["temp_max_f"], bins=temp_bins, labels=temp_labels, right=False)
    out["rain_day"] = out["precip_mm"] >= rain_threshold_mm
    return out


def build_daily_panel(crime: pd.DataFrame, weather: pd.DataFrame, feature_cfg: dict) -> pd.DataFrame:
    counts = daily_counts(crime, by_category=True)
    panel = counts.merge(weather, on="date", how="inner", validate="many_to_one")
    panel = add_calendar_features(panel)
    panel = add_weather_features(
        panel,
        temp_bins=feature_cfg["temp_bins_f"],
        temp_labels=feature_cfg["temp_labels"],
        rain_threshold_mm=feature_cfg["weather_type"]["rain_threshold_mm"],
    )
    return panel.sort_values(["date", "crime_category"]).reset_index(drop=True)


def hotspot_grid(crime: pd.DataFrame, precision: int = 2) -> pd.DataFrame:
    """Aggregate points to a ~1 km grid so the dashboard ships a small file, not 1M points."""
    pts = crime.dropna(subset=["lat", "lon"])
    grid = pts.assign(lat=pts["lat"].round(precision), lon=pts["lon"].round(precision))
    return grid.groupby(["lat", "lon", "crime_category"]).size().rename("crime_count").reset_index()
