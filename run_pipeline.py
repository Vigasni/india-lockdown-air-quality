"""One command to run the whole analysis:  python run_pipeline.py

Reads  data/city_day.csv
Writes outputs/*.csv  (coverage, summary, pause-or-fix tables)
       figures/*.png  (static figures for your report)
and prints the key findings to the terminal.
"""
import sys

import pandas as pd

from src import analysis, static_figures
from src.common import BASELINE_YEARS, MIN_COVERAGE, OUTPUT_DIR


def main():
    path = analysis.find_data_file()
    if path is None:
        sys.exit("Could not find city_day.csv in the data/ folder.\n"
                 "Download it from Kaggle (Air Quality Data in India) and put it there.")
    print(f"Reading {path.name} ...")
    raw = analysis.load_raw(path)
    print(f"  {len(raw):,} rows, {raw['City'].nunique()} cities, "
          f"{raw['Date'].min().date()} to {raw['Date'].max().date()}")

    df, cov, stats, summary, kept = analysis.run_all(raw)
    dropped = [c for c in cov.index if c not in kept]
    print(f"\nCoverage rule: >= {MIN_COVERAGE:.0%} of days in the lockdown window for 2020 "
          f"and for at least 2 of {BASELINE_YEARS}.")
    print(f"  Kept {len(kept)} cities: {', '.join(kept)}")
    print(f"  Dropped {len(dropped)}: {', '.join(dropped) if dropped else '-'}")
    if len(kept) < 3:
        sys.exit("Too few cities pass the coverage rule. Check your data file.")

    OUTPUT_DIR.mkdir(exist_ok=True)
    cov.to_csv(OUTPUT_DIR / "coverage.csv")
    summary.to_csv(OUTPUT_DIR / "summary.csv", index=False)
    pf = analysis.pause_or_fix(summary, "AQI")
    pf.to_csv(OUTPUT_DIR / "pause_or_fix_AQI.csv", index=False)

    print("\n=== Lockdown vs same dates in 2017-2019 (% change) ===")
    for pol in ["AQI", "PM2.5", "PM10", "NO2"]:
        h = analysis.headline(summary, pol)
        if h:
            print(f"{pol:6s} median {h['median']:+.0f}%  | best {h['best_city']} {h['best']:+.0f}%"
                  f"  | worst {h['worst_city']} {h['worst']:+.0f}%  "
                  f"| {h['n_improved']}/{h['n_cities']} cities cleaner")

    print("\n=== Pause or fix? (AQI) ===")
    print(pf[["City", "pct_lockdown", "pct_june", "verdict"]]
          .round(1).to_string(index=False))

    files = static_figures.make_all(df, summary, kept)
    print("\nSaved:")
    for f in files:
        print("  ", f.relative_to(f.parents[1]))
    print("  outputs/coverage.csv, outputs/summary.csv, outputs/pause_or_fix_AQI.csv")


if __name__ == "__main__":
    pd.options.display.width = 140
    main()
