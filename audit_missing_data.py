
import os
import json
import datetime
import pandas as pd
from backtest_main import run_day_analysis, IChartsDataManager, ICHARTS_DIR, INDEX_DATA_PATH, DATA_YEARS
from datetime import time

def audit_data():
    print(f"--- Starting Full Data Audit ---")
    print(f"Scanning years: {DATA_YEARS}")
    
    # 1. Get Date List
    spot_files = os.listdir(INDEX_DATA_PATH)
    dates = []
    for f in spot_files:
        if f.startswith("NIFTY-1minute-data-") and f.endswith(".csv"):
             ds = f.replace("NIFTY-1minute-data-", "").replace(".csv", "")
             try:
                 d = datetime.datetime.strptime(ds, "%Y-%m-%d").date()
                 if d.year in DATA_YEARS:
                     dates.append(d)
             except: pass
    dates = sorted(dates)
    print(f"Found {len(dates)} trading days to check.")

    missing_items = [] # List of {'Date': str, 'Strike': int, 'Reason': str}

    # Initialize Loader
    loader = IChartsDataManager(ICHARTS_DIR)
    
    for d in dates:
        # Run analysis in ROLLING mode to catch rolled strike gaps
        logs, df, trades = run_day_analysis(
            d,
            entry_window_mins=30,
            rolling_step=80,
            portfolio_sl=70,
            strategy_mode="ROLLING_VWAP", # Crucial to trigger rolls
            spot_check_time=time(9, 30)   # Default spot check
        )
        
        # Scan Logs
        for log in logs:
            if "FAILED TO LOAD" in log:
                # Format: [Time] ❌ FAILED TO LOAD NEW STRIKE {new_strike}. Staying on {current_strike}
                try:
                    parts = log.split("FAILED TO LOAD NEW STRIKE ")
                    strike_part = parts[1].split(".")[0]
                    strike = int(strike_part)
                    missing_items.append({
                        'Date': d.strftime("%Y-%m-%d"),
                        'Type': 'Rolled Strike',
                        'Strike': strike,
                        'Log': log
                    })
                except:
                    print(f"Error parsing log: {log}")
                    
            elif "No Straddle Data for" in log:
                # Format: No Straddle Data for {current_strike}
                try:
                    parts = log.split("No Straddle Data for ")
                    strike = int(parts[1])
                    missing_items.append({
                        'Date': d.strftime("%Y-%m-%d"),
                        'Type': 'Initial Strike',
                        'Strike': strike,
                        'Log': log
                    })
                except: pass

            elif "Missing Straddle" in log:
                 # Format: Missing Straddle {current_strike}
                try:
                    parts = log.split("Missing Straddle ")
                    strike = int(parts[1])
                    missing_items.append({
                        'Date': d.strftime("%Y-%m-%d"),
                        'Type': 'Initial Strike',
                        'Strike': strike,
                        'Log': log
                    })
                except: pass

    # Report
    print(f"\n--- Audit Complete ---")
    if missing_items:
        print(f"Found {len(missing_items)} missing data points.")
        
        # Deduplicate
        unique_missing = []
        seen = set()
        for item in missing_items:
            key = (item['Date'], item['Strike'])
            if key not in seen:
                seen.add(key)
                unique_missing.append(item)
        
        print(f"Unique gaps to recover: {len(unique_missing)}")
        for m in unique_missing:
            print(f"  [{m['Date']}] Missing {m['Type']}: {m['Strike']}")
            
        with open("missing_data_report.json", "w") as f:
            json.dump(unique_missing, f, indent=4)
        print("Drafted 'missing_data_report.json'")
    else:
        print("No missing data found! All strikes loaded successfully.")

if __name__ == "__main__":
    audit_data()
