"""Interactive dashboard. Reads only the small aggregated files in app/data/.

Run locally:  streamlit run app/streamlit_app.py
Generate data: crime-weather all   (or crime-weather publish after a full run)
"""

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

st.title("Does weather move crime in Los Angeles?")
st.caption("LAPD incident data joined with daily weather. Associations, not causal effects.")

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

view = panel[
    panel["crime_category"].isin(chosen)
    & panel["date"].between(pd.Timestamp(start), pd.Timestamp(end))
]
daily = view.groupby(["date", "temp_max_f", "temp_bin"], observed=True)["crime_count"].sum().reset_index()

c1, c2, c3 = st.columns(3)
c1.metric("Days", f"{daily['date'].nunique():,}")
c2.metric("Avg crimes / day", f"{daily['crime_count'].mean():,.0f}")
c3.metric("Avg max temp", f"{daily['temp_max_f'].mean():.0f}°F")

st.subheader("Daily crime vs. maximum temperature")
scatter = alt.Chart(daily).mark_circle(opacity=0.35, size=18).encode(
    x=alt.X("temp_max_f:Q", title="Max temperature (°F)"),
    y=alt.Y("crime_count:Q", title="Crimes that day"),
    tooltip=["date:T", "temp_max_f:Q", "crime_count:Q"],
)
st.altair_chart(scatter + scatter.transform_loess("temp_max_f", "crime_count").mark_line(),
                use_container_width=True)

if results is not None:
    st.subheader("Model: effect of weather after controlling for season, weekday, year, holidays")
    st.caption("Incidence rate ratio vs. a 70-80°F dry day. 1.05 = 5% more crime. Bars are 95% CIs.")
    res = results[results["category"].isin(["all", *chosen])]
    base = alt.Chart(res).encode(y=alt.Y("term:N", title=None), color="category:N")
    st.altair_chart(
        base.mark_rule().encode(x=alt.X("ci_low:Q", title="IRR", scale=alt.Scale(zero=False)),
                                x2="ci_high:Q")
        + base.mark_point(filled=True).encode(x="irr:Q"),
        use_container_width=True,
    )

if hotspots is not None:
    st.subheader("Where crime concentrates")
    hs = hotspots[hotspots["crime_category"].isin(chosen)]
    hs = hs.groupby(["lat", "lon"])["crime_count"].sum().reset_index()
    hs = hs[hs["crime_count"] >= hs["crime_count"].quantile(0.5)]
    hs["radius_m"] = 60 + 340 * hs["crime_count"] / hs["crime_count"].max()  # circle size in meters
    st.map(hs, latitude="lat", longitude="lon", size="radius_m")

st.divider()
st.caption("Built by Sara Armengol · [GitHub](https://github.com/<your-username>/la-crime-weather)")
