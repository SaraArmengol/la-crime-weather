"""Command-line entry point.

    crime-weather extract              # download raw data (API)
    crime-weather extract --local-csv  # use your existing CSV download instead
    crime-weather transform
    crime-weather load
    crime-weather model
    crime-weather publish              # small files the dashboard reads
    crime-weather all
"""

from __future__ import annotations

import argparse
import json
import logging

import pandas as pd

from crime_weather.config import Settings, get_secret, load_settings
from crime_weather.extract import lapd, scrape_stats, weather
from crime_weather.http import make_session
from crime_weather.load import warehouse
from crime_weather.transform import clean_crime, clean_weather, features

logger = logging.getLogger("crime_weather")


def extract(s: Settings, local_csv: bool = False) -> None:
    raw_dir = s.path("raw")
    session = make_session()
    start, end = s["date_range"]["start"], s["date_range"]["end"]

    if local_csv:
        crime_raw = lapd.read_crime_csv(s["lapd"]["local_csv"])
    else:
        crime_raw = lapd.fetch_crime_api(
            s["lapd"]["base_url"], start, end,
            page_size=s["lapd"]["page_size"],
            app_token=get_secret("SOCRATA_APP_TOKEN"),
            session=session,
        )
    warehouse.write_parquet(crime_raw.astype(str), raw_dir / "crime_raw.parquet")

    w = s["weather"]
    payload = weather.fetch_weather(
        w["base_url"], w["latitude"], w["longitude"], start, end,
        w["daily_variables"], w["timezone"], raw_dir / "weather_cache", session=session,
    )
    warehouse.write_parquet(weather.parse_daily(payload), raw_dir / "weather_raw.parquet")

    if s["scrape"]["url"]:
        html = scrape_stats.fetch_html(s["scrape"]["url"], raw_dir / "html", session=session)
        table = scrape_stats.parse_table(html, s["scrape"]["table_index"])
        warehouse.write_parquet(table, raw_dir / "scraped_stats.parquet")
    else:
        logger.warning("scrape.url is empty in settings.yaml; skipping scraping step")


def transform(s: Settings) -> None:
    raw_dir, proc = s.path("raw"), s.path("processed")
    crime_raw = pd.read_parquet(raw_dir / "crime_raw.parquet")
    crime = clean_crime.clean_crime(crime_raw, s["date_range"]["start"], s["date_range"]["end"])
    report = clean_crime.quality_report(crime_raw, crime)
    logger.info("Data quality: %s", report)
    (proc / "quality_report.json").parent.mkdir(parents=True, exist_ok=True)
    (proc / "quality_report.json").write_text(json.dumps(report, indent=2))

    wx = clean_weather.clean_weather(pd.read_parquet(raw_dir / "weather_raw.parquet"))
    panel = features.build_daily_panel(crime, wx, s["features"])

    warehouse.write_parquet(crime, proc / "crime_clean.parquet")
    warehouse.write_parquet(wx, proc / "weather_clean.parquet")
    warehouse.write_parquet(panel, proc / "daily_panel.parquet")


def load(s: Settings) -> None:
    proc = s.path("processed")
    warehouse.load_into_duckdb(s.path("warehouse"), {
        "crime": proc / "crime_clean.parquet",
        "weather": proc / "weather_clean.parquet",
        "daily_panel": proc / "daily_panel.parquet",
    })


def model(s: Settings) -> None:
    from crime_weather.analysis.models import fit_all

    panel = pd.read_parquet(s.path("processed") / "daily_panel.parquet")
    results = fit_all(panel)
    results.to_csv(s.path("processed") / "model_results.csv", index=False)
    logger.info("Model results:\n%s", results.round(3).to_string(index=False))


def publish(s: Settings) -> None:
    """Write the small, aggregated files the dashboard needs (these ARE committed)."""
    proc, app = s.path("processed"), s.path("app_data")
    app.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(proc / "daily_panel.parquet")
    panel.to_parquet(app / "daily_panel.parquet", index=False)
    crime = pd.read_parquet(proc / "crime_clean.parquet")
    features.hotspot_grid(crime).to_parquet(app / "hotspots.parquet", index=False)
    if (proc / "model_results.csv").exists():
        pd.read_csv(proc / "model_results.csv").to_csv(app / "model_results.csv", index=False)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="crime-weather")
    parser.add_argument("stage", choices=["extract", "transform", "load", "model", "publish", "all"])
    parser.add_argument("--local-csv", action="store_true", help="Read LAPD data from local CSV")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    s = load_settings()

    stages = {
        "extract": lambda: extract(s, local_csv=args.local_csv),
        "transform": lambda: transform(s),
        "load": lambda: load(s),
        "model": lambda: model(s),
        "publish": lambda: publish(s),
    }
    order = list(stages) if args.stage == "all" else [args.stage]
    for name in order:
        logger.info("=== %s ===", name)
        stages[name]()


if __name__ == "__main__":
    main()
