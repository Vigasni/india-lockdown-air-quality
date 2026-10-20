"""Interactive Plotly charts (used by the Streamlit app and notebooks).

Design rules followed here: two series colours only (blue = normal years,
orange = 2020), blue-red diverging scale for correlations, thin lines, soft
grid, legends on, and titles that state what the chart is about.
Backgrounds are transparent so charts work in light and dark themes.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .common import (
    BASELINE_YEARS, BLUE, BLUE_RAMP, DIVERGING, GRAY, LOCKDOWN_YEAR, ORANGE,
    POLLUTANT_NAMES, WINDOWS, WINDOW_LABELS,
)

GRID = "rgba(128,128,128,0.25)"
BASELINE_LABEL = f"{BASELINE_YEARS[0]}-{BASELINE_YEARS[-1]} average"


def _style(fig: go.Figure, height: int | None = None) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        title=dict(x=0, xanchor="left"),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    if height:
        fig.update_layout(height=height)
    return fig


def _label(pollutant: str) -> str:
    return POLLUTANT_NAMES.get(pollutant, pollutant)


# 1 ---------------------------------------------------------------------------
def baseline_vs_2020(curve: pd.DataFrame, city: str, pollutant: str,
                     title: str | None = None) -> go.Figure:
    """2020 against the range of normal years, with the lockdown window shaded."""
    fig = go.Figure()
    if "base_min" in curve:
        fig.add_trace(go.Scatter(x=curve["Date"], y=curve["base_max"], mode="lines",
                                 line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=curve["Date"], y=curve["base_min"], mode="lines",
                                 line=dict(width=0), fill="tonexty",
                                 fillcolor="rgba(42,120,214,0.15)",
                                 name=f"{BASELINE_YEARS[0]}-{BASELINE_YEARS[-1]} range",
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=curve["Date"], y=curve["base_mean"], mode="lines",
                                 line=dict(color=BLUE, width=2), name=BASELINE_LABEL,
                                 hovertemplate="%{y:.0f}"))
    fig.add_trace(go.Scatter(x=curve["Date"], y=curve["y2020"], mode="lines",
                             line=dict(color=ORANGE, width=2), name=str(LOCKDOWN_YEAR),
                             hovertemplate="%{y:.0f}"))
    start, end = WINDOWS["lockdown"]
    x0, x1 = f"{LOCKDOWN_YEAR}-{start}", f"{LOCKDOWN_YEAR}-{end}"
    fig.add_shape(type="rect", xref="x", yref="paper", x0=x0, x1=x1, y0=0, y1=1,
                  fillcolor="rgba(128,128,128,0.14)", line_width=0, layer="below")
    fig.add_annotation(x=x0, y=1, yref="paper", text="Lockdown", showarrow=False,
                       xanchor="left", yanchor="top", font=dict(color=GRAY, size=12))
    fig.update_layout(title=title or f"{city}: {_label(pollutant)} in 2020 vs normal years",
                      hovermode="x unified", xaxis_tickformat="%d %b",
                      yaxis_title=_label(pollutant))
    return _style(fig, 430)


# 2 ---------------------------------------------------------------------------
def dumbbell(summary: pd.DataFrame, pollutant: str, window: str = "lockdown",
             highlight: str | None = None) -> go.Figure:
    """Baseline vs 2020 for every city, ordered by size of the change."""
    s = summary[(summary["Pollutant"] == pollutant) & (summary["window"] == window)]
    s = s.sort_values("pct_change").reset_index(drop=True)
    cities = s["City"].tolist()
    fig = go.Figure()
    xs, ys = [], []
    for _, r in s.iterrows():
        xs += [r["baseline"], r["y2020"], None]
        ys += [r["City"], r["City"], None]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=GRAY, width=2),
                             hoverinfo="skip", showlegend=False))
    custom = s[["pct_change"]].values
    fig.add_trace(go.Scatter(
        x=s["baseline"], y=s["City"], mode="markers", name=BASELINE_LABEL,
        marker=dict(color=BLUE, size=11, line=dict(color="white", width=1.5)),
        customdata=custom, hovertemplate="%{y}<br>Normal years: %{x:.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=s["y2020"], y=s["City"], mode="markers", name=str(LOCKDOWN_YEAR),
        marker=dict(color=ORANGE, size=11, line=dict(color="white", width=1.5)),
        customdata=custom,
        hovertemplate="%{y}<br>2020: %{x:.0f}<br>Change: %{customdata[0]:+.0f}%<extra></extra>"))
    fig.update_layout(
        title=f"{_label(pollutant)}: {WINDOW_LABELS[window]} vs {BASELINE_LABEL}",
        xaxis_title=_label(pollutant), hovermode="closest",
        yaxis=dict(categoryorder="array", categoryarray=cities, autorange="reversed"))
    return _style(fig, max(320, 26 * len(cities) + 150))


# 3 ---------------------------------------------------------------------------
def pause_or_fix_bars(pf: pd.DataFrame, pollutant: str) -> go.Figure:
    """% change vs baseline: during lockdown and in June. Closer to 0 = bounced back."""
    pf = pf.sort_values("pct_lockdown")
    cities = pf["City"].tolist()
    fig = go.Figure()
    fig.add_trace(go.Bar(y=pf["City"], x=pf["pct_lockdown"], orientation="h",
                         name=WINDOW_LABELS["lockdown"], marker_color=BLUE,
                         hovertemplate="%{y}<br>Lockdown: %{x:+.0f}%<extra></extra>"))
    fig.add_trace(go.Bar(y=pf["City"], x=pf["pct_june"], orientation="h",
                         name=WINDOW_LABELS["june"], marker_color=ORANGE,
                         hovertemplate="%{y}<br>June: %{x:+.0f}%<extra></extra>"))
    fig.add_vline(x=0, line_color=GRAY, line_width=1)
    fig.update_layout(
        title=f"{_label(pollutant)}: change vs normal years (below 0 = cleaner than usual)",
        barmode="group", bargap=0.25, bargroupgap=0.08,
        xaxis_title="% change vs 2017-2019 same dates", xaxis_ticksuffix="%",
        yaxis=dict(categoryorder="array", categoryarray=cities, autorange="reversed"))
    return _style(fig, max(360, 38 * len(cities) + 150))


# 4 ---------------------------------------------------------------------------
def animated_map(monthly: pd.DataFrame, pollutant: str = "AQI") -> go.Figure:
    """Bubble map of India with a month slider."""
    d = monthly.dropna(subset=[pollutant])
    fig = px.scatter_geo(
        d, lat="lat", lon="lon", size=pollutant, color=pollutant,
        hover_name="City", animation_frame="Month", size_max=34,
        range_color=(0, 400), color_continuous_scale=BLUE_RAMP,
        projection="natural earth", hover_data={"lat": False, "lon": False,
                                                 pollutant: ":.0f", "Month": False},
        title=f"Monthly average {_label(pollutant)} by city")
    fig.update_geos(
        lataxis_range=[6, 37], lonaxis_range=[67, 98], showcountries=True,
        countrycolor="rgba(128,128,128,0.5)", showland=True,
        landcolor="rgba(128,128,128,0.12)", showocean=False, showlakes=False,
        bgcolor="rgba(0,0,0,0)", coastlinecolor="rgba(128,128,128,0.5)")
    fig.update_layout(coloraxis_colorbar=dict(title=pollutant, thickness=12))
    _style(fig, 560)
    fig.update_layout(margin=dict(l=0, r=0, t=60, b=0))
    return fig


# 5 ---------------------------------------------------------------------------
def correlation_heatmap(corr: pd.DataFrame, title: str = "How pollutants move together") -> go.Figure:
    fig = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, aspect="auto",
                    color_continuous_scale=DIVERGING)
    fig.update_layout(title=title, coloraxis_colorbar=dict(title="r", thickness=12))
    return _style(fig, 460)
