"""Loading, cleaning and the lockdown-vs-baseline analysis.

The core idea: compare the lockdown window of 2020 with the *same calendar
dates* in 2017-2019, city by city. Comparing against January or February would
mix the lockdown effect with the normal seasonal change.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .common import (
    BASELINE_YEARS, DATA_DIR, COORDS_FILE, LOCKDOWN_YEAR, MAX_GAP_DAYS,
    MIN_BASELINE_YEARS, MIN_COVERAGE, NUMERIC_COLUMNS, POLLUTANTS, WINDOWS,EXCLUDE_CITIES,
)


# ----------------------------------------------------------------------------
# 1. Loading
# ----------------------------------------------------------------------------
def find_data_file(data_dir: Path = DATA_DIR) -> Path | None:
    """Find city_day.csv in data/ (also tolerates names like city_day.csv.csv)."""
    exact = data_dir / "city_day.csv"
    if exact.exists():
        return exact
    matches = sorted(data_dir.glob("city_day*"))
    return matches[0] if matches else None


def load_raw(source) -> pd.DataFrame:
    """Read the Kaggle CSV from a path or an uploaded file object."""
    df = pd.read_csv(source)
    df.columns = [c.strip() for c in df.columns]
    missing = {"City", "Date"} - set(df.columns)
    if missing:
        raise ValueError(f"Expected columns {sorted(missing)} not found. "
                         "Is this the city_day.csv file?")
    df["Date"] = pd.to_datetime(df["Date"])
    df["City"] = df["City"].astype(str).str.strip()
    return df


def load_coords(path: Path = COORDS_FILE) -> pd.DataFrame:
    return pd.read_csv(path)


# ----------------------------------------------------------------------------
# 2. Cleaning
# ----------------------------------------------------------------------------
def fill_short_gaps(s: pd.Series, max_gap: int) -> pd.Series:
    """Linearly interpolate gaps of at most `max_gap` days. Longer gaps stay empty.

    (pandas' own `limit=` would fill the *first* few days of a long gap, which
    would invent data. This fills only gaps that are fully short.)
    """
    isna = s.isna()
    group = (~isna).cumsum()
    gap_len = isna.groupby(group).transform("sum")
    filled = s.interpolate(limit_area="inside")
    return s.where(~(isna & (gap_len <= max_gap)), filled)


def clean(raw: pd.DataFrame, max_gap: int = MAX_GAP_DAYS) -> pd.DataFrame:
    """Return a tidy, daily table per city.

    - keeps numeric pollutant columns only
    - turns impossible values (negative readings) into missing values
    - gives every city a continuous daily calendar
    - interpolates only short gaps (<= max_gap days)
    """
    cols = [c for c in NUMERIC_COLUMNS if c in raw.columns]
    df = raw[["City", "Date"] + cols].drop_duplicates(["City", "Date"]).copy()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df.loc[df[c] < 0, c] = float("nan")

    parts = []
    for city, g in df.groupby("City"):
        g = g.set_index("Date").sort_index().drop(columns="City")
        full = pd.date_range(g.index.min(), g.index.max(), freq="D")
        g = g.reindex(full)
        for c in cols:
            g[c] = fill_short_gaps(g[c], max_gap)
        g["City"] = city
        parts.append(g.rename_axis("Date").reset_index())
    return pd.concat(parts, ignore_index=True)


# ----------------------------------------------------------------------------
# 3. Coverage: which cities can be compared fairly?
# ----------------------------------------------------------------------------
def _window_bounds(year: int, window: str):
    start, end = WINDOWS[window]
    return pd.Timestamp(f"{year}-{start}"), pd.Timestamp(f"{year}-{end}")


def window_stats(df: pd.DataFrame, pollutants=POLLUTANTS) -> pd.DataFrame:
    """Mean and number of valid days per city / pollutant / window / year."""
    pollutants = [p for p in pollutants if p in df.columns]
    rows = []
    for window in WINDOWS:
        for year in BASELINE_YEARS + [LOCKDOWN_YEAR]:
            start, end = _window_bounds(year, window)
            n_days = (end - start).days + 1
            sub = df[(df["Date"] >= start) & (df["Date"] <= end)]
            if sub.empty:
                continue
            g = sub.groupby("City")[pollutants]
            mean = g.mean().reset_index().melt("City", var_name="Pollutant", value_name="mean")
            cnt = g.count().reset_index().melt("City", var_name="Pollutant", value_name="n")
            t = mean.merge(cnt, on=["City", "Pollutant"])
            t["window"], t["year"], t["n_days"] = window, year, n_days
            rows.append(t)
    out = pd.concat(rows, ignore_index=True)
    out["valid"] = out["n"] >= MIN_COVERAGE * out["n_days"]
    return out


def coverage_table(stats: pd.DataFrame) -> pd.DataFrame:
    """Days of AQI data in the lockdown window, per city and year, plus a keep flag."""
    s = stats[(stats["Pollutant"] == "AQI") & (stats["window"] == "lockdown")]
    days = s.pivot(index="City", columns="year", values="n").fillna(0).astype(int)
    for y in BASELINE_YEARS + [LOCKDOWN_YEAR]:
        if y not in days.columns:
            days[y] = 0
    days = days[BASELINE_YEARS + [LOCKDOWN_YEAR]]
    need = MIN_COVERAGE * s["n_days"].iloc[0]
    ok_2020 = days[LOCKDOWN_YEAR] >= need
    ok_base = (days[BASELINE_YEARS] >= need).sum(axis=1) >= MIN_BASELINE_YEARS
    days["keep"] = ok_2020 & ok_base
    return days.sort_values("keep", ascending=False)


# ----------------------------------------------------------------------------
# 4. Lockdown vs baseline summary
# ----------------------------------------------------------------------------
def build_summary(stats: pd.DataFrame) -> pd.DataFrame:
    """One row per city / pollutant / window with baseline, 2020 and % change."""
    base = stats[stats["year"].isin(BASELINE_YEARS) & stats["valid"]]
    b = (base.groupby(["City", "Pollutant", "window"])
             .agg(baseline=("mean", "mean"), n_base_years=("year", "nunique"))
             .reset_index())
    b = b[b["n_base_years"] >= MIN_BASELINE_YEARS]
    cur = (stats[(stats["year"] == LOCKDOWN_YEAR) & stats["valid"]]
           [["City", "Pollutant", "window", "mean"]].rename(columns={"mean": "y2020"}))
    out = b.merge(cur, on=["City", "Pollutant", "window"])
    out["pct_change"] = (out["y2020"] / out["baseline"] - 1) * 100
    return out.sort_values(["Pollutant", "window", "pct_change"]).reset_index(drop=True)


def pause_or_fix(summary: pd.DataFrame, pollutant: str = "AQI") -> pd.DataFrame:
    """Per city: change vs baseline during lockdown and in June, and how much held.

    retained = share of the lockdown improvement still present in June
    (both measured against their own baseline, so the season cancels out).
    """
    s = summary[summary["Pollutant"] == pollutant]
    lock = s[s["window"] == "lockdown"].set_index("City")
    june = s[s["window"] == "june"].set_index("City")
    t = pd.DataFrame({
        "pct_lockdown": lock["pct_change"],
        "pct_june": june["pct_change"],
        "lockdown_2020": lock["y2020"],
        "june_2020": june["y2020"],
        "lockdown_baseline": lock["baseline"],
        "june_baseline": june["baseline"],
    }).dropna(subset=["pct_lockdown", "pct_june"])
    t["rebound_pct"] = (t["june_2020"] / t["lockdown_2020"] - 1) * 100

    def verdict(r):
        if r["pct_lockdown"] > -5:
            return "No clear lockdown drop"
        retained = r["pct_june"] / r["pct_lockdown"]
        if retained >= 0.66:
            return "Improvement mostly held"
        if retained >= 0.33:
            return "Improvement partly held"
        return "Mostly bounced back"

    t["verdict"] = t.apply(verdict, axis=1)
    return t.reset_index().sort_values("pct_lockdown")


def headline(summary: pd.DataFrame, pollutant: str = "AQI") -> dict | None:
    """Key numbers for the written insight above the charts."""
    s = summary[(summary["Pollutant"] == pollutant) & (summary["window"] == "lockdown")]
    if s.empty:
        return None
    best = s.sort_values("pct_change").iloc[0]
    worst = s.sort_values("pct_change").iloc[-1]
    return {
        "n_cities": int(s["City"].nunique()),
        "median": float(s["pct_change"].median()),
        "best_city": best["City"], "best": float(best["pct_change"]),
        "worst_city": worst["City"], "worst": float(worst["pct_change"]),
        "n_improved": int((s["pct_change"] < 0).sum()),
    }


# ----------------------------------------------------------------------------
# 5. Series used by the charts
# ----------------------------------------------------------------------------
def daily_curve(df: pd.DataFrame, city: str, pollutant: str, smooth: int = 7) -> pd.DataFrame:
    """2020 vs the 2017-2019 range, for each day from 1 Mar to 30 Jun.

    Values are smoothed with a centred rolling mean (default 7 days).
    Output dates are placed on 2020's calendar so all lines share one x-axis.
    """
    g = df[df["City"] == city].set_index("Date")[pollutant]
    s = g.rolling(smooth, min_periods=max(2, smooth // 2), center=True).mean()
    f = pd.DataFrame({"v": s, "year": s.index.year, "md": s.index.strftime("%m-%d")})
    f = f[(f["md"] >= "03-01") & (f["md"] <= "06-30")]
    wide = f.pivot_table(index="md", columns="year", values="v")
    base_cols = [y for y in BASELINE_YEARS if y in wide.columns]
    out = pd.DataFrame(index=wide.index)
    out["y2020"] = wide.get(LOCKDOWN_YEAR)
    if base_cols:
        b = wide[base_cols]
        enough = b.notna().sum(axis=1) >= MIN_BASELINE_YEARS
        out["base_mean"] = b.mean(axis=1).where(enough)
        out["base_min"] = b.min(axis=1).where(enough)
        out["base_max"] = b.max(axis=1).where(enough)
    out["Date"] = pd.to_datetime([f"{LOCKDOWN_YEAR}-{m}" for m in out.index])
    return out.reset_index(drop=True)


def monthly_city(df: pd.DataFrame, coords: pd.DataFrame, pollutant: str = "AQI",
                 min_days: int = 10) -> pd.DataFrame:
    """Monthly mean per city (with coordinates) for the animated map."""
    d = df.dropna(subset=[pollutant]).copy()
    d["Month"] = d["Date"].dt.strftime("%Y-%m")
    g = d.groupby(["City", "Month"])[pollutant].agg(["mean", "count"]).reset_index()
    g = g[g["count"] >= min_days].rename(columns={"mean": pollutant})
    g = g.merge(coords, on="City", how="inner")
    return g.sort_values(["Month", "City"]).reset_index(drop=True)


def correlation(df: pd.DataFrame, cities=None) -> pd.DataFrame:
    cols = [c for c in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"] if c in df.columns]
    d = df if cities is None else df[df["City"].isin(cities)]
    return d[cols].corr()


def run_all(raw: pd.DataFrame):
    """Convenience: raw table -> (clean, coverage, stats, summary, kept_cities)."""
    df = clean(raw)
    stats = window_stats(df)
    cov = coverage_table(stats)
    kept = [c for c in cov.index[cov["keep"]] if c not in EXCLUDE_CITIES]
    cov.loc[cov.index.isin(EXCLUDE_CITIES), "keep"] = False
    summary = build_summary(stats)
    summary = summary[summary["City"].isin(kept)]
    return df, cov, stats, summary, kept
