from pathlib import Path

import pytest

from crime_weather.extract.scrape_stats import parse_table

HTML = (Path(__file__).parent / "fixtures" / "stats_page.html").read_text()


def test_parse_table():
    df = parse_table(HTML)
    assert list(df.columns) == ["Year", "Violent", "Property"]
    assert df.iloc[1]["Violent"] == "31,000"


def test_parse_table_missing_index():
    with pytest.raises(ValueError):
        parse_table(HTML, table_index=3)
