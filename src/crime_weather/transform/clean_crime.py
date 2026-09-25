"""Clean raw LAPD records into an analysis-ready table.

Works on both sources: the CSV download ("DATE OCC", "Crm Cd Desc") and the
Socrata API (date_occ, crm_cd_desc), because column names are normalized first.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

KEEP_COLUMNS = [
    "dr_no", "date_occ", "hour_occ", "area", "area_name",
    "crm_cd", "crm_cd_desc", "crime_category", "lat", "lon",
]

# Ordered: the first matching rule wins ("BURGLARY FROM VEHICLE" -> vehicle, not property).
# This is a starting point. Review the distinct crm_cd_desc values and refine.
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("vehicle", ("VEHICLE - STOLEN", "FROM MOTOR VEHICLE", "BURGLARY FROM VEHICLE")),
    ("violent", ("ASSAULT", "BATTERY", "ROBBERY", "HOMICIDE", "RAPE", "KIDNAPPING",
                 "INTIMATE PARTNER", "SHOTS FIRED", "BRANDISH")),
    ("property", ("BURGLARY", "THEFT", "SHOPLIFTING", "VANDALISM", "ARSON",
                  "EMBEZZLEMENT", "STOLEN")),
]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """'DATE OCC' / 'Crm Cd Desc' -> 'date_occ' / 'crm_cd_desc'."""
    out = df.copy()
    out.columns = [re.sub(r"[^0-9a-z]+", "_", c.strip().lower()).strip("_") for c in out.columns]
    return out


def categorize(desc: pd.Series) -> pd.Series:
    desc = desc.fillna("").str.upper()
    result = pd.Series("other", index=desc.index, dtype="object")
    assigned = pd.Series(False, index=desc.index)
    for category, keywords in CATEGORY_RULES:
        pattern = "|".join(re.escape(k) for k in keywords)
        hit = desc.str.contains(pattern, regex=True) & ~assigned
        result[hit] = category
        assigned |= hit
    return result


def clean_crime(raw: pd.DataFrame, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    df = normalize_columns(raw)

    required = {"dr_no", "date_occ", "time_occ", "crm_cd_desc"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing expected columns: {sorted(missing)}")

    # Duplicates: one row per report number
    df = df.drop_duplicates(subset="dr_no", keep="first")

    # Dates: CSV uses '03/01/2020 12:00:00 AM', API uses ISO strings
    df["date_occ"] = pd.to_datetime(df["date_occ"], format="mixed", errors="coerce").dt.normalize()
    df = df.dropna(subset=["date_occ"])

    # TIME OCC is HHMM as an integer (5 means 00:05, 1530 means 15:30)
    time_occ = pd.to_numeric(df["time_occ"], errors="coerce")
    hour = (time_occ // 100).where(time_occ.between(0, 2359))
    df["hour_occ"] = hour.astype("Int64")

    # Coordinates: LAPD encodes unknown locations as (0, 0)
    for col in ("lat", "lon"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").replace(0, np.nan)
        else:
            df[col] = np.nan

    df["crime_category"] = categorize(df["crm_cd_desc"])

    if start:
        df = df[df["date_occ"] >= pd.Timestamp(start)]
    if end:
        df = df[df["date_occ"] <= pd.Timestamp(end)]

    for col in KEEP_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[KEEP_COLUMNS].reset_index(drop=True)


def quality_report(raw: pd.DataFrame, clean: pd.DataFrame) -> dict[str, float]:
    """Numbers worth stating in the README's data section."""
    return {
        "raw_rows": len(raw),
        "clean_rows": len(clean),
        "rows_dropped_pct": round(100 * (1 - len(clean) / max(len(raw), 1)), 2),
        "missing_coords_pct": round(100 * clean["lat"].isna().mean(), 2),
        "missing_hour_pct": round(100 * clean["hour_occ"].isna().mean(), 2),
        "other_category_pct": round(100 * (clean["crime_category"] == "other").mean(), 2),
    }
