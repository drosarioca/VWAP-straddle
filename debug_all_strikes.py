
import os
import pandas as pd
from datetime import datetime, timedelta

# Paths
INDEX_DATA_PATH = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\NIFTY-index-data"
ICHARTS_DIR = r"c:\Users\Rosario\.gemini\antigravity\scratch\quant_trading\icharts_download"

def scan_all_missing_atms():
    print("--- Scanning for Missing ATM Data (2024-2025) ---")
    
    # 1. Identify all unique expiry dates from existing files
    # We scan the folder to find "groups" of files for each expiry
    expiry_map = {} # date -> set of existing strikes
    
    files = os.listdir(ICHARTS_DIR)
    print(f"Scanning {len(files)} files in {ICHARTS_DIR}...")
    
    for fname in files:
        if fname.startswith("NIFTY_") and fname.endswith("_Straddle.csv"):
            try:
                # NIFTY_07OCT25_25100_Straddle.csv
                parts = fname.split("_")
                exp_str = parts[1]
                strike = int(parts[2])
                
                exp_date = datetime.strptime(exp_str, "%d%b%y").date()
                if exp_date.year not in [2024, 2025]:
                    continue
                    
                if exp_date not in expiry_map:
                    expiry_map[exp_date] = set()
                expiry_map[exp_date].add(strike)
            except:
                pass
                
    sorted_dates = sorted(expiry_map.keys())
    print(f"Found {len(sorted_dates)} expiry dates in 2024-2025.")
    
    missing_list = []
    
    # 2. Check each date
    for d in sorted_dates:
        # Load Spot Data
        spot_fname = f"NIFTY-1minute-data-{d}.csv"
        spot_path = os.path.join(INDEX_DATA_PATH, spot_fname)
        
        if not os.path.exists(spot_path):
            print(f"[WARN] No Spot Data for Expiry {d}")
            continue
            
        try:
            # We only need the open/close around 9:20-9:30 to determine ATM
            # Let's read first 50 lines to be fast
            df = pd.read_csv(spot_path, nrows=50)
            
            # Find 09:30 candle or similar
            # If 'time' column exists
            target_row = None
            if 'time' in df.columns:
                 # Standard format
                 target_row = df[df['time'] == '09:30:00']
            
            spot_price = 0
            if target_row is not None and not target_row.empty:
                spot_price = target_row.iloc[0]['close']
            else:
                # Fallback to roughly 15th candle (09:15 -> 09:30)
                if len(df) > 15:
                    spot_price = df.iloc[15]['close']
                else:
                    spot_price = df.iloc[-1]['close'] # Take whatever we have
            
            if spot_price == 0:
                print(f"[WARN] Could not determine spot price for {d}")
                continue
                
            # Calculate ATM
            atm_strike = round(spot_price / 50) * 50
            
            # Check if we have it
            existing_strikes = expiry_map[d]
            
            if atm_strike not in existing_strikes:
                print(f"[MISSING] {d.strftime('%d%b%y').upper()}: Spot {spot_price} -> ATM {atm_strike} missing.")
                missing_list.append((d.strftime('%d%b%y').upper(), atm_strike))
            # else:
            #     print(f"[OK] {d}: Found ATM {atm_strike}")

        except Exception as e:
            print(f"Error checking {d}: {e}")

    print(f"\nTotal Missing files: {len(missing_list)}")
    print(missing_list)
    
    # Save list to file for the downloader
    with open("missing_tasks.csv", "w") as f:
        for item in missing_list:
            f.write(f"{item[0]},{item[1]}\n")
    print("Saved missing list to 'missing_tasks.csv'")

if __name__ == "__main__":
    scan_all_missing_atms()
