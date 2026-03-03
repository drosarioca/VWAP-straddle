
import os
import sys
import pandas as pd
from datetime import date, time, datetime
from backtest_main import IChartsDataManager, get_atm_strike_at_time, ICHARTS_DIR, INDEX_DATA_PATH

def debug_loader():
    print("--- Debugging ICharts Loader ---")
    data_dir = ICHARTS_DIR
    print(f"Data Dir: {data_dir}")
    manager = IChartsDataManager(data_dir)
    
    target_date = date(2024, 7, 22)
    print(f"\nTarget Date: {target_date}")
    
    # 1. Check Index Data / ATM
    print("Checking ATM...")
    atm = get_atm_strike_at_time(target_date, time(9, 20), None)
    print(f"ATM at 9:20: {atm}")
    
    if atm:
        # 2. Check Straddle Load
        print(f"Loading Straddle for {atm}...")
        df = manager.load_straddle(target_date, atm)
        if df is not None:
            print("Straddle Loaded Successfully!")
            print(df.head())
            print(df.tail())
            print(f"Row count: {len(df)}")
        else:
            print("Failed to load straddle df.")
            
            # Check if file map has it
            expiry = manager.get_nearest_expiry(target_date)
            print(f"Nearest Expiry: {expiry}")
            if expiry:
                fpath = manager.file_map.get((expiry, atm))
                print(f"Expected File Path: {fpath}")
                if fpath and os.path.exists(fpath):
                    print("File exists on disk.")
                else:
                    print("File NOT found in map or disk.")
    else:
        print("Could not skip ATM step.")

if __name__ == "__main__":
    debug_loader()
