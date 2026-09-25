"""Extract LAPD crime records from LA Open Data (Socrata API) or a local CSV.

Pulling from the API instead of a manual download makes the pipeline
reproducible end to end. Socrata pages results with $limit / $offset;
ordering by the record ID keeps pages stable between requests.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)


def fetch_crime_api(
    base_url: str,
    start: str,
    end: str,
    page_size: int = 50_000,
    app_token: str | None = None,
    session: requests.Session | None = None,
    max_pages: int | None = None,
) -> pd.DataFrame:
    """Download all crime records with date_occ in [start, end]."""
    session = session or requests.Session()
    headers = {"X-App-Token": app_token} if app_token else {}
    where = f"date_occ between '{start}T00:00:00' and '{end}T23:59:59'"

    frames: list[pd.DataFrame] = []
    offset, page = 0, 0
    while True:
        params = {"$where": where, "$order": "dr_no", "$limit": page_size, "$offset": offset}
        resp = session.get(base_url, params=params, headers=headers, timeout=120)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        frames.append(pd.DataFrame.from_records(rows))
        logger.info("Fetched page %d (%d rows, offset %d)", page, len(rows), offset)
        offset += page_size
        page += 1
        if len(rows) < page_size or (max_pages is not None and page >= max_pages):
            break

    if not frames:
        raise RuntimeError("Socrata API returned no rows. Check the date range and dataset ID.")
    return pd.concat(frames, ignore_index=True)


def read_crime_csv(path: str | Path) -> pd.DataFrame:
    """Read the manually downloaded LAPD CSV (all columns as strings; typing happens in transform)."""
    return pd.read_csv(path, dtype=str, low_memory=False)
