
import os
from backtest_main import IChartsDataManager, ICHARTS_DIR
import datetime

def debug_oct28():
    target_date = datetime.date(2025, 10, 28)
    loader = IChartsDataManager(ICHARTS_DIR)
    
    print(f"--- Debugging {target_date} ---")
    expiry = loader.get_nearest_expiry(target_date)
    print(f"Nearest Expiry: {expiry}")
    
    if expiry:
        strike = 25900
        print(f"Looking for Strike: {strike}")
        
        # Check file map directly
        fpath = loader.file_map.get((expiry, strike))
        print(f"File Path in Map: {fpath}")
        
        if fpath:
            if os.path.exists(fpath):
                print("File exists on disk.")
                df = loader.load_straddle(target_date, strike)
                if df is not None and not df.empty:
                    print(f"Successfully loaded {len(df)} rows.")
                    print(df.head())
                else:
                    print("Failed to load content (df empty or None).")
            else:
                print("File path in map does NOT exist on disk.")
        else:
            print("Strike NOT found in File Map.")
            
            # Manual Search in directory to see if it exists but wasn't mapped
            print("\n--- Manual Directory Search ---")
            expiry_str = expiry.strftime("%d%b%y").upper()
            search_str = f"_{expiry_str}_{strike}_"
            print(f"Searching for pattern: {search_str}")
            
            print("\n--- Available Strikes for 28OCT25 ---")
            found_strikes = []
            for fname in os.listdir(ICHARTS_DIR):
                if "_28OCT25_" in fname:
                    found_strikes.append(fname)
            
            if found_strikes:
                print(f"Found {len(found_strikes)} files for this expiry.")
                print("First 10 files:", sorted(found_strikes)[:10])
                # Extract strike numbers
                strikes = []
                for f in found_strikes:
                    try:
                        parts = f.split("_")
                        strikes.append(int(parts[2]))
                    except: pass
                strikes.sort()
                print(f"Min Strike: {min(strikes)}, Max Strike: {max(strikes)}")
                if 25900 in strikes:
                    print("Wait, 25900 IS in the list?")
                else:
                    print(f"25900 is MISSING. Nearest are: {[s for s in strikes if abs(s-25900) <= 200]}")
            else:
                print("NO FILES found for 28OCT25 expiry!")
    else:
        print("No Expiry found.")

if __name__ == "__main__":
    debug_oct28()
