import pandas as pd
import pytest
from conftest import WEATHER_TYPE_CFG

from crime_weather.extract.weather import fetch_weather, parse_hourly
from crime_weather.transform.clean_weather import aggregate_daily, classify_weather_type, clean_weather


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Stands in for requests.Session so tests never touch the network."""

    def __init__(self, payload):
        self.payload, self.calls = payload, 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return FakeResponse(self.payload)


def _fetch(session, cache_dir):
    return fetch_weather("https://example.test", 34.05, -118.24, "2022-07-01", "2022-07-03",
                         ["temperature_2m"], "America/Los_Angeles", cache_dir, session=session)


def test_fetch_uses_cache(weather_payload, tmp_path):
    session = FakeSession(weather_payload)
    _fetch(session, tmp_path)
    _fetch(session, tmp_path)
    assert session.calls == 1  # second call served from disk


def test_parse_hourly_rejects_bad_payload():
    with pytest.raises(ValueError):
        parse_hourly({"error": True, "reason": "bad request"})


def test_aggregate_daily(weather_payload):
    daily = aggregate_daily(parse_hourly(weather_payload)).set_index("date")
    assert len(daily) == 3
    assert daily.loc["2022-07-01", "temp_mean_f"] == 80.0
    assert daily.loc["2022-07-01", "temp_max_f"] == 90.0
    assert daily.loc["2022-07-02", "precip_mm"] == 0.0  # missing hour treated as no precipitation
    assert daily.loc["2022-07-03", "precip_mm"] == 3.4


def test_weather_type_order_and_thresholds():
    daily = pd.DataFrame({
        "temp_mean_f": [85.0, 85.0, 85.0, 70.0, 55.0, 45.0],
        "precip_mm":   [5.0,  0.0,  0.0,  0.5,  0.0,  0.0],
        "cloud_cover_pct": [90, 90, 10, 10, 10, 10],
        "snowfall_cm": [0, 0, 0, 0, 0, 0],
    })
    labels = classify_weather_type(daily, WEATHER_TYPE_CFG).tolist()
    # rain beats clouds beats temperature; 0.5 mm drizzle is below the rain threshold
    assert labels == ["Rainy", "Cloudy", "Hot", "Warm", "Cool", "Cold"]


def test_clean_weather_end_to_end(weather_payload):
    wx = clean_weather(parse_hourly(weather_payload), WEATHER_TYPE_CFG)
    assert wx["weather_type"].tolist() == ["Warm", "Hot", "Rainy"]
