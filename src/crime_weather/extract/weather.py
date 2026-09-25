"""Extract hourly historical weather for Los Angeles from Open-Meteo (free, no key).

Hourly data (rather than Open-Meteo's daily summaries) keeps the approach from the
CS 2316 version: aggregate hours into days ourselves, which also gives variables
the daily endpoint lacks (average cloud cover, average apparent temperature).
Responses are cached on disk so re-running the pipeline never re-hits the API.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)


def _cache_key(params: dict[str, Any]) -> str:
    blob = json.dumps(params, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def fetch_weather(
    base_url: str,
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    hourly_variables: list[str],
    timezone: str,
    cache_dir: Path,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Return the raw JSON payload, using a disk cache keyed on request parameters."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(hourly_variables),
        "timezone": timezone,
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "mm",
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"weather_{_cache_key(params)}.json"
    if cache_file.exists():
        logger.info("Weather cache hit: %s", cache_file.name)
        return json.loads(cache_file.read_text())

    session = session or requests.Session()
    resp = session.get(base_url, params=params, timeout=120)
    resp.raise_for_status()
    payload = resp.json()
    cache_file.write_text(json.dumps(payload))
    logger.info("Weather fetched and cached: %s", cache_file.name)
    return payload


def parse_hourly(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert Open-Meteo's column-oriented `hourly` block into a tidy DataFrame."""
    if "hourly" not in payload:
        raise ValueError(f"Unexpected weather payload; keys: {sorted(payload)}")
    df = pd.DataFrame(payload["hourly"])
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    return df.dropna(subset=["time"])
