import pandas as pd
from conftest import FEATURE_CFG, WEATHER_TYPE_CFG

from crime_weather.extract.weather import parse_hourly
from crime_weather.transform.clean_crime import clean_crime
from crime_weather.transform.clean_weather import clean_weather
from crime_weather.transform.features import build_daily_panel, daily_counts, hotspot_grid


def _panel(raw_crime, weather_payload):
    crime = clean_crime(raw_crime)
    wx = clean_weather(parse_hourly(weather_payload), WEATHER_TYPE_CFG)
    return crime, build_daily_panel(crime, wx, FEATURE_CFG)


def test_daily_counts_fill_zero_days():
    crime = pd.DataFrame({
        "date_occ": pd.to_datetime(["2022-07-01", "2022-07-03"]),
        "crime_category": ["violent", "property"],
    })
    counts = daily_counts(crime)
    assert len(counts) == 3 * 2  # 3 days x 2 categories, zeros included
    assert counts["crime_count"].sum() == 2


def test_panel_features(raw_crime_csv_style, weather_payload):
    crime, panel = _panel(raw_crime_csv_style, weather_payload)
    day1 = panel[panel["date"] == "2022-07-01"].iloc[0]
    day2 = panel[panel["date"] == "2022-07-02"].iloc[0]
    assert day2["temp_bin"] == "90+"
    assert bool(day2["is_weekend"]) is True       # July 2, 2022 was a Saturday
    assert bool(day1["is_first_of_month"]) is True
    assert bool(day1["is_jan_1"]) is False
    assert panel["rain_day"][panel["date"] == "2022-07-03"].all()
    assert panel["crime_count"].sum() == len(crime)


def test_hotspot_grid_drops_missing_coords(raw_crime_csv_style):
    grid = hotspot_grid(clean_crime(raw_crime_csv_style))
    assert grid["crime_count"].sum() == 3  # record "2" has no coordinates
