"""Clean raw LAPD records into an analysis-ready table.

Works on both sources: the CSV download ("DATE OCC", "Crm Cd Desc") and the
Socrata API (date_occ, crm_cd_desc), because column names are normalized first.

Crime types follow the FBI Uniform Crime Reporting (UCR) categories, so LA can be
compared with the UCR city table scraped from Wikipedia. The mapping began in the
CS 2316 version of this project; see docs/FROM_CLASS_PROJECT.md for what changed.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

KEEP_COLUMNS = [
    "dr_no", "date_occ", "hour_occ", "area", "area_name",
    "crm_cd", "crm_cd_desc", "crime_type", "crime_category", "lat", "lon",
]

# Exact descriptions -> UCR crime type.
CRIME_MAPPING: dict[str, str] = {
    "VEHICLE - STOLEN": "Motor vehicle theft",
    "VEHICLE - ATTEMPT STOLEN": "Motor vehicle theft",
    "VEHICLE, STOLEN - OTHER (MOTORIZED SCOOTERS, BIKES, ETC)": "Motor vehicle theft",
    "BURGLARY": "Burglary",
    "BURGLARY, ATTEMPTED": "Burglary",
    "BURGLARY FROM VEHICLE": "Larceny theft",  # UCR counts theft from vehicles as larceny
    "ROBBERY": "Robbery",
    "ATTEMPTED ROBBERY": "Robbery",
    "ASSAULT WITH DEADLY WEAPON, AGGRAVATED ASSAULT": "Aggravated assault",
    "INTIMATE PARTNER - AGGRAVATED ASSAULT": "Aggravated assault",
    "BATTERY - SIMPLE ASSAULT": "Simple assault",  # not a UCR Part I crime
    "INTIMATE PARTNER - SIMPLE ASSAULT": "Simple assault",
    "OTHER ASSAULT": "Simple assault",
    "THEFT PLAIN - PETTY ($950 & UNDER)": "Larceny theft",
    "SHOPLIFTING - PETTY THEFT ($950 & UNDER)": "Larceny theft",
    "THEFT FROM MOTOR VEHICLE - PETTY ($950 & UNDER)": "Larceny theft",
    "THEFT FROM MOTOR VEHICLE - GRAND ($950.01 AND OVER)": "Larceny theft",
    "BIKE - STOLEN": "Larceny theft",
    "SHOPLIFTING - ATTEMPT": "Larceny theft",
    "THEFT OF IDENTITY": "Fraud",   # UCR larceny excludes fraud and identity theft
    "BUNCO, GRAND THEFT": "Fraud",  # bunco = confidence scam
    "VANDALISM - FELONY ($400 & OVER, ALL CHURCH VANDALISMS)": "Vandalism",
    "VANDALISM - MISDEAMEANOR ($399 OR UNDER)": "Vandalism",
    "RAPE, FORCIBLE": "Rape",
    "ARSON": "Arson",
    "CRIMINAL HOMICIDE": "Homicide",
}

# Fallback rules for descriptions not in the dictionary. ORDERED: the first
# matching rule wins, so specific rules must come before general ones.
FALLBACK_RULES: list[tuple[str, str]] = [
    ("HOMICIDE|MURDER|MANSLAUGHTER", "Homicide"),
    ("RAPE", "Rape"),
    ("ROBBERY", "Robbery"),
    ("VEHICLE - STOLEN|VEHICLE - ATTEMPT STOLEN", "Motor vehicle theft"),
    ("AGGRAVATED|DEADLY WEAPON", "Aggravated assault"),
    ("ASSAULT|BATTERY", "Simple assault"),
    ("IDENTITY|BUNCO|EMBEZZLEMENT|FORGERY|CREDIT CARDS|DOCUMENT WORTHLESS", "Fraud"),
    ("BURGLARY", "Burglary"),
    ("THEFT|SHOPLIFTING|PICKPOCKET|PURSE SNATCHING|BIKE - STOLEN", "Larceny theft"),
    ("VANDALISM", "Vandalism"),
    ("ARSON", "Arson"),
]

# Coarse groups used by the model and the dashboard filter
CATEGORY_OF_TYPE = {
    "Homicide": "violent", "Rape": "violent", "Robbery": "violent",
    "Aggravated assault": "violent", "Simple assault": "violent",
    "Burglary": "property", "Larceny theft": "property", "Motor vehicle theft": "property",
    "Vandalism": "property", "Arson": "property",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """'DATE OCC' / 'Crm Cd Desc' -> 'date_occ' / 'crm_cd_desc'."""
    out = df.copy()
    out.columns = [re.sub(r"[^0-9a-z]+", "_", c.strip().lower()).strip("_") for c in out.columns]
    return out


def classify_crime_type(desc: pd.Series) -> pd.Series:
    desc = desc.fillna("").str.upper().str.strip()
    result = desc.map(CRIME_MAPPING)
    for pattern, crime_type in FALLBACK_RULES:
        unassigned = result.isna()  # recomputed every rule, so earlier matches are never overwritten
        result[unassigned & desc.str.contains(pattern, regex=True)] = crime_type
    return result.fillna("Other")


def clean_crime(raw: pd.DataFrame, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    df = normalize_columns(raw)

    required = {"dr_no", "date_occ", "time_occ", "crm_cd_desc"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing expected columns: {sorted(missing)}")

    # Duplicates: one row per report number (full-row drop_duplicates misses re-entered reports)
    df = df.drop_duplicates(subset="dr_no", keep="first")

    # Dates: CSV uses '03/01/2020 12:00:00 AM', API uses ISO strings
    df["date_occ"] = pd.to_datetime(df["date_occ"], format="mixed", errors="coerce").dt.normalize()
    df = df.dropna(subset=["date_occ"])

    # TIME OCC is HHMM as an integer (5 means 00:05, 1530 means 15:30)
    time_occ = pd.to_numeric(df["time_occ"], errors="coerce")
    df["hour_occ"] = (time_occ // 100).where(time_occ.between(0, 2359)).astype("Int64")

    # Coordinates: LAPD encodes unknown locations as (0, 0)
    for col in ("lat", "lon"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").replace(0, np.nan)
        else:
            df[col] = np.nan

    df["crime_type"] = classify_crime_type(df["crm_cd_desc"])
    df["crime_category"] = df["crime_type"].map(CATEGORY_OF_TYPE).fillna("other")

    if start:
        df = df[df["date_occ"] >= pd.Timestamp(start)]
    if end:
        df = df[df["date_occ"] <= pd.Timestamp(end)]

    for col in KEEP_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[KEEP_COLUMNS].sort_values("date_occ").reset_index(drop=True)


def quality_report(raw: pd.DataFrame, clean: pd.DataFrame) -> dict[str, float]:
    """Numbers worth stating in the README's data section."""
    day = clean["date_occ"].dt.day
    first_of_month_share = (day == 1).mean()
    return {
        "raw_rows": len(raw),
        "clean_rows": len(clean),
        "rows_dropped_pct": round(100 * (1 - len(clean) / max(len(raw), 1)), 2),
        "missing_coords_pct": round(100 * clean["lat"].isna().mean(), 2),
        "missing_hour_pct": round(100 * clean["hour_occ"].isna().mean(), 2),
        "other_type_pct": round(100 * (clean["crime_type"] == "Other").mean(), 2),
        # ~3.3% expected if dates were uniform; much higher = default dates for unknown occurrence dates
        "first_of_month_pct": round(100 * first_of_month_share, 2),
        "fraud_on_first_of_month_pct": round(
            100 * (day[clean["crime_type"] == "Fraud"] == 1).mean(), 2
        ) if (clean["crime_type"] == "Fraud").any() else 0.0,
    }
