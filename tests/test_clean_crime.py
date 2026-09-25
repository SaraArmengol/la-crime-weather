import pandas as pd

from crime_weather.transform.clean_crime import (
    categorize,
    clean_crime,
    normalize_columns,
    quality_report,
)


def test_normalize_columns_handles_csv_names(raw_crime_csv_style):
    cols = normalize_columns(raw_crime_csv_style).columns
    assert {"dr_no", "date_occ", "time_occ", "area_name", "crm_cd_desc"} <= set(cols)


def test_duplicates_and_bad_dates_are_dropped(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style)
    assert clean["dr_no"].tolist() == ["1", "2", "3"]  # "2" deduped, "4" had an invalid date


def test_hour_parsing_and_invalid_times(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style).set_index("dr_no")
    assert clean.loc["1", "hour_occ"] == 15
    assert clean.loc["2", "hour_occ"] == 0      # "5" means 00:05
    assert pd.isna(clean.loc["3", "hour_occ"])  # 2400 is not a valid HHMM


def test_zero_coordinates_become_missing(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style).set_index("dr_no")
    assert pd.isna(clean.loc["2", "lat"]) and pd.isna(clean.loc["2", "lon"])
    assert clean.loc["1", "lat"] == 34.05


def test_category_rules_are_ordered():
    desc = pd.Series(["BURGLARY FROM VEHICLE", "BURGLARY", "ROBBERY", "TRESPASSING", None])
    assert categorize(desc).tolist() == ["vehicle", "property", "violent", "other", "other"]


def test_date_filter(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style, start="2022-07-02", end="2022-07-31")
    assert clean["dr_no"].tolist() == ["3"]


def test_quality_report(raw_crime_csv_style):
    clean = clean_crime(raw_crime_csv_style)
    report = quality_report(raw_crime_csv_style, clean)
    assert report["raw_rows"] == 5 and report["clean_rows"] == 3
