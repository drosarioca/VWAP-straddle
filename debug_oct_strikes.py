
import os
import sys
import pandas as pd
from datetime import datetime, date

# Mocking the path setup
INDEX_DATA_PATH = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\NIFTY-index-data"
ICHARTS_DIR = r"c:\Users\Rosario\.gemini\antigravity\scratch\quant_trading\icharts_download"

def check_missing_strikes():
    print("--- Checking Missing ATM Strikes for Oct 2025 ---")
    
    # 1. Map existing files
    print(f"Scanning {ICHARTS_DIR}...")
    existing_files = set(os.listdir(ICHARTS_DIR))
    
    target_dates = [
        date(2025, 10, 7),
        date(2025, 10, 14),
        date(2025, 10, 20),
        date(2025, 10, 28)
    ]
    
    missing_strikes = []
    
    for d in target_dates:
        # Load Spot Data
        spot_file = os.path.join(INDEX_DATA_PATH, f"NIFTY-1minute-data-{d}.csv")
        if not os.path.exists(spot_file):
            print(f"Skipping {d}: Spot file not found.")
            continue
            
        try:
            df = pd.read_csv(spot_file)
            # Filter for 09:30
            # Ensure time column
            # Formats vary, assume 'time' or second col
            row = df[df['time'] == '09:30:00']
            if row.empty:
                 # Try with date-time combined or just grab 15th row
                 # 9:15 to 9:30 is 15 mins.
                 if len(df) > 20:
                     spot_price = df.iloc[15]['close']
                 else:
                     print(f"{d}: Data too short.")
                     continue
            else:
                spot_price = row.iloc[0]['close']
                
            atm_strike = round(spot_price / 50) * 50
            
            # Construct expected filename
            # NIFTY_07OCT25_25100_Straddle.csv
            # Date part: %d%b%y in UPPER
            d_str = d.strftime("%d%b%y").upper()
            fname = f"NIFTY_{d_str}_{atm_strike}_Straddle.csv"
            
            if fname in existing_files:
                print(f"[OK] {d}: Spot {spot_price} -> ATM {atm_strike} FOUND.")
            else:
                print(f"[MISSING] {d}: Spot {spot_price} -> ATM {atm_strike} NOT FOUND.")
                missing_strikes.append((d, atm_strike))
                
        except Exception as e:
            print(f"Error processing {d}: {e}")
            
    print("\nSUMMARY OF MISSING FILES:")
    for item in missing_strikes:
        print(item)

if __name__ == "__main__":
    check_missing_strikes()
