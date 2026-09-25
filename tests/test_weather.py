import pytest

from crime_weather.extract.weather import fetch_weather, parse_daily
from crime_weather.transform.clean_weather import clean_weather


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
                         ["temperature_2m_max"], "America/Los_Angeles", cache_dir, session=session)


def test_parse_daily(weather_payload):
    df = parse_daily(weather_payload)
    assert len(df) == 3 and "date" in df.columns
    assert df["temperature_2m_max"].iloc[1] == 91.5


def test_parse_daily_rejects_bad_payload():
    with pytest.raises(ValueError):
        parse_daily({"error": True, "reason": "bad request"})


def test_fetch_uses_cache(weather_payload, tmp_path):
    session = FakeSession(weather_payload)
    _fetch(session, tmp_path)
    _fetch(session, tmp_path)
    assert session.calls == 1  # second call served from disk


def test_clean_weather_renames_and_fills(weather_payload):
    wx = clean_weather(parse_daily(weather_payload))
    assert {"temp_max_f", "precip_mm"} <= set(wx.columns)
    assert wx["precip_mm"].notna().all()
