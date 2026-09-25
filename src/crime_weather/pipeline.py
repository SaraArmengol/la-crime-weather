"""Command-line entry point.

    crime-weather extract              # download raw data (skips crime data already downloaded)
    crime-weather extract --refresh    # force a fresh crime download
    crime-weather extract --local-csv  # read LAPD data from a local CSV instead of the API
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


def extract(s: Settings, local_csv: bool = False, refresh: bool = False) -> None:
    raw_dir = s.path("raw")
    session = make_session()
    start, end = s["date_range"]["start"], s["date_range"]["end"]

    crime_path = raw_dir / "crime_raw.parquet"
    if crime_path.exists() and not refresh and not local_csv:
        logger.info("Crime data already downloaded (%s); use --refresh to re-download", crime_path.name)
    else:
        if local_csv:
            crime_raw = lapd.read_crime_csv(s["lapd"]["local_csv"])
        else:
            crime_raw = lapd.fetch_crime_api(
                s["lapd"]["base_url"], start, end,
                page_size=s["lapd"]["page_size"],
                app_token=get_secret("SOCRATA_APP_TOKEN"),
                session=session,
            )
        warehouse.write_parquet(crime_raw.astype(str), crime_path)

    w = s["weather"]
    payload = weather.fetch_weather(
        w["base_url"], w["latitude"], w["longitude"], start, end,
        w["hourly_variables"], w["timezone"], raw_dir / "weather_cache", session=session,
    )
    warehouse.write_parquet(weather.parse_hourly(payload), raw_dir / "weather_hourly.parquet")

    html = scrape_stats.fetch_html(s["scrape"]["url"], raw_dir / "html", session=session)
    cities = scrape_stats.parse_ucr_table(html, s["scrape"]["table_index"])
    warehouse.write_parquet(cities, raw_dir / "ucr_cities.parquet")


def transform(s: Settings) -> None:
    raw_dir, proc = s.path("raw"), s.path("processed")
    proc.mkdir(parents=True, exist_ok=True)

    crime_raw = pd.read_parquet(raw_dir / "crime_raw.parquet")
    crime = clean_crime.clean_crime(crime_raw, s["date_range"]["start"], s["date_range"]["end"])
    report = clean_crime.quality_report(crime_raw, crime)
    logger.info("Data quality: %s", report)
    (proc / "quality_report.json").write_text(json.dumps(report, indent=2))

    hourly = pd.read_parquet(raw_dir / "weather_hourly.parquet")
    wx = clean_weather.clean_weather(hourly, s["features"]["weather_type"])
    panel = features.build_daily_panel(crime, wx, s["features"])

    cities = pd.read_parquet(raw_dir / "ucr_cities.parquet")
    benchmark = scrape_stats.benchmark_mix(cities, state=s["scrape"]["benchmark_state"])

    warehouse.write_parquet(crime, proc / "crime_clean.parquet")
    warehouse.write_parquet(wx, proc / "weather_clean.parquet")
    warehouse.write_parquet(panel, proc / "daily_panel.parquet")
    warehouse.write_parquet(benchmark, proc / "ucr_benchmark.parquet")


def load(s: Settings) -> None:
    proc = s.path("processed")
    warehouse.load_into_duckdb(s.path("warehouse"), {
        "crime": proc / "crime_clean.parquet",
        "weather": proc / "weather_clean.parquet",
        "daily_panel": proc / "daily_panel.parquet",
        "ucr_benchmark": proc / "ucr_benchmark.parquet",
    })


def model(s: Settings) -> None:
    from crime_weather.analysis.baseline import compare_baselines
    from crime_weather.analysis.descriptive import crime_mix_vs_benchmark, weather_type_rates
    from crime_weather.analysis.models import fit_all

    proc = s.path("processed")
    panel = pd.read_parquet(proc / "daily_panel.parquet")
    crime = pd.read_parquet(proc / "crime_clean.parquet", columns=["crime_type"])
    benchmark = pd.read_parquet(proc / "ucr_benchmark.parquet")

    outputs = {
        "model_results.csv": fit_all(panel),
        "baseline_metrics.csv": compare_baselines(panel),
        "weather_type_rates.csv": weather_type_rates(panel),
        "crime_mix.csv": crime_mix_vs_benchmark(crime, benchmark),
    }
    for name, df in outputs.items():
        df.to_csv(proc / name, index=False)
        logger.info("%s:\n%s", name, df.to_string(index=False))


def publish(s: Settings) -> None:
    """Write the small, aggregated files the dashboard needs (these ARE committed)."""
    proc, app = s.path("processed"), s.path("app_data")
    app.mkdir(parents=True, exist_ok=True)
    pd.read_parquet(proc / "daily_panel.parquet").to_parquet(app / "daily_panel.parquet", index=False)
    crime = pd.read_parquet(proc / "crime_clean.parquet")
    features.hotspot_grid(crime).to_parquet(app / "hotspots.parquet", index=False)
    for name in ["model_results.csv", "baseline_metrics.csv", "weather_type_rates.csv", "crime_mix.csv"]:
        if (proc / name).exists():
            pd.read_csv(proc / name).to_csv(app / name, index=False)
    if (proc / "quality_report.json").exists():
        (app / "quality_report.json").write_text((proc / "quality_report.json").read_text())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="crime-weather")
    parser.add_argument("stage", choices=["extract", "transform", "load", "model", "publish", "all"])
    parser.add_argument("--local-csv", action="store_true", help="Read LAPD data from local CSV")
    parser.add_argument("--refresh", action="store_true", help="Re-download crime data even if cached")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    s = load_settings()

    stages = {
        "extract": lambda: extract(s, local_csv=args.local_csv, refresh=args.refresh),
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
