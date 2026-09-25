"""Baseline from the class version: can weather alone predict daily crime counts?

Two corrections to the original:
  1. Chronological split. The class version split days randomly (train_test_split),
     so the model trained on days *after* the ones it was tested on. With time series,
     the honest test is to train on the past and predict the future.
  2. A second model adds calendar features (weekday, month) with the same split.
     Comparing the two R-squared values shows how much of daily crime is explained
     by the calendar rather than the weather.
"""

from __future__ import annotations

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

from crime_weather.analysis.descriptive import daily_totals

WEATHER_FEATURES = ["temp_mean_f", "apparent_temp_mean_f", "precip_mm", "cloud_cover_pct", "wind_mean_kmh"]


def chronological_split(df: pd.DataFrame, test_share: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("date")
    cut = int(len(df) * (1 - test_share))
    return df.iloc[:cut], df.iloc[cut:]


def _fit_score(train: pd.DataFrame, test: pd.DataFrame, features: list[str]) -> dict[str, float]:
    model = LinearRegression().fit(train[features], train["crime_count"])
    pred = model.predict(test[features])
    return {"r2": r2_score(test["crime_count"], pred), "mae": mean_absolute_error(test["crime_count"], pred)}


def compare_baselines(panel: pd.DataFrame, test_share: float = 0.2) -> pd.DataFrame:
    days = daily_totals(panel)
    days = days[~days["is_first_of_month"]].dropna(subset=WEATHER_FEATURES)
    calendar = pd.get_dummies(days[["dow"]].astype(str).join(days["month"].astype(str)),
                              drop_first=True, dtype=float)
    days = pd.concat([days.reset_index(drop=True), calendar.reset_index(drop=True)], axis=1)
    train, test = chronological_split(days, test_share)

    rows = [
        {"model": "Weather only", **_fit_score(train, test, WEATHER_FEATURES)},
        {"model": "Weather + weekday + month", **_fit_score(train, test, WEATHER_FEATURES + list(calendar.columns))},
    ]
    out = pd.DataFrame(rows)
    out["test_period"] = f"{test['date'].min():%Y-%m-%d} to {test['date'].max():%Y-%m-%d}"
    return out.round(3)
