"""Scrape a statistics table from a web page (BeautifulSoup).

TODO: point `scrape.url` in config/settings.yaml at the page from your original
project and adapt `parse_table` if the page structure differs.

Good practice shown here:
  - raw HTML is saved to disk, so the analysis still runs if the site changes
  - parsing is a pure function of HTML, so it is unit-tested on a saved fixture
  - check the site's robots.txt and terms before scraping; note it in docs/data_sources.md
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


def fetch_html(url: str, snapshot_dir: Path, session: requests.Session | None = None) -> str:
    """Fetch a page once per day and keep a dated snapshot."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot = snapshot_dir / f"scrape_{date.today():%Y%m%d}.html"
    if snapshot.exists():
        return snapshot.read_text(encoding="utf-8")
    session = session or requests.Session()
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    snapshot.write_text(resp.text, encoding="utf-8")
    return resp.text


def parse_table(html: str, table_index: int = 0) -> pd.DataFrame:
    """Parse the Nth <table> into a DataFrame using its header row as columns."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) <= table_index:
        raise ValueError(f"Found {len(tables)} tables; wanted index {table_index}")
    rows = tables[table_index].find_all("tr")
    header = [cell.get_text(strip=True) for cell in rows[0].find_all(["th", "td"])]
    body = [
        [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
        for row in rows[1:]
    ]
    body = [r for r in body if len(r) == len(header)]
    return pd.DataFrame(body, columns=header)
