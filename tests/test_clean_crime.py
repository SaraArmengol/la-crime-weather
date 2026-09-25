import pandas as pd

from crime_weather.transform.clean_crime import (
    classify_crime_type,
    clean_crime,
    normalize_columns,
    quality_report,
)


def test_normalize_columns_handles_csv_names(raw_crime_csv_style):
    cols = normalize_columns(raw_crime_csv_style).columns
    assert {"dr_no", "date_occ", "time_occ", "area_name", "crm_cd_desc"} <= set(cols)


def test_duplicates_and_bad_dates_are_dropped(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style)
    assert clean["dr_no"].tolist() == ["1", "2", "3", "5"]  # "2" deduped, "4" had an invalid date


def test_hour_parsing_and_invalid_times(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style).set_index("dr_no")
    assert clean.loc["1", "hour_occ"] == 15
    assert clean.loc["2", "hour_occ"] == 0      # "5" means 00:05
    assert pd.isna(clean.loc["3", "hour_occ"])  # 2400 is not a valid HHMM


def test_zero_coordinates_become_missing(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style).set_index("dr_no")
    assert pd.isna(clean.loc["2", "lat"]) and pd.isna(clean.loc["2", "lon"])
    assert clean.loc["1", "lat"] == 34.05


def test_ucr_types_follow_fbi_definitions():
    desc = pd.Series([
        "BATTERY - SIMPLE ASSAULT",   # simple assault is not aggravated assault
        "BURGLARY FROM VEHICLE",      # UCR: larceny, not burglary
        "THEFT OF IDENTITY",          # UCR larceny excludes identity theft
        "ASSAULT WITH DEADLY WEAPON ON POLICE OFFICER",
        "TRESPASSING",
        None,
    ])
    assert classify_crime_type(desc).tolist() == [
        "Simple assault", "Larceny theft", "Fraud", "Aggravated assault", "Other", "Other",
    ]


def test_fallback_rules_do_not_overwrite_earlier_matches():
    # Matches both "ROBBERY" and "THEFT"; the earlier, more specific rule must win.
    # In the class version, later rules overwrote earlier ones.
    desc = pd.Series(["ROBBERY - THEFT FROM PERSON", "SEXUAL BATTERY"])
    assert classify_crime_type(desc).tolist() == ["Robbery", "Simple assault"]


def test_coarse_categories(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style).set_index("dr_no")
    assert clean.loc["1", "crime_category"] == "property"  # vehicle theft
    assert clean.loc["2", "crime_category"] == "violent"   # simple assault
    assert clean.loc["5", "crime_category"] == "other"     # fraud


def test_date_filter(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style, start="2022-07-02", end="2022-07-31")
    assert clean["dr_no"].tolist() == ["3", "5"]


def test_quality_report_flags_first_of_month(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style)
    report = quality_report(raw_crime_csv_style, clean)
    assert report["raw_rows"] == 6 and report["clean_rows"] == 4
    assert report["first_of_month_pct"] == 50.0  # 2 of 4 records dated July 1
