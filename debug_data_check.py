
import sys
import os
import pandas as pd
from datetime import date, time
sys.path.append(os.getcwd())
try:
    from backtest_main import load_index_data, OptionsLoader, construct_straddle, NIFTY_PATHS
except ImportError:
    # Fallback to local import style if needed
    sys.path.append(os.getcwd())
    from src.options_loader import OptionsLoader
    from backtest_main import NIFTY_PATHS, construct_straddle, load_index_data

target_date = date(2025, 2, 20)
strike = 22900

print(f"--- Checking Data for {target_date} Strike {strike} ---")
loader = OptionsLoader(NIFTY_PATHS)
straddle = construct_straddle(loader, target_date, target_date, strike)

if straddle is not None:
    # Filter 9:16 to 10:36
    mask = (straddle.index.time >= time(9, 16)) & (straddle.index.time <= time(10, 36))
    subset = straddle[mask]
    
    min_low = subset['Low'].min()
    min_low_idx = subset['Low'].idxmin()
    
    print(f"Min Low in window (9:16-10:36): {min_low} at {min_low_idx}")
    print("Head of data:")
    print(subset[['Open','High','Low','Close']].head(10))
    print("Around Min Low:")
    print(subset.loc[min_low_idx - pd.Timedelta(minutes=2) : min_low_idx + pd.Timedelta(minutes=2)][['Low']])
else:
    print("Straddle not found.")
