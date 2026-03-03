"""
nifty_expiry_loader.py
======================
Loads and merges Nifty spot 1-min OHLC data with ATM straddle data
for all 0 DTE (expiry) days derived from the icharts_download/ filenames.

Spot data format (per file): date, time, open, high, low, close
Straddle file naming:        NIFTY_DDMMMYY_STRIKE_Straddle.csv
"""

import os
import re
import sys
import glob
import pandas as pd
from datetime import datetime, date
from collections import defaultdict

# Force UTF-8 stdout — prevents Windows cp1252 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
STRADDLE_DIR   = os.path.join(BASE_DIR, "icharts_download")
SPOT_DIR       = os.path.join(BASE_DIR, "nifty_spot_data")

# ─── 1.  Extract all 0 DTE dates from straddle filenames ─────────────────────
MONTH_MAP = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}

def parse_expiry_date(filename: str) -> date | None:
    """
    Parse expiry date from e.g. NIFTY_04JAN24_21000_Straddle.csv
    Returns a datetime.date or None if unparseable.
    """
    m = re.match(r"NIFTY_(\d{2})([A-Z]{3})(\d{2})_", os.path.basename(filename))
    if not m:
        return None
    day, mon, yr = m.group(1), m.group(2), m.group(3)
    try:
        return datetime.strptime(f"{day}-{MONTH_MAP[mon]}-20{yr}", "%d-%m-%Y").date()
    except (KeyError, ValueError):
        return None


def get_all_expiry_dates() -> list[date]:
    """Return sorted list of all 0 DTE dates found in straddle filenames."""
    files = glob.glob(os.path.join(STRADDLE_DIR, "NIFTY_*_Straddle.csv"))
    dates = set()
    for f in files:
        d = parse_expiry_date(f)
        if d:
            dates.add(d)
    return sorted(dates)


# ─── 2.  Group straddle files by expiry date  ─────────────────────────────────
def get_straddle_files_by_date() -> dict[date, list[tuple[int, str]]]:
    """
    Returns {expiry_date: [(strike, filepath), ...]} sorted by strike.
    """
    files = glob.glob(os.path.join(STRADDLE_DIR, "NIFTY_*_Straddle.csv"))
    by_date: dict[date, list[tuple[int, str]]] = defaultdict(list)
    for f in files:
        exp = parse_expiry_date(f)
        if exp is None:
            continue
        m = re.match(r"NIFTY_\d{2}[A-Z]{3}\d{2}_(\d+)_Straddle", os.path.basename(f))
        if m:
            strike = int(m.group(1))
            by_date[exp].append((strike, f))
    # sort each list by strike
    for exp in by_date:
        by_date[exp].sort()
    return dict(by_date)


# ─── 3.  Load spot 1-min data for a single date ───────────────────────────────
def load_spot_day(expiry_date: date) -> pd.DataFrame | None:
    """
    Load Nifty spot 1-min OHLC for a given date.
    Expected file: nifty_spot_data/NIFTY-1minute-data-YYYY-MM-DD.csv
    Columns: date, time, open, high, low, close
    """
    fname = f"NIFTY-1minute-data-{expiry_date.strftime('%Y-%m-%d')}.csv"
    fpath = os.path.join(SPOT_DIR, fname)
    if not os.path.exists(fpath):
        return None
    df = pd.read_csv(fpath)
    df.columns = [c.strip().lower() for c in df.columns]
    df["datetime"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
    df = df.set_index("datetime").sort_index()
    df = df[["open", "high", "low", "close"]].astype(float)
    return df


# ─── 4.  Find ATM strike for a given expiry date using spot open  ─────────────
def find_atm_strike(expiry_date: date,
                    straddle_map: dict,
                    spot_df: pd.DataFrame,
                    tick: int = 50) -> int | None:
    """
    ATM strike = nearest multiple of `tick` to spot open price.
    Falls back to the strike with highest average volume if spot is missing.
    """
    strikes_available = [s for s, _ in straddle_map.get(expiry_date, [])]
    if not strikes_available:
        return None

    if spot_df is not None and not spot_df.empty:
        spot_open = float(spot_df["open"].iloc[0])
        atm = round(spot_open / tick) * tick
        # find closest available strike
        closest = min(strikes_available, key=lambda s: abs(s - atm))
        return closest

    # fallback: pick median strike
    return sorted(strikes_available)[len(strikes_available) // 2]


# ─── 5.  Load one straddle CSV for a given expiry date & strike ───────────────
def load_straddle_day(expiry_date: date, strike: int, straddle_map: dict) -> pd.DataFrame | None:
    """
    Load straddle minute data for a given expiry + strike.
    Only returns rows from the expiry date itself (0 DTE).
    Columns: open, high, low, close, volume
    """
    strike_files = {s: f for s, f in straddle_map.get(expiry_date, [])}
    if strike not in strike_files:
        return None
    fpath = strike_files[strike]
    df = pd.read_csv(fpath)
    df.columns = [c.strip().lower() for c in df.columns]

    # parse datetime
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    elif "timestamp" in df.columns:
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s") + pd.Timedelta(hours=5, minutes=30)
    else:
        return None

    df = df.set_index("datetime").sort_index()

    # filter to only the expiry date
    df = df[df.index.date == expiry_date]
    if df.empty:
        return None

    cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    return df[cols].astype(float)


# ─── 6.  Build full day record  ────────────────────────────────────────────────
def build_expiry_record(expiry_date: date,
                        spot_df: pd.DataFrame | None,
                        straddle_df: pd.DataFrame | None,
                        atm_strike: int | None) -> dict:
    """
    Compute per-expiry-day statistics from spot + straddle dataframes.
    """
    record = {
        "date":         str(expiry_date),
        "year":         expiry_date.year,
        "month":        expiry_date.month,
        "month_name":   expiry_date.strftime("%b"),
        "weekday":      expiry_date.strftime("%A"),
        "atm_strike":   atm_strike,
    }

    # ── Spot stats ──────────────────────────────────────────────────────────
    if spot_df is not None and not spot_df.empty:
        spot_open  = float(spot_df["open"].iloc[0])
        spot_close = float(spot_df["close"].iloc[-1])
        spot_high  = float(spot_df["high"].max())
        spot_low   = float(spot_df["low"].min())
        day_range  = spot_high - spot_low
        oc_move    = spot_close - spot_open

        record.update({
            "spot_open":       round(spot_open, 2),
            "spot_close":      round(spot_close, 2),
            "spot_high":       round(spot_high, 2),
            "spot_low":        round(spot_low, 2),
            "day_range_pts":   round(day_range, 2),
            "day_range_pct":   round(day_range / spot_open * 100, 3),
            "oc_move_pts":     round(oc_move, 2),
            "oc_move_pct":     round(oc_move / spot_open * 100, 3),
            "direction":       "UP" if oc_move >= 0 else "DOWN",
            "spot_rows":       len(spot_df),
        })

        # Time-of-day normalized prices (spot price at key hours)
        # Includes :00 markers for intraday path + :15 boundaries for hourly-slot heatmap
        for hh, mm in [(9, 15), (10, 0), (10, 15), (11, 0), (11, 15),
                       (12, 0), (12, 15), (13, 0), (13, 15),
                       (14, 0), (14, 15), (15, 0), (15, 15), (15, 29)]:
            ts_label = f"spot_{hh:02d}{mm:02d}"
            t_end = mm + 1 if mm < 58 else mm
            window = spot_df.between_time(f"{hh:02d}:{mm:02d}", f"{hh:02d}:{t_end:02d}")
            if not window.empty:
                val = float(window["close"].iloc[-1])
                record[ts_label] = round((val - spot_open) / spot_open * 100, 3)
            else:
                record[ts_label] = None

        # When was high / low formed (approximate)
        high_idx = spot_df["high"].idxmax()
        low_idx  = spot_df["low"].idxmin()
        record["high_time"] = high_idx.strftime("%H:%M") if pd.notna(high_idx) else None
        record["low_time"]  = low_idx.strftime("%H:%M")  if pd.notna(low_idx)  else None
        record["high_before_low"] = (high_idx < low_idx) if (pd.notna(high_idx) and pd.notna(low_idx)) else None

    else:
        record.update({
            "spot_open": None, "spot_close": None, "spot_high": None, "spot_low": None,
            "day_range_pts": None, "day_range_pct": None,
            "oc_move_pts": None, "oc_move_pct": None,
            "direction": None, "spot_rows": 0,
            "high_time": None, "low_time": None, "high_before_low": None,
        })
        for hh, mm in [(9, 15), (10, 0), (10, 15), (11, 0), (11, 15),
                       (12, 0), (12, 15), (13, 0), (13, 15),
                       (14, 0), (14, 15), (15, 0), (15, 15), (15, 29)]:
            record[f"spot_{hh:02d}{mm:02d}"] = None

    # ── Straddle / ATM stats ─────────────────────────────────────────────────
    if straddle_df is not None and not straddle_df.empty:
        s_open  = float(straddle_df["open"].iloc[0])
        s_close = float(straddle_df["close"].iloc[-1])
        s_high  = float(straddle_df["high"].max()) if "high" in straddle_df.columns else None
        decay   = s_open - s_close

        record.update({
            "straddle_open":       round(s_open, 2),
            "straddle_close":      round(s_close, 2),
            "straddle_high":       round(s_high, 2) if s_high else None,
            "straddle_decay_pts":  round(decay, 2),
            "straddle_decay_pct":  round(decay / s_open * 100, 2) if s_open else None,
            "straddle_rows":       len(straddle_df),
        })

        # Straddle price at key hours (absolute)
        for hh, mm in [(9, 15), (10, 0), (11, 0), (12, 0), (13, 0), (14, 0), (15, 0)]:
            ts_label = f"straddle_{hh:02d}{mm:02d}"
            window = straddle_df.between_time(f"{hh:02d}:{mm:02d}", f"{hh:02d}:{mm+1 if mm < 59 else mm:02d}")
            record[ts_label] = round(float(window["close"].iloc[-1]), 2) if not window.empty else None
    else:
        record.update({
            "straddle_open": None, "straddle_close": None, "straddle_high": None,
            "straddle_decay_pts": None, "straddle_decay_pct": None, "straddle_rows": 0,
        })
        for hh, mm in [(9, 15), (10, 0), (11, 0), (12, 0), (13, 0), (14, 0), (15, 0)]:
            record[f"straddle_{hh:02d}{mm:02d}"] = None

    return record


# ─── 7.  Load all expiry days → DataFrame  ────────────────────────────────────
def load_all_expiry_data(years: list[int] | None = None,
                         verbose: bool = True) -> pd.DataFrame:
    """
    Main entry point. Returns DataFrame with one row per 0 DTE expiry day.
    years: filter to specific years e.g. [2021,2022,2023,2024,2025]
    """
    expiry_dates = get_all_expiry_dates()
    straddle_map = get_straddle_files_by_date()

    if years:
        expiry_dates = [d for d in expiry_dates if d.year in years]

    records = []
    missing_spot = []

    for i, exp_date in enumerate(expiry_dates):
        spot_df     = load_spot_day(exp_date)
        atm_strike  = find_atm_strike(exp_date, straddle_map, spot_df)
        straddle_df = load_straddle_day(exp_date, atm_strike, straddle_map) if atm_strike else None

        if spot_df is None:
            missing_spot.append(str(exp_date))

        rec = build_expiry_record(exp_date, spot_df, straddle_df, atm_strike)
        records.append(rec)

        if verbose and (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{len(expiry_dates)} expiry days...")

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    if verbose:
        print(f"\n[OK] Loaded {len(df)} expiry days")
        print(f"   Years: {sorted(df['year'].unique().tolist())}")
        print(f"   Spot data missing for {len(missing_spot)} dates")
        if missing_spot[:5]:
            print(f"   First few missing: {missing_spot[:5]}")
        print(f"\nSample row:\n{df.iloc[-1].to_dict()}\n")

    return df


# ─── CLI quick-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Nifty 0 DTE Expiry Loader - Quick Test")
    print("=" * 60)

    # Show how many expiry dates found
    all_dates = get_all_expiry_dates()
    print(f"\nTotal 0 DTE dates found in straddle files: {len(all_dates)}")
    by_year: dict[int, int] = defaultdict(int)
    for d in all_dates:
        by_year[d.year] += 1
    for yr, cnt in sorted(by_year.items()):
        print(f"  {yr}: {cnt} expiry days")

    # Load last 2 years for a quick test
    print("\nLoading 2024–2025 data for quick test...")
    df = load_all_expiry_data(years=[2024, 2025], verbose=True)

    # Save for inspection
    out = os.path.join(BASE_DIR, "results output", "expiry_data_quick_test.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\n[SAVED] {out}")
