"""Extract daily historical weather for Los Angeles.

Default provider: Open-Meteo historical archive (free, no key).
Responses are cached to disk so re-running the pipeline never re-hits the API.
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
    daily_variables: list[str],
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
        "daily": ",".join(daily_variables),
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
    resp = session.get(base_url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    cache_file.write_text(json.dumps(payload))
    logger.info("Weather fetched and cached: %s", cache_file.name)
    return payload


def parse_daily(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert Open-Meteo's column-oriented `daily` block into a tidy DataFrame."""
    if "daily" not in payload:
        raise ValueError(f"Unexpected weather payload; keys: {sorted(payload)}")
    df = pd.DataFrame(payload["daily"])
    df = df.rename(columns={"time": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df
