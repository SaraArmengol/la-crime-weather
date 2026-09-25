import pytest

from crime_weather.extract.scrape_stats import UCR_TYPES, benchmark_mix, parse_ucr_table


def test_parse_ucr_table_multilevel_header(wikipedia_html):
    df = parse_ucr_table(wikipedia_html)
    assert list(df.columns) == ["state", "city", "population", *UCR_TYPES]
    assert len(df) == 4
    la = df[df["city"] == "Los Angeles"].iloc[0]   # superscript footnote stripped
    assert la["population"] == 3_796_352
    assert la["Robbery"] == 209.86


def test_parse_ucr_table_missing_index(wikipedia_html):
    with pytest.raises(ValueError):
        parse_ucr_table(wikipedia_html, table_index=3)


def test_benchmark_is_population_weighted_and_excludes_la(wikipedia_html):
    mix = benchmark_mix(parse_ucr_table(wikipedia_html)).set_index("crime_type")
    # San Diego (1M people) and Fresno (0.5M) only. Implied larceny count:
    # 600*10 + 800*5 = 10,000 of 15,000 total (robbery 1,000, aggravated assault 2,000, burglary 1,000, MVT 1,000)
    assert mix.loc["Larceny theft", "benchmark_share_pct"] == pytest.approx(66.67, abs=0.01)
    assert mix["n_cities"].iloc[0] == 2
    assert mix["benchmark_share_pct"].sum() == pytest.approx(100, abs=0.05)
