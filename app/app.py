"""Streamlit dashboard:  streamlit run app/app.py

Question: Did India's 2020 lockdown clean the air, or just pause the pollution?
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import analysis, charts  # noqa: E402
from src.common import (  # noqa: E402
    BASELINE_YEARS, COORDS_FILE, MIN_COVERAGE, POLLUTANTS, POLLUTANT_NAMES, WINDOWS,EXCLUDE_CITIES,
)

st.set_page_config(page_title="India Lockdown Air Quality", page_icon="🌫️", layout="wide")


# ---- data loading (cached so filters feel instant) ---------------------------
@st.cache_data(show_spinner="Reading data...")
def read_path(path: str):
    return analysis.load_raw(path)


@st.cache_data(show_spinner="Reading data...")
def read_upload(data: bytes):
    import io
    return analysis.load_raw(io.BytesIO(data))


@st.cache_data(show_spinner="Cleaning and analysing...")
def compute(raw):
    return analysis.run_all(raw)


@st.cache_data
def coords():
    return analysis.load_coords(COORDS_FILE)


path = analysis.find_data_file()
if path is not None:
    raw = read_path(str(path))
else:
    st.title("India lockdown air quality")
    st.warning("`data/city_day.csv` was not found. Upload it below, or put it in the "
               "`data/` folder (Kaggle: *Air Quality Data in India 2015-2020*).")
    up = st.file_uploader("Upload city_day.csv", type="csv")
    if up is None:
        st.stop()
    try:
        raw = read_upload(up.getvalue())
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not read that file: {e}")
        st.stop()

df, cov, stats, summary, kept = compute(raw)
if not kept:
    st.error("No city has enough data in the lockdown window. Check the file.")
    st.stop()

# ---- sidebar filters --------------------------------------------------------
st.sidebar.header("Filters")
pollutant = st.sidebar.selectbox("Pollutant", [p for p in POLLUTANTS if p in df.columns],
                                 format_func=lambda p: POLLUTANT_NAMES.get(p, p))
default_city = kept.index("Delhi") if "Delhi" in kept else 0
city = st.sidebar.selectbox("City", kept, index=default_city)
smooth = st.sidebar.slider("Smoothing (days)", 1, 14, 7,
                           help="Rolling average used in the time-series chart.")
st.sidebar.caption(f"{len(kept)} of {len(cov)} cities have enough data "
                   f"(at least {MIN_COVERAGE:.0%} of days) to compare fairly.")

# ---- header -----------------------------------------------------------------
st.title("Did the 2020 lockdown clean India's air, or just pause the pollution?")
st.caption("Lockdown window 25 Mar - 31 May 2020, compared with the same calendar dates in "
           f"{BASELINE_YEARS[0]}-{BASELINE_YEARS[-1]}. Source: CPCB data via Kaggle.")

h = analysis.headline(summary, pollutant)
pf = analysis.pause_or_fix(summary, "AQI") if "AQI" in df.columns else None

c1, c2, c3 = st.columns(3)
if h:
    c1.metric("Median change in " + pollutant, f"{h['median']:+.0f}%",
              help="Lockdown 2020 vs same dates in 2017-2019, median across cities.")
    c2.metric("Cities cleaner than usual", f"{h['n_improved']} of {h['n_cities']}")
    c3.metric(f"Biggest drop: {h['best_city']}", f"{h['best']:+.0f}%")

tab_map, tab_lock, tab_fix, tab_corr, tab_data = st.tabs(
    ["Overview map", "Lockdown analysis", "Pause or fix?", "Pollutants", "Data & method"])

# ---- tab 1: map ---------------------------------------------------------------
with tab_map:
    st.write("Each bubble is a city. Press play or drag the slider to move through the months; "
             "darker and larger means worse air.")
    years = sorted(df["Date"].dt.year.unique())
    lo, hi = st.select_slider("Years shown", options=years, value=(max(years) - 1, max(years)))
    monthly = analysis.monthly_city(df, coords(), pollutant)
    monthly = monthly[~monthly["City"].isin(EXCLUDE_CITIES)]
    monthly = monthly[monthly["Month"].str[:4].astype(int).between(lo, hi)]
    missing = sorted(set(df["City"]) - set(coords()["City"]))
    if missing:
        st.caption("No coordinates for: " + ", ".join(missing))
    if monthly.empty:
        st.info("No monthly data for that selection.")
    else:
        st.plotly_chart(charts.animated_map(monthly, pollutant), width="stretch")

# ---- tab 2: lockdown analysis ---------------------------------------------------
with tab_lock:
    row = summary[(summary["City"] == city) & (summary["Pollutant"] == pollutant)
                  & (summary["window"] == "lockdown")]
    curve = analysis.daily_curve(df, city, pollutant, smooth)
    if not row.empty:
        r = row.iloc[0]
        word = "lower" if r["pct_change"] < 0 else "higher"
        st.info(f"**{city}:** average {pollutant} during the lockdown was **{r['y2020']:.0f}**, "
                f"versus **{r['baseline']:.0f}** on the same dates in normal years - "
                f"**{abs(r['pct_change']):.0f}% {word}**.")
        title = f"{city}: {pollutant} was {abs(r['pct_change']):.0f}% {word} than usual in the lockdown"
    else:
        st.warning(f"Not enough {pollutant} data for {city} to compare.")
        title = None
    st.plotly_chart(charts.baseline_vs_2020(curve, city, pollutant, title), width="stretch")
    st.markdown("---")
    st.write("Same comparison for every city. The orange dot is 2020; the blue dot is the "
             "normal-year average. Cities are ordered from the biggest drop at the top.")
    if (summary["Pollutant"] == pollutant).any():
        st.plotly_chart(charts.dumbbell(summary, pollutant), width="stretch")
    with st.expander("Show data table"):
        t = summary[(summary["Pollutant"] == pollutant) & (summary["window"] == "lockdown")]
        st.dataframe(t[["City", "baseline", "y2020", "pct_change"]]
                     .rename(columns={"baseline": "Normal years", "y2020": "2020",
                                      "pct_change": "% change"}).round(1),
                     hide_index=True, width="stretch")

# ---- tab 3: pause or fix ------------------------------------------------------
with tab_fix:
    if pf is None or pf.empty:
        st.info("Not enough AQI data to compare lockdown and June.")
    else:
        verdicts = pf["verdict"].value_counts()
        st.write("If the lockdown really *fixed* something, the improvement should still be "
                 "visible once the economy reopened. Both bars below are measured against "
                 "normal years on the same dates, so the monsoon and seasons cancel out.")
        st.info("  \n".join(f"**{n} cities:** {v.lower()}" for v, n in verdicts.items()))
        st.plotly_chart(charts.pause_or_fix_bars(pf, "AQI"), width="stretch")
        st.caption("The dataset ends in early July 2020, so this shows only the first month "
                   "of the rebound. 'Retained' means the share of the lockdown improvement "
                   "still present in June.")
        with st.expander("Show data table"):
            st.dataframe(pf[["City", "pct_lockdown", "pct_june", "verdict"]]
                         .rename(columns={"pct_lockdown": "Lockdown % vs normal",
                                          "pct_june": "June % vs normal"}).round(1),
                         hide_index=True, width="stretch")

# ---- tab 4: pollutants ------------------------------------------------------------
with tab_corr:
    scope = st.radio("Show correlations for", ["All compared cities", city], horizontal=True)
    corr = analysis.correlation(df, kept if scope == "All compared cities" else [city])
    st.plotly_chart(charts.correlation_heatmap(corr, f"How pollutants move together ({scope})"),
                    width="stretch")
    st.caption("Values near 1 mean two pollutants rise and fall together; "
               "near 0 means they are mostly unrelated.")

# ---- tab 5: data & method ------------------------------------------------------------
with tab_data:
    s, e = WINDOWS["lockdown"]
    st.markdown(f"""
**Method**
1. Keep daily readings per city; negative readings are treated as missing.
2. Gaps of up to 3 days are filled by interpolation; longer gaps stay empty.
3. For each city, compare the mean over **25 Mar - 31 May 2020** with the mean over the same dates in
   **{BASELINE_YEARS[0]}-{BASELINE_YEARS[-1]}** (the average of valid years).
4. A city is included only if at least **{MIN_COVERAGE:.0%}** of the window's days have data in 2020 and in at
   least 2 baseline years. The same rule is applied to the June comparison.

**Limitations.** Weather (wind, rain, temperature) also changes air quality, so results are *consistent
with* a lockdown effect, not proof of it. Stations differ between years, and the data ends in July 2020.
""")
    st.subheader("Days of AQI data in the lockdown window")
    st.dataframe(cov.rename(columns={"keep": "included"}).rename(columns=str), width="stretch")
