"""Shared settings for the project.

Everything you might want to tweak (dates, thresholds, colours) lives here, so
the analysis, the charts and the Streamlit app always agree with each other.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = ROOT / "figures"
COORDS_FILE = DATA_DIR / "city_coords.csv"

# ---- Analysis settings -----------------------------------------------------
# Lockdown window (India's nationwide lockdown phases 1-4, inclusive).
# The window is given as "MM-DD" so the same calendar dates can be compared
# in other years (this removes the seasonal effect from the comparison).
WINDOWS = {
    "lockdown": ("03-25", "05-31"),   # 68 days
    "june": ("06-01", "06-30"),       # first month after the lockdown
}
WINDOW_LABELS = {
    "lockdown": "Lockdown (25 Mar - 31 May)",
    "june": "June (rebound)",
}
LOCKDOWN_YEAR = 2020
BASELINE_YEARS = [2017, 2018, 2019]

# A city-year only counts if at least this share of the window's days has data.
MIN_COVERAGE = 0.60
# A city needs this many valid baseline years to be compared fairly.
MIN_BASELINE_YEARS = 2
# Gaps of up to this many consecutive days are filled by interpolation.
MAX_GAP_DAYS = 3
EXCLUDE_CITIES = ["Ahmedabad"]   # AQI values above 500 (impossible) in every year

POLLUTANTS = ["AQI", "PM2.5", "PM10", "NO2"]
CORR_COLUMNS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]
NUMERIC_COLUMNS = ["PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "CO", "SO2",
                   "O3", "Benzene", "Toluene", "Xylene", "AQI"]

POLLUTANT_NAMES = {
    "AQI": "AQI",
    "PM2.5": "PM2.5 (µg/m³)",
    "PM10": "PM10 (µg/m³)",
    "NO2": "NO₂ (µg/m³)",
}

# ---- Colours (validated categorical pair + diverging pair) -------------------
BLUE = "#2a78d6"      # baseline / "normal" years
ORANGE = "#eb6834"    # 2020 / June
RED = "#e34948"
GRAY = "#8a8985"
LIGHT_GRAY = "#f0efec"
BLUE_RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
DIVERGING = [BLUE, LIGHT_GRAY, RED]
