
import os
import pandas as pd
from datetime import datetime, timedelta
# Reuse existing extraction logic
from download_icharts import get_expiries_from_html

# Paths
INDEX_DATA_PATH = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\NIFTY-index-data"
ICHARTS_DIR = r"c:\Users\Rosario\.gemini\antigravity\scratch\quant_trading\icharts_download"

def verify_all():
    print("--- VERIFYING ALL 2024-2025 EXPIRIES ---")
    
    # 1. Get Source Truth from HTML
    all_expiries = get_expiries_from_html() # returns ['02JAN25', ...]
    
    # Filter 2024/2025
    targets = []
    for e in all_expiries:
        if e.endswith("24") or e.endswith("25"):
            targets.append(e)
            
    # Sort
    targets.sort(key=lambda x: datetime.strptime(x, "%d%b%y"))
    print(f"Source Truth: Found {len(targets)} expiries in HTML for 2024/2025.")
    
    missing_tasks = []
    
    for exp_str in targets:
        # Convert to Date object
        exp_date = datetime.strptime(exp_str, "%d%b%y").date()
        date_iso = exp_date.strftime("%Y-%m-%d")
        
        # 2. Get Spot Price for this Date from Index Data
        spot_file = os.path.join(INDEX_DATA_PATH, f"NIFTY-1minute-data-{date_iso}.csv")
        
        if not os.path.exists(spot_file):
            print(f"[WARN] No Index Data for {exp_str} ({date_iso}). Cannot calc ATM.")
            # If we don't have index data, we can't backtest anyway, but let's log it.
            continue
            
        try:
            # Read first chunk to find ~09:20 price
            df = pd.read_csv(spot_file, nrows=50)
            spot_price = 0
            
            # Locate 09:20 or close
            # Assuming format: date,time,open,high,low,close
            # time usually "09:15:00"
            
            if 'time' in df.columns:
                 row = df[df['time'] >= '09:20:00']
                 if not row.empty:
                     spot_price = row.iloc[0]['close']
                 else:
                     spot_price = df.iloc[-1]['close'] # Fallback
            else:
                 # Fallback by index
                 spot_price = df.iloc[5]['close'] if len(df) > 5 else df.iloc[-1]['close']
                 
            # 3. Calculate ATM
            atm_strike = round(spot_price / 50) * 50
            
            # 4. Check File Existence
            # NIFTY_07OCT25_25100_Straddle.csv
            fname = f"NIFTY_{exp_str}_{atm_strike}_Straddle.csv"
            fpath = os.path.join(ICHARTS_DIR, fname)
            
            if not os.path.exists(fpath):
                print(f"[MISSING] {exp_str}: Spot {spot_price} -> ATM {atm_strike}")
                missing_tasks.append((exp_str, atm_strike))
                
        except Exception as e:
            print(f"Error processing {exp_str}: {e}")
            
    print(f"\n--- RESULTS ---")
    print(f"Total Missing files: {len(missing_tasks)}")
    print(missing_tasks)
    
    # Save to CSV for the downloader
    with open("final_missing.csv", "w") as f:
        for t in missing_tasks:
            f.write(f"{t[0]},{t[1]}\n")

if __name__ == "__main__":
    verify_all()
