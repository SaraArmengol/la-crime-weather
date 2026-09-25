import json
from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def weather_payload() -> dict:
    return json.loads((FIXTURES / "weather_response.json").read_text())


@pytest.fixture
def raw_crime_csv_style() -> pd.DataFrame:
    """Mimics the LAPD CSV download: spaced, mixed-case column names; strings everywhere."""
    return pd.DataFrame({
        "DR_NO": ["1", "2", "2", "3", "4"],
        "DATE OCC": ["07/01/2022 12:00:00 AM", "07/01/2022 12:00:00 AM",
                     "07/01/2022 12:00:00 AM", "07/02/2022 12:00:00 AM", "not a date"],
        "TIME OCC": ["1530", "5", "5", "2400", "1200"],
        "AREA": ["1", "1", "1", "2", "2"],
        "AREA NAME": ["Central", "Central", "Central", "Rampart", "Rampart"],
        "Crm Cd": ["510", "624", "624", "330", "740"],
        "Crm Cd Desc": ["VEHICLE - STOLEN", "BATTERY - SIMPLE ASSAULT", "BATTERY - SIMPLE ASSAULT",
                        "BURGLARY FROM VEHICLE", "VANDALISM - FELONY"],
        "LAT": ["34.05", "0", "0", "34.06", "34.07"],
        "LON": ["-118.25", "0", "0", "-118.27", "-118.28"],
    })
