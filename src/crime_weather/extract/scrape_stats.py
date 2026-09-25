"""Scrape the UCR crime-rate table for large US cities from Wikipedia.

Used as a benchmark: how does LA's mix of crime types compare with other large
California cities? Scraper logic comes from the CS 2316 version of the project.

Good practice shown here:
  - raw HTML is saved to disk, so the analysis still runs if the page changes
  - parsing is a pure function of HTML, so it is unit-tested on a saved fixture
  - columns are matched by name, not position, so a new column doesn't silently shift data
"""

from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Wikipedia header text (lowercased, partial match) -> our column name. Order matters.
COLUMN_PATTERNS = [
    ("state", "state"),
    ("city", "city"),
    ("popul", "population"),
    ("murder", "Homicide"),
    ("rape", "Rape"),
    ("robbery", "Robbery"),
    ("aggravated", "Aggravated assault"),
    ("arson", "Arson"),
    ("burglary", "Burglary"),
    ("larceny", "Larceny theft"),
    ("motor", "Motor vehicle theft"),
]
UCR_TYPES = [name for _, name in COLUMN_PATTERNS[3:]]


def fetch_html(url: str, snapshot_dir: Path, session: requests.Session | None = None) -> str:
    """Fetch a page once per day and keep a dated snapshot."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot = snapshot_dir / f"wikipedia_ucr_{date.today():%Y%m%d}.html"
    if snapshot.exists():
        return snapshot.read_text(encoding="utf-8")
    session = session or requests.Session()
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    snapshot.write_text(resp.text, encoding="utf-8")
    return resp.text


def _flatten(col) -> str:
    parts = col if isinstance(col, tuple) else (col,)
    return " ".join(str(p) for p in parts).lower()


def parse_ucr_table(html: str, table_index: int = 0) -> pd.DataFrame:
    """Parse the first wikitable into one row per city with UCR crime-type rates."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table", {"class": "wikitable"})
    if len(tables) <= table_index:
        raise ValueError(f"Found {len(tables)} wikitables; wanted index {table_index}")
    raw = pd.read_html(StringIO(str(tables[table_index])))[0]

    rename = {}
    for col in raw.columns:
        flat = _flatten(col)
        for pattern, name in COLUMN_PATTERNS:
            if pattern in flat and name not in rename.values():
                rename[col] = name
                break
    missing = {name for _, name in COLUMN_PATTERNS} - set(rename.values())
    if missing:
        raise ValueError(f"Could not find columns for: {sorted(missing)}")

    df = pd.DataFrame({name: raw[col] for col, name in rename.items()})
    # Footnote markers: "[3]" links or superscript digits ("Los Angeles2", "Florida3")
    for col in ("state", "city"):
        df[col] = df[col].astype(str).str.replace(r"\[.*?\]|\d+$", "", regex=True).str.strip()
    for col in ["population", *UCR_TYPES]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(r"[^\d.]", "", regex=True), errors="coerce")
    return df


def benchmark_mix(cities: pd.DataFrame, state: str = "California", exclude_city: str = "Los Angeles") -> pd.DataFrame:
    """Share of each UCR crime type across large cities in a state, excluding LA itself.

    The table reports rates per 100k residents, so rates are weighted by population
    to get implied counts before summing across cities.
    """
    subset = cities[(cities["state"] == state) & (cities["city"] != exclude_city)]
    if subset.empty:
        raise ValueError(f"No cities found for state={state!r}")
    counts = subset[UCR_TYPES].mul(subset["population"] / 100_000, axis=0).sum()
    return pd.DataFrame({
        "crime_type": counts.index,
        "benchmark_share_pct": (100 * counts / counts.sum()).round(2).values,
        "n_cities": len(subset),
    })
