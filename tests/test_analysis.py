import numpy as np
import pandas as pd
import pytest

from crime_weather.analysis.baseline import chronological_split, compare_baselines
from crime_weather.analysis.descriptive import crime_mix_vs_benchmark, weather_type_rates


def _synthetic_panel(n_days: int = 400, seed: int = 0) -> pd.DataFrame:
    """Two categories per day; more warm days than rainy days, but rainy days have fewer crimes."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-02", periods=n_days, freq="D")
    weather_type = np.where(rng.random(n_days) < 0.8, "Warm", "Rainy")
    rows = []
    for d, wt in zip(dates, weather_type, strict=True):
        base = 300 if wt == "Warm" else 240
        day = {  # day-level values are shared by both category rows, as in the real panel
            "date": d, "weather_type": wt, "is_first_of_month": d.day == 1,
            "temp_mean_f": 70 + rng.normal(0, 5), "apparent_temp_mean_f": 70 + rng.normal(0, 5),
            "precip_mm": 5.0 if wt == "Rainy" else 0.0, "cloud_cover_pct": rng.uniform(0, 100),
            "wind_mean_kmh": rng.uniform(5, 20), "dow": d.day_name()[:3], "month": d.month,
        }
        for cat in ("violent", "property"):
            rows.append({**day, "crime_category": cat, "crime_count": int(base + rng.normal(0, 10))})
    return pd.DataFrame(rows)


def test_weather_type_rates_separate_frequency_from_intensity():
    rates = weather_type_rates(_synthetic_panel()).set_index("weather_type")
    # Warm days hold most crimes only because most days are warm...
    assert rates.loc["Warm", "share_of_crimes_pct"] > 75
    # ...but per day, rainy days have clearly fewer crimes
    assert rates.loc["Rainy", "avg_daily_crimes"] < rates.loc["Warm", "avg_daily_crimes"] * 0.85
    assert rates["n_days"].sum() == 400 - 13  # one row per day; the 13 first-of-month days excluded


def test_chronological_split_never_trains_on_the_future():
    df = pd.DataFrame({"date": pd.date_range("2022-01-01", periods=10, freq="D")[::-1]})
    train, test = chronological_split(df, test_share=0.3)
    assert train["date"].max() < test["date"].min()
    assert len(test) == 3


def test_compare_baselines_detects_rain_signal():
    out = compare_baselines(_synthetic_panel()).set_index("model")
    assert out.loc["Weather only", "r2"] > 0.5  # precipitation drives the synthetic data
    assert {"r2", "mae", "test_period"} <= set(out.columns)


def test_crime_mix_only_compares_ucr_types():
    crime = pd.DataFrame({"crime_type": ["Robbery"] * 2 + ["Larceny theft"] * 6 + ["Fraud"] * 50})
    benchmark = pd.DataFrame({"crime_type": ["Robbery", "Larceny theft"], "benchmark_share_pct": [20.0, 80.0]})
    mix = crime_mix_vs_benchmark(crime, benchmark).set_index("crime_type")
    assert "Fraud" not in mix.index
    assert mix.loc["Larceny theft", "la_share_pct"] == pytest.approx(75.0)
