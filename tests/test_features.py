import pandas as pd

from crime_weather.extract.weather import parse_daily
from crime_weather.transform.clean_crime import clean_crime
from crime_weather.transform.clean_weather import clean_weather
from crime_weather.transform.features import build_daily_panel, daily_counts, hotspot_grid

FEATURE_CFG = {
    "temp_bins_f": [-100, 60, 70, 80, 90, 200],
    "temp_labels": ["<60", "60-70", "70-80", "80-90", "90+"],
    "rain_threshold_mm": 1.0,
}


def test_daily_counts_fill_zero_days():
    crime = pd.DataFrame({
        "date_occ": pd.to_datetime(["2022-07-01", "2022-07-03"]),
        "crime_category": ["violent", "property"],
    })
    counts = daily_counts(crime)
    assert len(counts) == 3 * 2  # 3 days x 2 categories, zeros included
    assert counts["crime_count"].sum() == 2


def test_panel_features(raw_crime_csv_style, weather_payload):
    crime = clean_crime(raw_crime_csv_style)
    wx = clean_weather(parse_daily(weather_payload))
    panel = build_daily_panel(crime, wx, FEATURE_CFG)

    day2 = panel[panel["date"] == "2022-07-02"].iloc[0]
    assert day2["temp_bin"] == "90+"
    assert bool(day2["is_weekend"]) is True  # July 2, 2022 was a Saturday
    assert not panel["rain_day"][panel["date"] == "2022-07-01"].any()
    assert panel["crime_count"].sum() == len(crime)


def test_hotspot_grid_drops_missing_coords(raw_crime_csv_style):
    grid = hotspot_grid(clean_crime(raw_crime_csv_style))
    assert grid["crime_count"].sum() == 2  # record "2" has no coordinates
