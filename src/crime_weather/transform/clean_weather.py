"""Clean daily weather data."""

from __future__ import annotations

import pandas as pd

RENAME = {
    "temperature_2m_max": "temp_max_f",
    "temperature_2m_min": "temp_min_f",
    "precipitation_sum": "precip_mm",
    "wind_speed_10m_max": "wind_max_kmh",
}


def clean_weather(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns=RENAME).copy()
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    for col in RENAME.values():
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)
    if "precip_mm" in out.columns:
        out["precip_mm"] = out["precip_mm"].fillna(0.0)
    return out
