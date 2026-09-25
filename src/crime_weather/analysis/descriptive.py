"""Descriptive comparisons shown in the dashboard.

`weather_type_rates` fixes the main flaw in the class version's pie chart: the share
of all crimes that happened on "Warm" days mostly reflects how many days were warm.
Comparing crimes *per day* for each weather type removes that effect.
"""

from __future__ import annotations

import pandas as pd

from crime_weather.extract.scrape_stats import UCR_TYPES


def daily_totals(panel: pd.DataFrame) -> pd.DataFrame:
    """Collapse the (date x category) panel to one row per day."""
    day_cols = [c for c in panel.columns if c not in ("crime_category", "crime_count")]
    return panel.groupby(day_cols, observed=True, dropna=False)["crime_count"].sum().reset_index()


def weather_type_rates(panel: pd.DataFrame, exclude_artifact_days: bool = True) -> pd.DataFrame:
    days = daily_totals(panel)
    if exclude_artifact_days:
        days = days[~days["is_first_of_month"]]
    overall = days["crime_count"].mean()
    out = (
        days.groupby("weather_type")
        .agg(n_days=("crime_count", "size"), total_crimes=("crime_count", "sum"),
             avg_daily_crimes=("crime_count", "mean"))
        .reset_index()
    )
    out["share_of_days_pct"] = 100 * out["n_days"] / out["n_days"].sum()
    out["share_of_crimes_pct"] = 100 * out["total_crimes"] / out["total_crimes"].sum()
    out["vs_average_pct"] = 100 * (out["avg_daily_crimes"] / overall - 1)
    return out.sort_values("avg_daily_crimes", ascending=False).round(2).reset_index(drop=True)


def crime_mix_vs_benchmark(crime: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
    """LA's mix of UCR Part I crime types vs. other large California cities.

    Only UCR types are compared; simple assault, fraud, vandalism and "Other" are
    excluded because the benchmark table doesn't report them.
    """
    la = crime[crime["crime_type"].isin(UCR_TYPES)]["crime_type"].value_counts()
    la_share = (100 * la / la.sum()).rename("la_share_pct").reset_index()
    la_share.columns = ["crime_type", "la_share_pct"]
    merged = la_share.merge(benchmark[["crime_type", "benchmark_share_pct"]], on="crime_type", how="outer")
    return merged.fillna(0).sort_values("la_share_pct", ascending=False).round(2).reset_index(drop=True)
