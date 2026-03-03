
import sys
import os
import pandas as pd
from datetime import date, time, datetime
sys.path.append(os.getcwd())
try:
    from backtest_main import load_index_data, OptionsLoader, construct_straddle, NIFTY_PATHS
except ImportError:
    # Fallback to local import style 
    sys.path.append(os.getcwd())
    from src.options_loader import OptionsLoader
    from backtest_main import NIFTY_PATHS, construct_straddle, load_index_data

target_date = date(2025, 2, 20)
strike = 22850

print(f"--- Diagnosing Entry Conditions for {target_date} Strike {strike} ---")
loader = OptionsLoader(NIFTY_PATHS)
straddle = construct_straddle(loader, target_date, target_date, strike)

if straddle is not None:
    # Analyze 10:28
    check_times = [time(10, 28), time(10, 29), time(10, 30), time(10, 31)]
    
    # We need VWAP values, so calculate them if not present? 
    # construct_straddle supposedly calculates 'VWAP'.
    
    print(f"\nData columns: {straddle.columns}")
    
    for t in check_times:
        print(f"\n--- Checking {t} ---")
        dt = datetime.combine(target_date, t)
        
        if dt not in straddle.index:
            print("Time not found in data.")
            continue
            
        idx_loc = straddle.index.get_loc(dt)
        if idx_loc < 5:
            print("Not enough history.")
            continue
            
        grp_a = straddle.iloc[idx_loc-5 : idx_loc-2]
        grp_b = straddle.iloc[idx_loc-2 : idx_loc+1]
        
        curr_close = straddle.loc[dt]['Close']
        curr_vwap = straddle.loc[dt]['VWAP'] # Assuming dynamic VWAP as no roll mentioned before 10:36
        
        cond1 = (grp_a['Close'] < grp_a['VWAP']).all()
        cond2 = (grp_b['Close'] < grp_b['VWAP']).all()
        
        low_a = grp_a['Low'].min()
        cond3 = curr_close < low_a
        
        print(f"Close: {curr_close:.2f}, VWAP: {curr_vwap:.2f}")
        print(f"GrpA ({-5} to {-3}):")
        print(grp_a[['Low', 'Close', 'VWAP']])
        print(f"Cond1 (All A < VWAP): {cond1}")
        
        print(f"GrpB ({-2} to {0}):")
        print(grp_b[['Low', 'Close', 'VWAP']])
        print(f"Cond2 (All B < VWAP): {cond2}")
        
        print(f"Low A: {low_a:.2f}")
        print(f"Cond3 (Close < Low A): {cond3}")
        
        if cond1 and cond2 and cond3:
            print(">>> ENTRY TRIGGER <<<")
        else:
            print(">>> NO ENTRY <<<")

else:
    print("Straddle not found.")
