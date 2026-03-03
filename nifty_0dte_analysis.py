"""
nifty_0dte_analysis.py
======================
Deep statistical analysis of Nifty expiry day (0 DTE) behaviour.
Produces summary statistics and exports CSV/Excel reports.

Usage:
    python nifty_0dte_analysis.py
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd

# Force UTF-8 stdout — prevents Windows cp1252 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

warnings.filterwarnings("ignore")

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results output")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Import loader (loads all expiry-day data)
# ─────────────────────────────────────────────────────────────────────────────
from nifty_expiry_loader import load_all_expiry_data


# ─────────────────────────────────────────────────────────────────────────────
# Helper: safe percentage
# ─────────────────────────────────────────────────────────────────────────────
def pct_of(series, condition):
    n = len(series.dropna())
    return round(condition.sum() / n * 100, 1) if n else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 1. Overall KPI summary
# ─────────────────────────────────────────────────────────────────────────────
def compute_kpis(df: pd.DataFrame) -> dict:
    spot = df[df["spot_open"].notna()].copy()
    kpis = {
        "total_expiry_days":       len(df),
        "days_with_spot_data":     len(spot),
        "years_covered":           sorted(df["year"].unique().tolist()),
        "pct_up_days":             pct_of(spot, spot["direction"] == "UP"),
        "pct_down_days":           pct_of(spot, spot["direction"] == "DOWN"),
        "avg_range_pct":           round(spot["day_range_pct"].mean(), 3),
        "median_range_pct":        round(spot["day_range_pct"].median(), 3),
        "std_range_pct":           round(spot["day_range_pct"].std(), 3),
        "max_range_pct":           round(spot["day_range_pct"].max(), 3),
        "min_range_pct":           round(spot["day_range_pct"].min(), 3),
        "avg_oc_move_pct":         round(spot["oc_move_pct"].mean(), 3),
        "std_oc_move_pct":         round(spot["oc_move_pct"].std(), 3),
        # Straddle stats (only where available)
    }
    strad = spot[spot["straddle_open"].notna()]
    if not strad.empty:
        kpis.update({
            "days_with_straddle_data":  len(strad),
            "avg_straddle_decay_pct":   round(strad["straddle_decay_pct"].mean(), 2),
            "median_straddle_decay_pct": round(strad["straddle_decay_pct"].median(), 2),
            "pct_straddle_decayed":     pct_of(strad, strad["straddle_decay_pts"] > 0),
        })
    return kpis


# ─────────────────────────────────────────────────────────────────────────────
# 2. Monthly seasonality table
# ─────────────────────────────────────────────────────────────────────────────
def compute_monthly_seasonality(df: pd.DataFrame) -> pd.DataFrame:
    spot = df[df["spot_open"].notna()].copy()
    tbl = spot.groupby("month_name").agg(
        count           = ("day_range_pct", "count"),
        avg_range_pct   = ("day_range_pct", "mean"),
        avg_oc_pct      = ("oc_move_pct",   "mean"),
        pct_up          = ("direction",     lambda x: (x == "UP").sum() / len(x) * 100),
        avg_straddle_decay = ("straddle_decay_pct", "mean"),
    ).round(3)
    # Re-order months
    month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    tbl = tbl.reindex([m for m in month_order if m in tbl.index])
    return tbl


# ─────────────────────────────────────────────────────────────────────────────
# 3. Year-over-year comparison
# ─────────────────────────────────────────────────────────────────────────────
def compute_yearly(df: pd.DataFrame) -> pd.DataFrame:
    spot = df[df["spot_open"].notna()].copy()
    tbl = spot.groupby("year").agg(
        count            = ("day_range_pct", "count"),
        avg_range_pct    = ("day_range_pct", "mean"),
        std_range_pct    = ("day_range_pct", "std"),
        max_range_pct    = ("day_range_pct", "max"),
        avg_oc_pct       = ("oc_move_pct",   "mean"),
        pct_up           = ("direction",      lambda x: (x == "UP").sum() / len(x) * 100),
        avg_straddle_decay = ("straddle_decay_pct", "mean"),
    ).round(3)
    return tbl


# ─────────────────────────────────────────────────────────────────────────────
# 4. Intraday composite path (avg price % from open at each hour)
# ─────────────────────────────────────────────────────────────────────────────
def compute_intraday_path(df: pd.DataFrame) -> pd.DataFrame:
    spot = df[df["spot_open"].notna()].copy()
    time_cols = ["spot_0915","spot_1000","spot_1100","spot_1200",
                 "spot_1300","spot_1400","spot_1500","spot_1529"]
    labels = ["09:15","10:00","11:00","12:00","13:00","14:00","15:00","15:29"]

    rows = []
    for col, lbl in zip(time_cols, labels):
        col_data = spot[col].dropna()
        rows.append({
            "time":   lbl,
            "avg_pct_from_open":    round(col_data.mean(), 3),
            "median_pct_from_open": round(col_data.median(), 3),
            "std_pct_from_open":    round(col_data.std(), 3),
            "pct_positive":         pct_of(col_data, col_data > 0),
            "pct_negative":         pct_of(col_data, col_data < 0),
        })
    return pd.DataFrame(rows).set_index("time")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Straddle decay by hour
# ─────────────────────────────────────────────────────────────────────────────
def compute_straddle_decay_curve(df: pd.DataFrame) -> pd.DataFrame:
    strad = df[df["straddle_open"].notna()].copy()
    strad_cols = ["straddle_0915","straddle_1000","straddle_1100","straddle_1200",
                  "straddle_1300","straddle_1400","straddle_1500"]
    labels = ["09:15","10:00","11:00","12:00","13:00","14:00","15:00"]

    rows = []
    for col, lbl in zip(strad_cols, labels):
        col_data = strad[col].dropna()
        if col_data.empty:
            continue
        open_data = strad.loc[col_data.index, "straddle_open"]
        pct_remain = ((col_data / open_data) * 100).dropna()
        rows.append({
            "time":                 lbl,
            "avg_straddle_value":   round(col_data.mean(), 2),
            "avg_pct_remaining":    round(pct_remain.mean(), 2),
            "median_pct_remaining": round(pct_remain.median(), 2),
        })
    return pd.DataFrame(rows).set_index("time")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Range distribution buckets
# ─────────────────────────────────────────────────────────────────────────────
def compute_range_distribution(df: pd.DataFrame) -> pd.DataFrame:
    spot = df[df["day_range_pct"].notna()].copy()
    bins  = [0, 0.3, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 100.0]
    labels = ["<0.3%","0.3-0.5%","0.5-0.75%","0.75-1.0%",
              "1.0-1.25%","1.25-1.5%","1.5-2.0%",">2.0%"]
    spot["range_bucket"] = pd.cut(spot["day_range_pct"], bins=bins, labels=labels, right=False)
    dist = spot["range_bucket"].value_counts().sort_index()
    dist_pct = (dist / dist.sum() * 100).round(1)
    return pd.DataFrame({"count": dist, "pct": dist_pct})


# ─────────────────────────────────────────────────────────────────────────────
# 7. High vs Low timing analysis
# ─────────────────────────────────────────────────────────────────────────────
def compute_hl_timing(df: pd.DataFrame) -> dict:
    spot = df[df["high_time"].notna() & df["low_time"].notna()].copy()
    pct_high_before_low = pct_of(spot, spot["high_before_low"] == True)

    # Count high/low by hour
    spot["high_hour"] = pd.to_datetime(spot["high_time"], format="%H:%M", errors="coerce").dt.hour
    spot["low_hour"]  = pd.to_datetime(spot["low_time"],  format="%H:%M", errors="coerce").dt.hour

    high_by_hour = spot["high_hour"].value_counts().sort_index().to_dict()
    low_by_hour  = spot["low_hour"].value_counts().sort_index().to_dict()

    return {
        "pct_high_before_low": pct_high_before_low,
        "pct_low_before_high": round(100 - pct_high_before_low, 1),
        "high_by_hour": high_by_hour,
        "low_by_hour":  low_by_hour,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. Weekday analysis (expiry day of week)
# ─────────────────────────────────────────────────────────────────────────────
def compute_weekday_stats(df: pd.DataFrame) -> pd.DataFrame:
    spot = df[df["spot_open"].notna()].copy()
    tbl = spot.groupby("weekday").agg(
        count         = ("day_range_pct", "count"),
        avg_range_pct = ("day_range_pct", "mean"),
        avg_oc_pct    = ("oc_move_pct",   "mean"),
        pct_up        = ("direction",     lambda x: (x == "UP").sum() / len(x) * 100),
    ).round(3)
    day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
    tbl = tbl.reindex([d for d in day_order if d in tbl.index])
    return tbl


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────
def run_analysis(years: list[int] | None = None, save_excel: bool = True) -> dict:
    """
    Run full analysis. Returns dict with all computed tables + raw DataFrame.
    """
    print("Loading expiry data...")
    df = load_all_expiry_data(years=years, verbose=True)

    print("\nRunning analysis modules...")
    results = {
        "raw_df":              df,
        "kpis":                compute_kpis(df),
        "monthly":             compute_monthly_seasonality(df),
        "yearly":              compute_yearly(df),
        "intraday_path":       compute_intraday_path(df),
        "straddle_decay":      compute_straddle_decay_curve(df),
        "range_distribution":  compute_range_distribution(df),
        "hl_timing":           compute_hl_timing(df),
        "weekday":             compute_weekday_stats(df),
    }

    # ── Print summary to console ─────────────────────────────────────────────
    print("\n" + "="*60)
    print("  NIFTY 0 DTE EXPIRY DAY - ANALYSIS SUMMARY")
    print("="*60)
    kpis = results["kpis"]
    print(f"  Expiry days analysed : {kpis['total_expiry_days']}")
    print(f"  With spot data       : {kpis['days_with_spot_data']}")
    print(f"  Years                : {kpis['years_covered']}")
    print(f"  Average daily range  : {kpis['avg_range_pct']:.3f}%")
    print(f"  Median daily range   : {kpis['median_range_pct']:.3f}%")
    print(f"  % Up days            : {kpis['pct_up_days']:.1f}%")
    print(f"  Avg OC move          : {kpis['avg_oc_move_pct']:.3f}%")
    if "avg_straddle_decay_pct" in kpis:
        print(f"  Avg straddle decay   : {kpis['avg_straddle_decay_pct']:.2f}%")
    print()
    print("Monthly seasonality:")
    print(results["monthly"].to_string())
    print()
    print("Year-over-Year:")
    print(results["yearly"].to_string())
    print()
    print("Intraday price path (avg % from open):")
    print(results["intraday_path"].to_string())
    print()
    print("Straddle decay curve:")
    print(results["straddle_decay"].to_string())
    print()
    print("High/Low timing:")
    hl = results["hl_timing"]
    print(f"  High forms before Low : {hl['pct_high_before_low']}% of days")
    print(f"  Low forms before High : {hl['pct_low_before_high']}% of days")

    # ── Save to Excel ─────────────────────────────────────────────────────────
    if save_excel:
        out_path = os.path.join(RESULTS_DIR, "nifty_0dte_analysis.xlsx")
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Raw Expiry Data", index=False)
            results["monthly"].to_excel(writer,    sheet_name="Monthly Seasonality")
            results["yearly"].to_excel(writer,     sheet_name="Year Overview")
            results["intraday_path"].to_excel(writer, sheet_name="Intraday Path")
            results["straddle_decay"].to_excel(writer, sheet_name="Straddle Decay")
            results["range_distribution"].to_excel(writer, sheet_name="Range Distribution")
            results["weekday"].to_excel(writer,    sheet_name="Weekday Stats")
        print(f"\n[SAVED] Excel report: {out_path}")

    return results


if __name__ == "__main__":
    run_analysis(years=None, save_excel=True)   # None = all available years
