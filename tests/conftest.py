import json
from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"

WEATHER_TYPE_CFG = {
    "rain_threshold_mm": 1.0,
    "snow_threshold_cm": 1.0,
    "cloudy_threshold_pct": 70,
    "hot_min_f": 82.4,
    "warm_min_f": 59.0,
    "cool_min_f": 51.8,
}

FEATURE_CFG = {
    "temp_bins_f": [-100, 60, 70, 80, 90, 200],
    "temp_labels": ["<60", "60-70", "70-80", "80-90", "90+"],
    "weather_type": WEATHER_TYPE_CFG,
}


@pytest.fixture
def weather_payload() -> dict:
    return json.loads((FIXTURES / "weather_hourly.json").read_text())


@pytest.fixture
def wikipedia_html() -> str:
    return (FIXTURES / "wikipedia_ucr.html").read_text()


@pytest.fixture
def raw_crime_csv_style() -> pd.DataFrame:
    """Mimics the LAPD CSV download: spaced, mixed-case column names; strings everywhere."""
    return pd.DataFrame({
        "DR_NO": ["1", "2", "2", "3", "4", "5"],
        "DATE OCC": ["07/01/2022 12:00:00 AM", "07/01/2022 12:00:00 AM", "07/01/2022 12:00:00 AM",
                     "07/02/2022 12:00:00 AM", "not a date", "07/03/2022 12:00:00 AM"],
        "TIME OCC": ["1530", "5", "5", "2400", "1200", "0900"],
        "AREA": ["1", "1", "1", "2", "2", "2"],
        "AREA NAME": ["Central", "Central", "Central", "Rampart", "Rampart", "Rampart"],
        "Crm Cd": ["510", "624", "624", "330", "740", "354"],
        "Crm Cd Desc": ["VEHICLE - STOLEN", "BATTERY - SIMPLE ASSAULT", "BATTERY - SIMPLE ASSAULT",
                        "BURGLARY FROM VEHICLE", "VANDALISM - FELONY", "THEFT OF IDENTITY"],
        "LAT": ["34.05", "0", "0", "34.06", "34.07", "34.08"],
        "LON": ["-118.25", "0", "0", "-118.27", "-118.28", "-118.29"],
    })
