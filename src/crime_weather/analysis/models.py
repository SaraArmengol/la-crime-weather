"""Count regression: how is the daily number of crimes associated with weather,
after controlling for calendar effects?

Why negative binomial: daily crime counts are non-negative integers whose
variance exceeds their mean (overdispersion), which violates the Poisson
assumption. Coefficients are reported as incidence rate ratios (IRR):
an IRR of 1.08 for "90+ degrees" means 8% more crimes than on a 70-80 degree day,
holding month, weekday, year, holidays, and rain constant.

This is an association, not a causal effect.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

BASELINE_TEMP_BIN = "70-80"

FORMULA = (
    "crime_count ~ C(temp_bin, Treatment('{base}')) + rain_day + is_holiday"
    " + C(dow) + C(month) + C(year)"
)


def fit_count_model(panel: pd.DataFrame, category: str | None = None):
    import statsmodels.formula.api as smf

    data = panel.dropna(subset=["temp_bin"])  # days without weather data
    if category is not None:
        data = data[data["crime_category"] == category]
    if category is None:  # total crime per day
        data = (
            data.groupby(["date", "temp_bin", "rain_day", "is_holiday", "dow", "month", "year"],
                         observed=True)["crime_count"].sum().reset_index()
        )
    data = data.assign(
        temp_bin=data["temp_bin"].astype(str),
        rain_day=data["rain_day"].astype(int),
        is_holiday=data["is_holiday"].astype(int),
    )
    model = smf.negativebinomial(FORMULA.format(base=BASELINE_TEMP_BIN), data=data)
    return model.fit(disp=False, maxiter=200)


def tidy_weather_effects(result, category: str) -> pd.DataFrame:
    """Keep only the weather terms, as IRRs with 95% confidence intervals."""
    params, ci = result.params, result.conf_int()
    rows = []
    for term in params.index:
        if "temp_bin" in term or term.startswith("rain_day"):
            label = term.split("[T.")[-1].rstrip("]") if "[T." in term else term
            rows.append({
                "category": category,
                "term": label if "temp_bin" in term else "rain_day",
                "irr": float(np.exp(params[term])),
                "ci_low": float(np.exp(ci.loc[term, 0])),
                "ci_high": float(np.exp(ci.loc[term, 1])),
                "p_value": float(result.pvalues[term]),
            })
    return pd.DataFrame(rows)


def fit_all(panel: pd.DataFrame) -> pd.DataFrame:
    tables = [tidy_weather_effects(fit_count_model(panel), "all")]
    for cat in sorted(panel["crime_category"].unique()):
        tables.append(tidy_weather_effects(fit_count_model(panel, cat), cat))
    return pd.concat(tables, ignore_index=True)
