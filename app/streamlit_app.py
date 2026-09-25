"""Interactive dashboard. Reads only the small aggregated files in app/data/.

Run locally:  streamlit run app/streamlit_app.py
Generate data: crime-weather all   (or crime-weather publish after a full run)
"""

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"

st.set_page_config(page_title="LA Crime & Weather", page_icon="🌡️", layout="wide")


@st.cache_data
def load(name: str) -> pd.DataFrame | None:
    path = DATA / name
    if not path.exists():
        return None
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


panel = load("daily_panel.parquet")
hotspots = load("hotspots.parquet")
results = load("model_results.csv")
baseline = load("baseline_metrics.csv")
wx_rates = load("weather_type_rates.csv")
mix = load("crime_mix.csv")
quality_path = DATA / "quality_report.json"
quality = json.loads(quality_path.read_text()) if quality_path.exists() else None

st.title("Does weather move crime in Los Angeles?")
st.caption("LAPD incident data (2020–2023) joined with hourly weather. Associations, not causal effects.")

if panel is None:
    st.warning("No data found. Run `crime-weather all` to generate app/data/.")
    st.stop()

# Sidebar filters
cats = sorted(panel["crime_category"].unique())
chosen = st.sidebar.multiselect("Crime category", cats, default=cats)
dmin, dmax = panel["date"].min().date(), panel["date"].max().date()
date_range = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
if len(date_range) != 2:
    st.info("Pick both a start and an end date.")
    st.stop()
start, end = date_range
hide_artifacts = st.sidebar.checkbox("Hide 1st-of-month days", value=True,
                                     help="Crimes with unknown dates are often recorded on the 1st. See Data quality.")

view = panel[
    panel["crime_category"].isin(chosen)
    & panel["date"].between(pd.Timestamp(start), pd.Timestamp(end))
]
if hide_artifacts:
    view = view[~view["is_first_of_month"]]
daily = view.groupby(["date", "temp_max_f", "weather_type"], observed=True)["crime_count"].sum().reset_index()

c1, c2, c3 = st.columns(3)
c1.metric("Days", f"{daily['date'].nunique():,}")
c2.metric("Avg crimes / day", f"{daily['crime_count'].mean():,.0f}")
c3.metric("Avg max temp", f"{daily['temp_max_f'].mean():.0f}°F")

# 1. Raw relationship
st.subheader("Daily crime vs. maximum temperature")
scatter = alt.Chart(daily).mark_circle(opacity=0.35, size=18).encode(
    x=alt.X("temp_max_f:Q", title="Max temperature (°F)", scale=alt.Scale(zero=False)),
    y=alt.Y("crime_count:Q", title="Crimes that day", scale=alt.Scale(zero=False)),
    tooltip=["date:T", "temp_max_f:Q", "weather_type:N", "crime_count:Q"],
)
st.altair_chart(scatter + scatter.transform_loess("temp_max_f", "crime_count").mark_line(),
                use_container_width=True)

# 2. Weather types: share of crimes vs crimes per day
if wx_rates is not None:
    st.subheader("Weather types: how common vs. how much crime per day")
    st.caption("Most crimes happen on warm days mainly because most days are warm. "
               "Compare crimes *per day* instead (all categories, 1st-of-month days excluded).")
    left, right = st.columns(2)
    long = wx_rates.melt("weather_type", ["share_of_days_pct", "share_of_crimes_pct"],
                         var_name="measure", value_name="pct")
    long["measure"] = long["measure"].map({"share_of_days_pct": "% of days", "share_of_crimes_pct": "% of crimes"})
    left.altair_chart(
        alt.Chart(long).mark_bar().encode(
            x=alt.X("pct:Q", title="%"), y=alt.Y("weather_type:N", title=None, sort="-x"),
            color=alt.Color("measure:N", title=None), yOffset="measure:N",
        ),
        use_container_width=True,
    )
    right.altair_chart(
        alt.Chart(wx_rates).mark_bar().encode(
            x=alt.X("vs_average_pct:Q", title="Crimes per day vs. average (%)"),
            y=alt.Y("weather_type:N", title=None, sort="-x"),
            tooltip=["weather_type", "n_days", "avg_daily_crimes", "vs_average_pct"],
        ),
        use_container_width=True,
    )

# 3. Model
if results is not None:
    st.subheader("Model: effect of weather after controlling for season, weekday, year, holidays")
    st.caption("Incidence rate ratio vs. a dry 70–80°F day. 1.05 = 5% more crime. Bars are 95% CIs.")
    res = results[results["category"].isin(["all", *chosen])]
    base = alt.Chart(res).encode(y=alt.Y("term:N", title=None), color="category:N")
    st.altair_chart(
        base.mark_rule().encode(x=alt.X("ci_low:Q", title="IRR", scale=alt.Scale(zero=False)), x2="ci_high:Q")
        + base.mark_point(filled=True).encode(x="irr:Q"),
        use_container_width=True,
    )

if baseline is not None:
    st.subheader("Can weather alone predict daily crime?")
    st.caption(f"Linear regression trained on earlier days, tested on {baseline['test_period'].iloc[0]}. "
               "R² near zero (or below) means the model predicts no better than the average.")
    cols = st.columns(len(baseline))
    for col, row in zip(cols, baseline.itertuples(), strict=True):
        col.metric(row.model, f"R² = {row.r2:.2f}", f"MAE {row.mae:.0f} crimes/day", delta_color="off")

# 4. Benchmark
if mix is not None:
    st.subheader("LA's crime mix vs. other large California cities")
    st.caption("Share of FBI UCR Part I crimes. Benchmark: other California cities in Wikipedia's UCR table, "
               "population-weighted. The benchmark year may differ from LA's 2020–2023 data.")
    long = mix.melt("crime_type", ["la_share_pct", "benchmark_share_pct"], var_name="source", value_name="pct")
    long["source"] = long["source"].map({"la_share_pct": "Los Angeles", "benchmark_share_pct": "Other CA cities"})
    st.altair_chart(
        alt.Chart(long).mark_bar().encode(
            x=alt.X("pct:Q", title="% of UCR crimes"), y=alt.Y("crime_type:N", title=None, sort="-x"),
            color=alt.Color("source:N", title=None), yOffset="source:N",
        ),
        use_container_width=True,
    )

# 5. Map
if hotspots is not None:
    st.subheader("Where crime concentrates")
    hs = hotspots[hotspots["crime_category"].isin(chosen)]
    hs = hs.groupby(["lat", "lon"])["crime_count"].sum().reset_index()
    hs = hs[hs["crime_count"] >= hs["crime_count"].quantile(0.5)]
    hs["radius_m"] = 60 + 340 * hs["crime_count"] / hs["crime_count"].max()  # circle size in meters
    st.map(hs, latitude="lat", longitude="lon", size="radius_m")

# 6. Data quality
if quality is not None:
    with st.expander("Data quality"):
        st.write(f"**{quality['clean_rows']:,}** clean records from {quality['raw_rows']:,} raw rows.")
        st.write(f"**{quality['first_of_month_pct']}%** of crimes are dated the 1st of a month (≈3.3% expected). "
                 f"For fraud, it's **{quality['fraud_on_first_of_month_pct']}%**: when the exact date is unknown, "
                 "the 1st is often recorded. The model includes a flag for these days.")
        st.write(f"Missing coordinates: {quality['missing_coords_pct']}% · "
                 f"Uncategorized crime types: {quality['other_type_pct']}%")
        st.write("Data ends in 2023: LAPD changed records systems on March 7, 2024, "
                 "so this dataset's 2024 counts are incomplete.")

st.divider()
st.caption("Built by Sara Armengol · [GitHub](https://github.com/SaraArmengol/la-crime-weather)")
